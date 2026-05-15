import sys
import json
import logging
from django.db.models import Count, Min, Max, Q
from core.models import JobCard

# Find duplicate parent_job + service_cycle
duplicates_by_parent = JobCard.objects.exclude(parent_job__isnull=True).values('parent_job', 'service_cycle').annotate(count=Count('id')).filter(count__gt=1)

# Find duplicates by loose match (client, service_type, date)
duplicates_by_loose = JobCard.objects.values('client__full_name', 'service_type', 'schedule_datetime__date', 'service_cycle').annotate(count=Count('id')).filter(count__gt=1)

report = {
    "total_parent_duplicates": duplicates_by_parent.count(),
    "total_loose_duplicates": duplicates_by_loose.count(),
    "parent_duplicate_details": list(duplicates_by_parent[:20]),
    "loose_duplicate_details": list(duplicates_by_loose[:20])
}

print("=== DUPLICATE REPORT ===")
print(json.dumps(report, indent=4, default=str))
