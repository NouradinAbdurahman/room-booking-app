from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from rooms.models import Room

DEMO_USERNAMES = ["user1", "user2", "user3"]
DEMO_ROOMS = [("Conference Room A", 10), ("Meeting Room B", 6), ("Focus Room", 4)]


class Command(BaseCommand):
    help = (
        "Create the demo users and rooms (idempotent). "
        "The users' shared password comes from DEMO_USER_PASSWORD."
    )

    def handle(self, *args, **options):
        password = settings.DEMO_USER_PASSWORD
        if not password:
            raise CommandError("DEMO_USER_PASSWORD must be set to seed the demo users.")

        User = get_user_model()
        for username in DEMO_USERNAMES:
            user, created = User.objects.get_or_create(username=username)
            # Re-applied every run so the demo logins always match the current env value.
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(f"{'Created' if created else 'Updated'} demo user {username}")

        # Only adds missing rooms; an existing room is left exactly as it is.
        for name, capacity in DEMO_ROOMS:
            room, created = Room.objects.get_or_create(name=name, defaults={"capacity": capacity})
            self.stdout.write(f"{'Created' if created else 'Exists'} demo room {name} ({room.capacity})")
