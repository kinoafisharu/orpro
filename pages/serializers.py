#! -*- coding: utf-8 -*-

"""
Author: Eugene Zaytsev
Email: zaytsev.eug@gmail.com
"""

from rest_framework.serializers import ModelSerializer
from pages.models import Price


class PriceSerializer(ModelSerializer):

    class Meta:
        model = Price
        fields = ('id', 'price_type', 'value',)