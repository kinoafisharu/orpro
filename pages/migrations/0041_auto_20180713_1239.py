# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-07-13 12:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0040_auto_20180713_1227'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='footer_text',
        ),
        migrations.AddField(
            model_name='tags',
            name='footer_text',
            field=models.TextField(blank=True, default=''),
        ),
    ]