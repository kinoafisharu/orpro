# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-01 14:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0016_auto_20180118_1616'),
    ]

    operations = [
        migrations.AddField(
            model_name='offers',
            name='offer_image_url',
            field=models.URLField(blank=True, null=True, verbose_name='Ссылка на картинку'),
        ),
        migrations.AlterField(
            model_name='offers',
            name='offer_subtags',
            field=models.ManyToManyField(blank=True, to='pages.Subtags', verbose_name='pr'),
        ),
    ]
