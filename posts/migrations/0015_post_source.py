# Generated by Django 3.2.3 on 2021-10-21 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0014_scrapejob_job_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='source',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
    ]
