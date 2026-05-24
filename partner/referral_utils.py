"""Map CRM inquiry status ↔ partner-facing referral status."""

CRM_TO_PARTNER = {
    'New': 'pending',
    'Contacted': 'in_progress',
    'Converted': 'successful',
    'Closed': 'closed',
}

PARTNER_TO_CRM = {v: k for k, v in CRM_TO_PARTNER.items()}

PARTNER_STATUS_LABELS = {
    'pending': 'Pending',
    'in_progress': 'In Progress',
    'successful': 'Successful',
    'closed': 'Closed',
}


def partner_status_from_crm(crm_status: str) -> str:
    return CRM_TO_PARTNER.get(crm_status, 'pending')


def crm_status_from_partner(partner_status: str) -> str:
    return PARTNER_TO_CRM.get(partner_status, 'New')
