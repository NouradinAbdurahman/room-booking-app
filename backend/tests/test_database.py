from django.db import connection


def test_tests_run_against_postgresql(db):
    assert connection.vendor == "postgresql"
