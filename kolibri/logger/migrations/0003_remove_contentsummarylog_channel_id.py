# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-05 20:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logger', '0002_remove_contentinteractionlog_item_session'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contentsummarylog',
            name='channel_id',
        ),
    ]
