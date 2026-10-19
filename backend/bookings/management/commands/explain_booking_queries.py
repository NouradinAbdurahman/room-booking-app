"""Development only: EXPLAIN ANALYZE the two Booking list queries exactly as the
API runs them (bookings.queries), for the performance evidence (ticket 13).

    python manage.py seed_perf_data
    python manage.py explain_booking_queries
    python manage.py explain_booking_queries --without-index booking_room_start_active_idx

--without-index drops one index inside a transaction that is always rolled
back, so the comparison never changes the database.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count, Q
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

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
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP INDEX "{without_index}"')  # name from the developer's own CLI
                    self.stdout.write(f"(index {without_index} dropped for this run; rolled back afterwards)")
                self._explain("Day schedule: page", queries.day_schedule(room, date)[:PAGE_SIZE])
                self._explain_count("Day schedule: count", queries.day_schedule(room, date))
                self._explain("My Bookings: page", queries.upcoming_bookings(user, now)[:PAGE_SIZE])
                self._explain_count("My Bookings: count", queries.upcoming_bookings(user, now))
                raise Rollback
        except Rollback:
            pass

        self._query_counts(room, date, user)

    def _explain(self, label, queryset):
        self.stdout.write(f"\n=== {label}\n{queryset.explain(analyze=True, buffers=True)}")

    def _explain_count(self, label, queryset):
        # The paginator's COUNT(*), as Django builds it for this queryset.
        sql, params = queryset.order_by().values("pk").query.sql_with_params()
        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) SELECT COUNT(*) FROM ({sql}) AS page", params)
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
