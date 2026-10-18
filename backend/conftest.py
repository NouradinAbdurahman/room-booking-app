import pytest
from django.conf import settings

POSTGRESQL_ENGINE = "django.db.backends.postgresql"


def pytest_configure(config):
    # The booking guarantees live in PostgreSQL constraints, so a test run on
    # any other database would prove nothing. Refuse to start instead.
    engine = settings.DATABASES["default"]["ENGINE"]
    if engine != POSTGRESQL_ENGINE:
        pytest.exit(
            f"Tests must run against PostgreSQL, but the database engine is {engine!r}.",
            returncode=1,
        )
