# -*- coding: utf-8 -*-
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# Делаем импорт настроек для импорта-экспорта.
from .resource import *
from import_export.formats.base_formats import *
# Делаем наследование от ImportExportModelAdmin, вместо обычного admin.AdminModels.
# Для подключение батарейке к моделе необходимо указывать наследование от ImportExportModelAdmin
# Он отвечает за импорт-экспорт в моделе.
import ast
import json

from import_export.formats.base_formats import JSON as _JSON
class JSON(_JSON):
    def export_data(self, dataset, **kwargs):
        data = []
        for row in dataset.dict:
            row_fix = {}
            data.append(row_fix)
            for k, v in row.items():
                if isinstance(v, str) and (v.startswith("{'") and v.endswith("'}")):
                    v = ast.literal_eval(v)
                if isinstance(v, str) and (v.startswith("['") and v.endswith("']")):
                    v = ast.literal_eval(v)
                row_fix[k] = v
        return json.dumps(data, ensure_ascii=False)

    def get_content_type(self):
        return 'application/json; charset=utf-8'


class TinyMCEAdmin(admin.ModelAdmin):
    class Media:
        js = ('/static/js/tiny_mce/tiny_mce.js', '/static/js/tiny_mce/textareas.js',)


class OfferAdmin(TinyMCEAdmin, ImportExportModelAdmin):
    search_fields = ('offer_title', )
    list_display = ('offer_title', 'get_main_image')
    resource_class = OfferResource

    def get_export_formats(self):
        return [CSV, XLS, XLSX, TSV, JSON, HTML]

    def get_import_formats(self):
        return [CSV, XLS, XLSX, TSV, JSON, HTML]

admin.site.register(Post, TinyMCEAdmin)
admin.site.register(Offers, OfferAdmin)
admin.site.register(AboutCompany, TinyMCEAdmin)
admin.site.register(Category)
admin.site.register(Subtags)
admin.site.register(Tags)
admin.site.register(MainBaner)
admin.site.register(FBlocks)
admin.site.register(LBlocks)
admin.site.register(TopOffers)
admin.site.register(Support)
admin.site.register(Personal)
admin.site.register(HeaderPhoto)
admin.site.register(Company)
admin.site.register(Availability)
admin.site.register(Images)
admin.site.register(Publish)
admin.site.register(Reviews)
