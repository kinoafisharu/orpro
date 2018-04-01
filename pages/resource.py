from .models import *
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from import_export import fields
from import_export import resources

# По умолчанию ModelResource, исследует поля модели и создает Field-трибуты с соответствующим Widget для каждого поля.
# Чтобы повлиять на то, какие поля модели будут включены в ресурс импорта-экспорта переопределим эти настройки.
# Потому что по умолчание стоит pk(id поля). Мы же делаем по названию или как захотим.
class OfferResource(resources.ModelResource):
    offer_title = fields.Field(
        column_name='offer_title',
        attribute='offer_title')
    offer_valuta = fields.Field(
        column_name='offer_valuta',
        attribute='offer_valuta')
    offer_price = fields.Field(
        column_name='offer_price',
        attribute='offer_price')
    offer_value = fields.Field(
        column_name='offer_value',
        attribute='offer_value')
    offer_minorder = fields.Field(
        column_name='offer_minorder',
        attribute='offer_minorder')
    offer_minorder_value = fields.Field(
        column_name='offer_minorder_value',
        attribute='offer_minorder_value')
    offer_pre_text = fields.Field(
        column_name='offer_pre_text',
        attribute='offer_pre_text')
    offer_availability = fields.Field(
        column_name='offer_availability',
        attribute='offer_availability',
        widget=ForeignKeyWidget(Availability, 'availability_title'))
    offer_publish = fields.Field(
        column_name='offer_publish',
        attribute='offer_publish',
        widget=ForeignKeyWidget(Publish, 'publish_title'))
    offer_url = fields.Field(
        column_name='offer_url',
        attribute='offer_url')
    offer_image_url = fields.Field(
        column_name='offer_image_url',
        attribute='offer_image_url')
    # Настройка полей для экспорта и импорта. Поле связаное по ключу.
    offer_tag = fields.Field(
        column_name='offer_tag',
        attribute='offer_tag',
        widget=ForeignKeyWidget(Tags, 'tag_title'))
    # Настройка полей для экспорта и импорта. Поле связаное по многое-ко-многому. Ниже продолжение настроек.
    offer_subtags = fields.Field(widget=ManyToManyWidget(Subtags, 'tag_title'))

    class Meta:
        model = Offers
        exclude = ["id"]
        fields = ('offer_title', 'offer_price', 'offer_valuta', 'offer_minorder',
                  'offer_minorder_value', 'offer_pre_text', 'offer_text', 'offer_publish',
                  'offer_availability', 'offer_image_url', 'offer_url', 'offer_tag', 'offer_subtags')

    # Настройка полей для экспорта и импорта. Поле связаное по многое-ко-многому. Выводим все значение. Функция описана в док. к батарейке
    def dehydrate_offer_subtags(self, offers):
        colls = [coll.tag_title for coll in offers.offer_subtags.all()]
        collectors = ', '.join(colls)

        return '%s' % collectors
