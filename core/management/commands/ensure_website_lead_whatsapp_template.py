"""
Ensure WhatsFlow draft exists for staff website-lead WhatsApp alert.

Does NOT auto-approve on Meta. After create:
  1. Open WhatsFlow CRM → Templates
  2. Open pc99_website_lead_alert
  3. Submit to Meta for Utility review
  4. Wait until status = approved
  5. Set Railway WEBSITE_LEAD_STAFF_WHATSAPP to the staff personal number

Usage:
  python manage.py ensure_website_lead_whatsapp_template
  python manage.py ensure_website_lead_whatsapp_template --force
"""
from django.core.management.base import BaseCommand

from core.whatsflow_pc99 import STAFF_LEAD_TEMPLATE_BODY, ensure_staff_lead_template_draft


class Command(BaseCommand):
    help = 'Create/ensure WhatsFlow draft template pc99_website_lead_alert for staff lead alerts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Create another draft even if a template with the same name exists.',
        )

    def handle(self, *args, **options):
        result = ensure_staff_lead_template_draft(force=options['force'])
        if not result.get('ok'):
            self.stderr.write(self.style.ERROR(f"failed: {result.get('error')}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"template={result.get('name')} id={result.get('id')} "
            f"status={result.get('status')} meta={result.get('meta_status')} "
            f"created={result.get('created')}"
        ))
        self.stdout.write('')
        self.stdout.write('Body to submit in Meta / WhatsFlow:')
        self.stdout.write(STAFF_LEAD_TEMPLATE_BODY)
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'Next: Submit this Utility template in WhatsFlow CRM → wait for Meta APPROVED, '
            'then set WEBSITE_LEAD_STAFF_WHATSAPP to a staff personal WhatsApp (not the WABA sender).'
        ))
