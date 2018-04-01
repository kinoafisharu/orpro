import os
import sys
from .models import *
import xlrd
import django
import json
from django.shortcuts import get_object_or_404
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import IntegrityError
from django.template.defaultfilters import slugify
from unidecode import unidecode
os.environ['DJANGO_SETTINGS_MODULE'] = 'untitled1.settings'
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
django.setup()


class UploadingProducts(object):
    foreign_key_field = ["offer_tag"]
    foreign_key_field_availability = ["offer_availability"]
    foreign_key_field_publish = ["offer_publish"]
    key_field = ["offer_url"]
    model = Offers

    def __init__(self, data):
        data = data
        self.uploaded_file = data.get("file")
        self.format_file = data.get("format_file")

    def getting_related_model(self, field_name):
        related_model = self.model._meta.get_field(field_name).rel.to
        return related_model

    def getting_headers(self):
        s = self.s
        headers = dict()
        for column in range(s.ncols):
            value = s.cell(0, column).value
            headers[column] = value
        return headers

    def parsing(self):
        uploaded_file = self.uploaded_file
        if self.format_file == 'xls' or self.format_file == 'xlsx':
            wb = xlrd.open_workbook(file_contents=uploaded_file.read())
            s = wb.sheet_by_index(0)
            self.s = s
            headers = self.getting_headers()
            product_bulk_list = list()
            sub_bulk_list = []
            sub_key_bulk_list = []
            sub_bulk_cat_list = []
            for row in range(1, s.nrows):
                row_dict = {}
                for column in range(s.ncols):
                    value = s.cell(row, column).value
                    field_name = headers[column]
                    if field_name == 'id' and not value:
                        continue
                    if field_name == "offer_subtags":
                        continue

                    if field_name in self.foreign_key_field_availability:
                        related_model = self.getting_related_model(field_name)
                        instance, created = related_model.objects.get_or_create(availability_title=value)
                        value = instance

                    if field_name in self.foreign_key_field_publish:
                        related_model = self.getting_related_model(field_name)
                        instance, created = related_model.objects.get_or_create(publish_title=value)
                        value = instance
                    if field_name in self.foreign_key_field:
                        related_model = self.getting_related_model(field_name)
                        try:
                            instance = related_model.objects.get(tag_title=value)
                        except ObjectDoesNotExist:
                            related_model.objects.create(tag_url=slugify(unidecode(value)), tag_title=value,
                                                         tag_publish=True, tag_priority=1)
                            instance = related_model.objects.get(tag_title=value)
                        value = instance
                    row_dict[field_name] = value
                # product_bulk_list.append(Offers(**row_dict))
                Offers.objects.update_or_create(**row_dict)
                key = row_dict["offer_url"]
                sub_bulk_cat = row_dict["offer_tag"]
                sub_bulk_cat_list.append(sub_bulk_cat)
                sub_bulk_list.append(key)
            # Offers.objects.bulk_create(product_bulk_list)
            for row in range(1, s.nrows):
                sub_dict = []
                sub_tag_list = []
                for column in range(s.ncols):
                    value = s.cell(row, column).value
                    field_name = headers[column]
                    if field_name in "offer_subtags":
                        for st in range(len(sub_bulk_cat_list)):
                            a = [v for v in value.split(", ")]
                            sub_tag_list.append(a)
                            for i in range(len(sub_tag_list[st])):
                                try:
                                    instance = Subtags.objects.get(tag_title=a[i])
                                except ObjectDoesNotExist:
                                    Subtags.objects.create(tag_url=slugify(unidecode(a[i])), tag_title=a[i],
                                                           tag_parent_tag=sub_bulk_cat_list[st])
                                    instance = get_object_or_404(Subtags, tag_title=a[i])
                                value_sub = instance
                                sub_dict.append(value_sub)
                        sub_key_bulk_list.append(sub_dict)
            ThroughModel = Offers.offer_subtags.through
            for i in range(len(sub_bulk_list)):
                for j in range(len(sub_key_bulk_list[i])):
                    try:
                        try:
                            ThroughModel.objects.bulk_create([
                                ThroughModel(offers_id=get_object_or_404(Offers, offer_url=sub_bulk_list[i]).id,
                                             subtags_id=get_object_or_404(Subtags, tag_title=sub_key_bulk_list[i][j]).id),
                            ])
                        except (MultipleObjectsReturned, IntegrityError):
                            continue
                    except IndexError:
                        continue
            return True
        elif self.format_file == 'json':
            x = json.loads(uploaded_file.read())
            js = []
            self.err = []
            self.add = ["Добавлены поля по стандарту", ]
            ThroughModel = Offers.offer_subtags.through
            for i in range(len(x)):
                d = dict()
                try:
                    d["offer_title"] = x[i]["offer_title"]
                except KeyError:
                    self.err.append("offer_title")
                    return False
                try:
                    if x[i]["offer_url"] == "":
                        print("WOAP")
                        d["offer_url"] = slugify(unidecode(x[i]["offer_title"]))
                    else:
                        d["offer_url"] = x[i]["offer_url"]
                except KeyError:
                    d["offer_url"] = slugify(unidecode(x[i]["offer_title"]))
                    self.add.append("offer_url:{}".format(slugify(unidecode(x[i]["offer_title"]))))
                    return False
                try:
                    d["offer_price"] = x[i]["offer_price"].replace(",", ".")
                except KeyError:
                    self.err.append("offer_price")
                    return False
                try:
                    d["offer_valuta"] = x[i]["offer_valuta"]
                except KeyError:
                    d["offer_valuta"] = "руб."
                    self.add.append("offer_valuta: руб.")
                try:
                    d["offer_value"] = x[i]["offer_value"]
                except KeyError:
                    self.err.append("offer_value")
                    return False
                try:
                    d["offer_minorder"] = x[i]["offer_minorder"]
                except KeyError:
                    d["offer_minorder"] = "1"
                    self.add.append("offer_minorder: 1")
                try:
                    d["offer_minorder_value"] = x[i]["offer_minorder_value"]
                except KeyError:
                    self.err.append("offer_minorder_value")
                    return False
                try:
                    d["offer_pre_text"] = x[i]["offer_pre_text"]
                except KeyError:
                    d["offer_pre_text"] = ""
                    self.add.append("offer_pre_text: """)
                try:
                    d["offer_text"] = x[i]["offer_text"]
                except KeyError:
                    d["offer_text"] = ""
                    self.add.append("offer_text: """)
                try:
                    d["offer_image_url"] = x[i]["offer_image_url"]
                except KeyError:
                    d["offer_image_url"] = x[i]["image_link"]
                try:
                    d["offer_availability"], created = Availability.objects.get_or_create(
                        availability_title=x[i]["offer_availability"])
                except KeyError:
                    d["offer_availability"], created = Availability.objects.get_or_create(
                        availability_title="Под заказ")
                    self.add.append("offer_availability: Под заказ")
                try:
                    if x[i]["offer_publish"] == "":
                        d["offer_publish"], created = Publish.objects.get_or_create(publish_title="Публикуемый")
                    else:
                        d["offer_publish"], created = Publish.objects.get_or_create(publish_title=x[i]["offer_publish"])
                except KeyError:
                    d["offer_publish"], created = Publish.objects.get_or_create(publish_title="Публикуемый")
                    self.add.append("offer_publish: Публикуемый")
                try:
                    try:
                        d["offer_tag"] = Tags.objects.get(tag_title=x[i]["offer_tag"])
                    except ObjectDoesNotExist:
                        Tags.objects.create(tag_url=slugify(unidecode(x[i]["offer_tag"])),
                                            tag_title=x[i]["offer_tag"],
                                            tag_publish=True, tag_priority=1)
                        d["offer_tag"] = get_object_or_404(Tags, tag_title=x[i]["offer_tag"])
                except KeyError:
                    return False
                js.append(d)
                Offers.objects.update_or_create(**d)
            for k in range(len(x)):
                try:
                    for j in range(len(x[k]["offer_subtags"].split(", "))):
                        try:
                            v = Subtags.objects.get(tag_title=x[k]["offer_subtags"].split(", ")[j])
                            print(v)
                        except ObjectDoesNotExist:
                            try:
                                Subtags.objects.create(tag_url=slugify(unidecode(x[k]["offer_subtags"].split(", ")[j])),
                                                       tag_title=x[k]["offer_subtags"].split(", ")[j],
                                                       tag_parent_tag=Tags.objects.get(tag_title=x[k]["offer_tag"]))
                                v = get_object_or_404(Subtags, tag_title=x[k]["offer_subtags"].split(", ")[j])
                            except IntegrityError:
                                continue
                        try:
                            ThroughModel.objects.bulk_create([
                                ThroughModel(offers_id=get_object_or_404(Offers, offer_url=slugify(
                                    unidecode(x[k]["offer_title"])) if x[k]["offer_url"] == ""
                                else x[k]["offer_url"]).id,
                                             subtags_id=get_object_or_404(Subtags, tag_title__icontains=v).id),
                            ])
                        except (MultipleObjectsReturned, IntegrityError):
                            continue
                except KeyError:
                    continue
            return True
