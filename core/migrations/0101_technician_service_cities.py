# Generated manually for technician service_cities M2M

from django.db import migrations, models


def migrate_legacy_service_areas(apps, schema_editor):
    Technician = apps.get_model('core', 'Technician')
    City = apps.get_model('core', 'City')
    import re

    def split_tokens(raw):
        if not raw:
            return []
        return [p.strip() for p in re.split(r'[,/|]+', str(raw)) if p and p.strip()]

    cities = list(City.objects.filter(is_active=True))
    by_name = {c.name.casefold(): c for c in cities if c.name}
    # display-normalized keys
    for c in cities:
        display = ' '.join(part.capitalize() for part in (c.name or '').split())
        by_name.setdefault(display.casefold(), c)

    aliases = {
        'bombay': 'mumbai',
        'navi-mumbai': 'navi mumbai',
        'navimumbai': 'navi mumbai',
        'new mumbai': 'navi mumbai',
        'lonavala': 'lonavla',
        'lonawala': 'lonavla',
    }

    for tech in Technician.objects.all().iterator():
        if tech.service_cities.exists():
            continue
        linked = []
        seen = set()
        for token in split_tokens(tech.city) + split_tokens(tech.service_area):
            key = token.casefold()
            key = aliases.get(key, key)
            city = by_name.get(key)
            if not city:
                # substring / containment
                for name_key, c in by_name.items():
                    if key == name_key or key in name_key or name_key in key:
                        city = c
                        break
            if city and city.id not in seen:
                seen.add(city.id)
                linked.append(city)
        if linked:
            tech.service_cities.set(linked)
            label = ', '.join(
                ' '.join(part.capitalize() for part in c.name.split()) for c in linked
            )
            Technician.objects.filter(pk=tech.pk).update(city=label, service_area=label)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0100_jobcard_hidden_from_technician_ledger'),
    ]

    operations = [
        migrations.AddField(
            model_name='technician',
            name='service_cities',
            field=models.ManyToManyField(
                blank=True,
                help_text='Cities this technician can be assigned to',
                related_name='technicians',
                to='core.city',
                verbose_name='Service Areas / Cities',
            ),
        ),
        migrations.AlterField(
            model_name='technician',
            name='city',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Legacy free-text city; prefer service_cities M2M',
                max_length=100,
                null=True,
                verbose_name='City (Legacy)',
            ),
        ),
        migrations.AlterField(
            model_name='technician',
            name='service_area',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Legacy free-text area; prefer service_cities M2M',
                max_length=255,
                null=True,
                verbose_name='Service Area (Legacy)',
            ),
        ),
        migrations.RunPython(migrate_legacy_service_areas, noop_reverse),
    ]
