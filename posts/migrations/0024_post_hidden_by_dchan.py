# Generated by Django 3.2.3 on 2022-05-15 01:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0023_textboardpost_sock_of'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='hidden_by_dchan',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
