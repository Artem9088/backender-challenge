import datetime as dt
import json
import uuid
from collections.abc import Generator

import pytest
from clickhouse_connect.driver import Client
from django.conf import settings

from outbox.models import EventOutbox
from users.use_cases import CreateUser, CreateUserRequest

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def f_use_case() -> CreateUser:
    return CreateUser()


@pytest.fixture(autouse=True)
def f_clean_up_event_log(f_ch_client: Client) -> Generator:
    f_ch_client.query(f"TRUNCATE TABLE {settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME}")
    yield


def test_user_created(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email="test@email.com",
        first_name="Test",
        last_name="Testovich",
    )

    response = f_use_case.execute(request)

    assert response.result.email == "test@email.com"
    assert response.error == ""


def test_emails_are_unique(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email="test@email.com",
        first_name="Test",
        last_name="Testovich",
    )

    f_use_case.execute(request)
    response = f_use_case.execute(request)

    assert response.result is None
    assert response.error == "User with this email already exists"


def test_event_log_entry_published(
    f_use_case: CreateUser,
    f_ch_client: Client,
) -> None:
    email = f"test_{uuid.uuid4()}@email.com"
    request = CreateUserRequest(
        email=email,
        first_name="Test",
        last_name="Testovich",
    )

    f_use_case.execute(request)

    # Manually call the Celery task to process the outbox
    from outbox.tasks import process_event_outbox

    process_event_outbox()

    # Now, check if the event is present in ClickHouse
    log = f_ch_client.query(
        "SELECT * FROM default.event_log WHERE event_type = 'user_created'",
    )
    assert len(log.result_rows) == 1

    actual_row = log.result_rows[0]

    # Assert event_type
    assert actual_row[0] == "user_created"

    # Assert event_date_time is a datetime object
    assert isinstance(actual_row[1], dt.datetime)

    # Assert environment
    assert actual_row[2] == "Local"

    # Parse event_context and compare dictionaries
    actual_event_context = json.loads(actual_row[3])
    expected_event_context = {
        "email": email,
        "first_name": "Test",
        "last_name": "Testovich",
    }
    assert actual_event_context == expected_event_context

    # Assert metadata_version
    assert actual_row[4] == 1


def test_event_written_to_outbox(f_use_case: CreateUser):
    email = "test@example.com"
    request = CreateUserRequest(
        email=email,
        first_name="Test",
        last_name="User",
    )

    f_use_case.execute(request)

    event = EventOutbox.objects.get(event_context__email=email)

    assert event.event_type == "user_created"
    assert event.processed is False
