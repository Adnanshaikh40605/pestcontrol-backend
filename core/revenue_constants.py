"""
Locked constants for Technician & Revenue Model v2 (40/60).
"""
from decimal import Decimal

# Split: technician share / company share
TECHNICIAN_SHARE_PERCENT = Decimal('40.00')
COMPANY_SHARE_PERCENT = Decimal('60.00')

# Presence / auto-suspend (days offline without approved leave → suspended)
# Locked Phase 0: 3 days (requirements: 2–3 days offline without approval)
AUTO_SUSPEND_OFFLINE_DAYS = 3

# Settlement cadence labels (used in Phase 3)
SETTLEMENT_CADENCE_WEEKLY = 'weekly'
SETTLEMENT_CADENCE_MONTHLY = 'monthly'

# Money quantize
MONEY_QUANTUM = Decimal('0.01')

# Contractual property / commercial signals (JobCard economics)
CONTRACTUAL_PROPERTY_TYPES = frozenset({
    'Society',
    'Hotel',
    'Office',
    'School',
    'Warehouse',
    'Factory',
    'Commercial Space',
    'Shop',
    'Restaurant',
})
CONTRACTUAL_COMMERCIAL_TYPES = frozenset({
    'hotel',
    'society',
    'office',
    'other',
})
