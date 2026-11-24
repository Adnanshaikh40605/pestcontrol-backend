"""Link inquiry mobiles to real JobCard bookings for Not Booked tracking."""

from __future__ import annotations

from django.db.models import BooleanField, Case, Exists, OuterRef, QuerySet, Value, When


def annotate_inquiry_has_booking(qs: QuerySet, *, linked_jobcard: bool = False) -> QuerySet:
    """Annotate ``has_booking`` when any JobCard exists for the inquiry mobile.

    Uses the client mobile on booking records so CRM and Website leads stay
    accurate even if inquiry status was changed manually. When
    ``linked_jobcard`` is True (website leads), a linked JobCard also counts.
    """
    from core.models import JobCard

    booking_exists = Exists(
        JobCard.objects.filter(client__mobile=OuterRef('mobile')),
    )
    if linked_jobcard:
        return qs.annotate(
            has_booking=Case(
                When(linked_jobcard_id__isnull=False, then=Value(True)),
                When(booking_exists, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
    return qs.annotate(has_booking=booking_exists)
