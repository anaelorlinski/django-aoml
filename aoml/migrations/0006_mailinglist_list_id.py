from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds the per-list List-Id override.

    No data migration and no default value: an empty list_id means
    "derive it from the name" (see MailingList.effective_list_id), so
    every existing list keeps working and gets a sensible header the
    first time it sends. Setting the override is only needed for a list
    whose name is going to change, or one that should share an identity
    with another.
    """

    dependencies = [
        ('aoml', '0005_auto_20230506_0040'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailinglist',
            name='list_id',
            field=models.CharField(
                blank=True,
                help_text='Overrides the List-Id header, e.g. '
                          '"soirees.example.com". Leave empty to derive it '
                          'from the name.',
                max_length=255,
                verbose_name='List-Id',
            ),
        ),
    ]
