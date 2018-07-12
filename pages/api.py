#! -*- coding: utf-8 -*-

"""
Author: Eugene Zaytsev
Email: zaytsev.eug@gmail.com
"""

from rest_framework.viewsets import ModelViewSet
from pages.models import Price
from pages.serializers import PriceSerializer
from rest_framework.response import Response


class PriceViewSet(ModelViewSet):

    serializer_class = PriceSerializer
    queryset = Price.objects.all()

    def list(self, request, *args, **kwargs):

        product_id = request.GET.get('product_id', None)

        queryset = self.queryset
        if product_id is not None:
            queryset = queryset.filter(offer__id=product_id)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)