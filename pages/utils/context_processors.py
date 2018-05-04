from __future__ import unicode_literals

from pages.models import Company

def orpro_data(request):
    model = Company.objects.get(pk=1)
    return {'orpro_data': model}
