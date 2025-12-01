"""
Production Database Integrity Check Script

Run this in Django shell on production to identify data issues:
python manage.py shell < check_production_db.py

Or in Railway shell:
railway run python manage.py shell < check_production_db.py
"""

from core.models import JobCard, Client, Renewal, Inquiry
from django.db.models import Q, Count
import logging

logger = logging.getLogger(__name__)

def check_database_integrity():
    """Check database integrity and report issues."""
    
    print("\n" + "="*80)
    print("PRODUCTION DATABASE INTEGRITY CHECK")
    print("="*80 + "\n")
    
    # 1. Check total counts
    print("📊 TOTAL COUNTS:")
    print(f"  - Total Clients: {Client.objects.count()}")
    print(f"  - Total Inquiries: {Inquiry.objects.count()}")
    print(f"  - Total Job Cards: {JobCard.objects.count()}")
    print(f"  - Total Renewals: {Renewal.objects.count()}")
    print()
    
    # 2. Check for orphaned job cards (no client)
    print("🔍 CHECKING FOR ORPHANED JOB CARDS:")
    orphaned_jobcards = JobCard.objects.filter(client__isnull=True)
    orphaned_count = orphaned_jobcards.count()
    print(f"  - Job cards with NULL client: {orphaned_count}")
    
    if orphaned_count > 0:
        print("  ⚠️  WARNING: Found orphaned job cards!")
        print("  - IDs:", list(orphaned_jobcards.values_list('id', flat=True)[:10]))
        print("  - Codes:", list(orphaned_jobcards.values_list('code', flat=True)[:10]))
    else:
        print("  ✅ No orphaned job cards found")
    print()
    
    # 3. Check for job cards with invalid client references
    print("🔍 CHECKING FOR INVALID CLIENT REFERENCES:")
    try:
        all_client_ids = set(Client.objects.values_list('id', flat=True))
        all_jobcard_client_ids = set(JobCard.objects.exclude(client__isnull=True).values_list('client_id', flat=True))
        invalid_client_ids = all_jobcard_client_ids - all_client_ids
        
        if invalid_client_ids:
            print(f"  ⚠️  WARNING: Found {len(invalid_client_ids)} job cards with invalid client IDs")
            print(f"  - Invalid client IDs: {list(invalid_client_ids)[:10]}")
        else:
            print("  ✅ All job card client references are valid")
    except Exception as e:
        print(f"  ❌ Error checking client references: {e}")
    print()
    
    # 4. Check for renewals with invalid job card references
    print("🔍 CHECKING FOR INVALID RENEWAL REFERENCES:")
    try:
        all_jobcard_ids = set(JobCard.objects.values_list('id', flat=True))
        all_renewal_jobcard_ids = set(Renewal.objects.exclude(jobcard__isnull=True).values_list('jobcard_id', flat=True))
        invalid_jobcard_ids = all_renewal_jobcard_ids - all_jobcard_ids
        
        if invalid_jobcard_ids:
            print(f"  ⚠️  WARNING: Found {len(invalid_jobcard_ids)} renewals with invalid job card IDs")
            print(f"  - Invalid job card IDs: {list(invalid_jobcard_ids)[:10]}")
        else:
            print("  ✅ All renewal job card references are valid")
    except Exception as e:
        print(f"  ❌ Error checking renewal references: {e}")
    print()
    
    # 5. Check for job cards with missing required fields
    print("🔍 CHECKING FOR MISSING REQUIRED FIELDS:")
    
    # Check for missing service_type
    missing_service_type = JobCard.objects.filter(Q(service_type__isnull=True) | Q(service_type=''))
    print(f"  - Job cards with missing service_type: {missing_service_type.count()}")
    
    # Check for missing schedule_date
    missing_schedule_date = JobCard.objects.filter(schedule_date__isnull=True)
    print(f"  - Job cards with missing schedule_date: {missing_schedule_date.count()}")
    
    # Check for missing price
    missing_price = JobCard.objects.filter(Q(price__isnull=True) | Q(price=0))
    print(f"  - Job cards with missing/zero price: {missing_price.count()}")
    
    if missing_service_type.count() == 0 and missing_schedule_date.count() == 0 and missing_price.count() == 0:
        print("  ✅ All required fields are present")
    print()
    
    # 6. Check for clients with duplicate mobile numbers
    print("🔍 CHECKING FOR DUPLICATE MOBILE NUMBERS:")
    duplicate_mobiles = Client.objects.values('mobile').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    if duplicate_mobiles.count() > 0:
        print(f"  ⚠️  WARNING: Found {duplicate_mobiles.count()} duplicate mobile numbers")
        for dup in duplicate_mobiles[:5]:
            print(f"  - Mobile: {dup['mobile']}, Count: {dup['count']}")
    else:
        print("  ✅ No duplicate mobile numbers found")
    print()
    
    # 7. Test query that's failing in production
    print("🔍 TESTING PROBLEMATIC QUERY:")
    try:
        # This is the query that fails in production
        test_qs = JobCard.objects.select_related('client').prefetch_related('renewals').all()
        test_qs = test_qs.order_by('-created_at')
        
        # Try to get first 10 records
        first_10 = list(test_qs[:10])
        print(f"  ✅ Successfully retrieved {len(first_10)} job cards")
        
        # Check if any have None clients
        none_clients = [jc for jc in first_10 if jc.client is None]
        if none_clients:
            print(f"  ⚠️  WARNING: {len(none_clients)} job cards in first 10 have None client")
            for jc in none_clients:
                print(f"    - Job Card ID: {jc.id}, Code: {jc.code}")
        
    except Exception as e:
        print(f"  ❌ ERROR: Failed to execute query: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 8. Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    issues_found = []
    
    if orphaned_count > 0:
        issues_found.append(f"- {orphaned_count} orphaned job cards")
    
    if duplicate_mobiles.count() > 0:
        issues_found.append(f"- {duplicate_mobiles.count()} duplicate mobile numbers")
    
    if missing_service_type.count() > 0:
        issues_found.append(f"- {missing_service_type.count()} job cards missing service_type")
    
    if missing_schedule_date.count() > 0:
        issues_found.append(f"- {missing_schedule_date.count()} job cards missing schedule_date")
    
    if issues_found:
        print("\n⚠️  ISSUES FOUND:")
        for issue in issues_found:
            print(f"  {issue}")
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("  1. Fix orphaned job cards by assigning valid clients")
        print("  2. Merge duplicate client records")
        print("  3. Fill in missing required fields")
        print("  4. Run data migration script to clean up")
    else:
        print("\n✅ NO ISSUES FOUND - Database integrity looks good!")
    
    print("\n" + "="*80)
    print()

if __name__ == "__main__":
    check_database_integrity()
