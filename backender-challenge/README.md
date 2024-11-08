# Die Hard

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-username/your-repo-name.git

   cd your-repo-name

   cp src/core/.env.ci src/core/.env

   docker compose up -d

   docker compose exec app python manage.py migrate
   docker compose exec app python manage.py createsuperuser

## Running Tests

To run the test suite:

```bash
docker compose run --rm app pytest -svv

## Code Linting

To run the linter and fix issues:

```bash
docker compose run --rm app ruff check --fix


## Technical Design

For detailed information about the technical solution and design, please refer to the [Technical Design Document](TECHNICAL_DESIGN.md).
