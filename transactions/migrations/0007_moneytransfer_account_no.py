# Generated by Django 4.2.7 on 2023-12-30 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0006_remove_moneytransfer_account_no_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='moneytransfer',
            name='account_no',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]