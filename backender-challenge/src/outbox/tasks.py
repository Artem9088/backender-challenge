from celery import shared_task
from django.utils import timezone

from core.event_log_client import EventLogClient
from outbox.models import EventOutbox


@shared_task
def process_event_outbox():
    events = EventOutbox.objects.filter(processed=False)[:1000]  # Process in batches
    if not events:
        return

    # Prepare data for ClickHouse
    data = []
    for event in events:
        data.append(
            {
                "event_type": event.event_type,
                "event_date_time": event.event_date_time,
                "environment": event.environment,
                "event_context": event.event_context,
                "metadata_version": event.metadata_version,
            },
        )

    # Insert data into ClickHouse
    with EventLogClient.init() as client:
        client.insert(data)

    # Mark events as processed
    EventOutbox.objects.filter(id__in=[event.id for event in events]).update(
        processed=True,
        processed_at=timezone.now(),
    )
