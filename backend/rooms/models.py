from django.db import models


class Room(models.Model):
    """A meeting room in the Doha office (GLOSSARY: Room, Capacity)."""

    name = models.CharField(max_length=100)
    # Informational only; it does not limit who can book (GLOSSARY: Capacity).
    capacity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        # Enforced by PostgreSQL, so even code that skips validation cannot
        # save an invalid Room (ADR 0003).
        constraints = [
            models.UniqueConstraint(fields=["name"], name="room_name_unique"),
            models.CheckConstraint(
                condition=~models.Q(name__regex=r"^\s*$"), name="room_name_not_blank"
            ),
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name="room_capacity_positive"),
        ]

    def __str__(self):
        return self.name
