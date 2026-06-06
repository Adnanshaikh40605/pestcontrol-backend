from django.db import migrations


LONAVALA_LOCATIONS = [
    'Lonavala',
    'Khandala',
    'Khopoli',
    'Karjat',
    'Talegaon',
    'Pawna',
    'Tungarli',
    'Valvan',
    'Bhushi Dam',
    'Diksal',
    'Varsoli',
    'Kurvande',
    'Ryewood Park',
    'Kaivalyadhama',
    'Lonavala Station',
    'Khandala Station',
    'Rajmachi',
    'Malavli',
    'Wadgaon',
    'Shirgaon',
]


def _normalize_location_name(text: str) -> str:
    return ''.join((text or '').split()).lower()


def seed_lonavala(apps, schema_editor):
    Country = apps.get_model('core', 'Country')
    State = apps.get_model('core', 'State')
    City = apps.get_model('core', 'City')
    Location = apps.get_model('core', 'Location')

    country = Country.objects.filter(name='India').first()
    if not country:
        country = Country.objects.create(name='India')

    state = State.objects.filter(country=country, name='Maharashtra').first()
    if not state:
        state = State.objects.create(country=country, name='Maharashtra')

    city, _ = City.objects.get_or_create(state=state, name='Lonavala', defaults={'is_active': True})
    if not city.is_active:
        city.is_active = True
        city.save(update_fields=['is_active'])

    for loc_name in LONAVALA_LOCATIONS:
        normalized = _normalize_location_name(loc_name)
        Location.objects.get_or_create(
            city=city,
            normalized_name=normalized,
            defaults={'name': loc_name, 'is_active': True},
        )


def unseed_lonavala(apps, schema_editor):
    City = apps.get_model('core', 'City')
    City.objects.filter(state__name='Maharashtra', name='Lonavala').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0076_partnerappversionconfig'),
    ]

    operations = [
        migrations.RunPython(seed_lonavala, unseed_lonavala),
    ]
