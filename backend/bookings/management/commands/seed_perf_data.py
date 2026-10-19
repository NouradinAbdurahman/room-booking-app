"""Development only: a large, realistic dataset for the performance evidence (ticket 13).

Never run automatically. Every row goes through the database constraints, so
the data is as valid as real data: no overlapping Active bookings per Room,
15 minutes to 4 hours each, cancelled_at consistent with status.
"""

import random
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from bookings.models import Booking, BookingStatus
from rooms.models import Room

ROOM_PREFIX = "Perf Room "
USER_PREFIX = "perf_user_"
QUARTER = timedelta(minutes=15)


class Command(BaseCommand):
    help = "Seed many Bookings across Rooms, Days and Users for EXPLAIN ANALYZE (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--rooms", type=int, default=20)
        parser.add_argument("--users", type=int, default=50)
        parser.add_argument("--days", type=int, default=365, help="Spread evenly around today.")
        parser.add_argument("--seed", type=int, default=2026, help="Random seed, for reproducible data.")
        parser.add_argument("--reset", action="store_true", help="Delete earlier perf data first.")
        parser.add_argument("--delete", action="store_true", help="Only delete the perf data, then stop.")
        parser.add_argument("--force", action="store_true", help="Allow running with DEBUG off.")

    def handle(self, *args, rooms, users, days, seed, reset, delete, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError("Development only: run with DJANGO_DEBUG=True, or pass --force.")
        rng = random.Random(seed)

        with transaction.atomic():
            if reset or delete:
                self._delete_perf_data()
                if delete:
                    return
            elif Room.objects.filter(name__startswith=ROOM_PREFIX).exists():
                raise CommandError("Perf data already exists; pass --reset to rebuild it.")

            perf_rooms = Room.objects.bulk_create(
                Room(name=f"{ROOM_PREFIX}{n:02d}", capacity=rng.choice([4, 6, 8, 10, 12])) for n in range(rooms)
            )
            User = get_user_model()
            perf_users = User.objects.bulk_create(User(username=f"{USER_PREFIX}{n:03d}") for n in range(users))

            today = timezone.localdate()
            first_day = today - timedelta(days=days // 2)
            zone = timezone.get_default_timezone()
            now = timezone.now()
            batch = []
            for room in perf_rooms:
                cursor = datetime.combine(first_day, time(7), tzinfo=zone)
                end_of_range = cursor + timedelta(days=days)
                while cursor < end_of_range:
                    cursor += QUARTER * rng.randint(0, 16)  # a gap of up to 4 hours
                    length = QUARTER * rng.randint(1, 16)  # 15 minutes to 4 hours
                    start, end = cursor, cursor + length
                    cancelled = rng.random() < 0.15
                    batch.append(_booking(room, rng.choice(perf_users), start, end, cancelled, now))
                    if cancelled and rng.random() < 0.5:
                        # Cancelled history often overlaps the Active booking that replaced it.
                        batch.append(_booking(room, rng.choice(perf_users), start, end, False, now))
                    cursor = end
                    if cursor.hour >= 20 and rng.random() < 0.7:
                        cursor = datetime.combine(cursor.date() + timedelta(days=1), time(7), tzinfo=zone)
            Booking.objects.bulk_create(batch, batch_size=5000)

        # Fresh planner statistics, as autovacuum would eventually provide.
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE bookings_booking")

        active = sum(1 for b in batch if b.status == BookingStatus.ACTIVE)
        crossing = sum(1 for b in batch if timezone.localdate(b.start_time) != timezone.localdate(b.end_time))
        self.stdout.write(
            f"Created {len(perf_rooms)} rooms, {len(perf_users)} users, {len(batch)} bookings "
            f"({active} active, {len(batch) - active} cancelled, {crossing} crossing midnight)."
        )


    def _delete_perf_data(self):
        """Only rows this command created: its prefixed Rooms and Users and their Bookings."""
        bookings, _ = Booking.objects.filter(room__name__startswith=ROOM_PREFIX).delete()
        rooms, _ = Room.objects.filter(name__startswith=ROOM_PREFIX).delete()
        users, _ = get_user_model().objects.filter(username__startswith=USER_PREFIX).delete()
        self.stdout.write(f"Deleted perf data: {bookings} bookings, {rooms} rooms, {users} user rows.")


def _booking(room, user, start, end, cancelled, now):
    return Booking(
        room=room,
        user=user,
        title="Perf",
        start_time=start,
        end_time=end,
        status=BookingStatus.CANCELLED if cancelled else BookingStatus.ACTIVE,
        cancelled_at=now if cancelled else None,
    )
