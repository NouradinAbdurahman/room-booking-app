"""Development only: EXPLAIN ANALYZE the two Booking list queries exactly as the
API runs them (bookings.queries), for the performance evidence (ticket 13).

    python manage.py seed_perf_data
    python manage.py explain_booking_queries
    python manage.py explain_booking_queries --without-index booking_room_start_active_idx

--without-index drops one index of the bookings table inside a transaction
that is always rolled back, so the comparison never changes the database.
While it runs it holds an ACCESS EXCLUSIVE lock on bookings_booking, which
blocks the running app's requests to that table: use it on a development
database only.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, Q
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from psycopg import sql

from bookings import queries
from bookings.doha_time import doha_day_bounds
from bookings.models import Booking, BookingStatus
from rooms.models import Room

PAGE_SIZE = 100


class Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "EXPLAIN ANALYZE the Day schedule and My Bookings queries on the current data."

    def add_arguments(self, parser):
        parser.add_argument("--without-index", help="Index to drop for this run only (rolled back).")

    def handle(self, *args, without_index=None, **options):
        now = timezone.now()
        room, date = self._busiest_room_day(now)
        user = self._user_with_most_upcoming(now)
        self.stdout.write(
            f"Bookings: {Booking.objects.count()} "
            f"({Booking.objects.filter(status=BookingStatus.ACTIVE).count()} active). "
            f"Day schedule: room {room.id} ({room.name}) on {date}. My Bookings: {user.username}."
        )
        try:
            with transaction.atomic():
                if without_index:
                    self._drop_index_for_this_run(without_index)
                self._explain("Day schedule: page", queries.day_schedule(room, date)[:PAGE_SIZE])
                self._explain_count("Day schedule: count", queries.day_schedule(room, date))
                self._explain("My Bookings: page", queries.upcoming_bookings(user, now)[:PAGE_SIZE])
                self._explain_count("My Bookings: count", queries.upcoming_bookings(user, now))
                raise Rollback
        except Rollback:
            pass

        self._query_counts(room, date, user)

    def _drop_index_for_this_run(self, name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_indexes WHERE tablename = 'bookings_booking' AND indexname = %s", [name]
            )
            if cursor.fetchone() is None:
                raise CommandError(f"{name!r} is not an index of bookings_booking.")
            # An exclusion constraint's index is dropped with its constraint, not on its own.
            cursor.execute(
                "SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = 'bookings_booking'::regclass", [name]
            )
            if cursor.fetchone():
                cursor.execute(sql.SQL("ALTER TABLE bookings_booking DROP CONSTRAINT {}").format(sql.Identifier(name)))
            else:
                cursor.execute(sql.SQL("DROP INDEX {}").format(sql.Identifier(name)))
        self.stdout.write(f"(index {name} dropped for this run; rolled back afterwards)")

    def _explain(self, label, queryset):
        self.stdout.write(f"\n=== {label}\n{queryset.explain(analyze=True, buffers=True)}")

    def _explain_count(self, label, queryset):
        # The exact COUNT query the paginator sends, captured from .count().
        with CaptureQueriesContext(connection) as ctx:
            queryset.count()
        count_sql = ctx.captured_queries[-1]["sql"]
        with connection.cursor() as cursor:
            cursor.execute("EXPLAIN (ANALYZE, BUFFERS) " + count_sql)
            plan = "\n".join(row[0] for row in cursor.fetchall())
        self.stdout.write(f"\n=== {label}\n{plan}")

    def _query_counts(self, room, date, user):
        client = Client(HTTP_HOST="localhost")
        client.force_login(user)
        self.stdout.write("\n=== Queries per API request (no query per row)")
        for label, url in [
            ("Day schedule", f"/api/bookings/?room={room.id}&date={date}"),
            ("My Bookings", "/api/bookings/?mine=true"),
        ]:
            with CaptureQueriesContext(connection) as ctx:
                response = client.get(url)
            body = response.json()
            self.stdout.write(
                f"{label}: HTTP {response.status_code}, {len(body['results'])} of {body['count']} "
                f"bookings returned in {len(ctx.captured_queries)} queries"
            )

    def _busiest_room_day(self, now):
        today = timezone.localdate(now)
        candidates = []
        for room in Room.objects.all():
            for offset in range(0, 30):
                date = today + timedelta(days=offset)
                start, end = doha_day_bounds(date)
                count = Booking.objects.filter(
                    room=room, status=BookingStatus.ACTIVE, start_time__lt=end, end_time__gt=start
                ).count()
                candidates.append((count, room.id, room, date))
        _, _, room, date = max(candidates)
        return room, date

    def _user_with_most_upcoming(self, now):
        return (
            get_user_model()
            .objects.annotate(
                upcoming=Count("bookings", filter=Q(bookings__status=BookingStatus.ACTIVE, bookings__end_time__gt=now))
            )
            .order_by("-upcoming", "id")
            .first()
        )
