from django import forms, views
from django.template import loader
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.datastructures import MultiValueDictKeyError

from pages.models import Offers, Subtags, Availability

__all__ = ('FormAjaxBase', 'BaseAjaxView', )


class FormAjaxBase(forms.ModelForm):
    def get_model_object(self, *args):
        pass

    def save_to_database(self, request):
        model_id = request.POST.get('model-id', None)

        try:
            int(model_id)
        except Exception:
            model_id = None

        #if True:
        try:
            exist_model = self.__model_class.objects.get(id=model_id)
        except self.__model_class.DoesNotExist:
            exist_model = self.__model_class()
            #raise IndexError('Model not found')

        delete = True if request.POST.get('delete', False) == 'on' else False
        if delete:
            exist_model.delete()
            return

        for field_model in self.__list_fields:
            field_sv_file = request.FILES.get(field_model, None)
            try:
                if field_model == 'offer_subtags':
                    exist_model.offer_subtags.clear()
                    for option_id in request.POST.getlist(field_model):
                        try:
                            obj_sub = Subtags.objects.get(id=option_id)
                        except Subtags.DoesNotExist:
                            continue
                        exist_model.offer_subtags.add(obj_sub)
                elif field_model == 'offer_availability':
                    field_sv = int(request.POST[field_model])
                    field_model += '_id'
                else:
                    field_sv = field_sv_file if field_sv_file else request.POST[field_model]
            except MultiValueDictKeyError:
                continue

            if field_model == 'tag_priority':
                if field_sv == '' or field_sv == None:
                    exist_model.__dict__[field_model] = None
                    continue
            exist_model.__dict__[field_model] = field_sv
            #print('\n\n{}\n\n {} \n\n'.format(field_model, exist_model.__dict__))
        exist_model.save()
        #else:
        #    raise AttributeError('Field "model-id" not found.')

    def __init__(self, model_initial_id=None, *args, **kwargs):
        try:
            self.__list_fields = self.Meta.fields
            self.__model_class = self.Meta.model
        except AttributeError:
            raise AttributeError('Сlass "Meta" is not found or it does not have attribute of "fields"')

        if model_initial_id is not None:
            initial_dict = {}
            form_initial = self.__model_class.objects.get(id=model_initial_id)

            for field_name in self.__list_fields:
                try:
                    initial_dict[field_name] = form_initial.__dict__[field_name]
                except KeyError:
                    continue

            super().__init__(initial=initial_dict, *args, **kwargs)
        #else:
        #    raise ValueError('The variable "model_initial_id" has an empty value')


class BaseAjaxView(views.View):

    def get(self, request):
        file_name_template = request.path.split('/')[-1]

        if file_name_template in self.ADMIN_EDIT_FORM:

            class_form = self.ADMIN_EDIT_FORM[file_name_template]
            model_id = request.GET.get('model-id', None)

            try:
                int(model_id)
            except Exception:
                model_id = None

            self.context_data['form'] = class_form(model_initial_id=model_id)
            self.context_data['template_send'] = file_name_template
            self.context_data['model_id'] = model_id

            get_context = getattr(self.context_data['form'], 'get_context', None)
            if get_context is not None:
                if callable(get_context):
                    self.context_data.update({'extra_data': get_context()})

            if file_name_template == 'offer-edit.html' and model_id is not None:
                result_list_tags = None
                try:
                    model_object = Offers.objects.get(id=model_id)
                    result_list_tags = model_object.offer_subtags.all()
                    self.context_data['offer_all_subtags'] = Subtags.objects.filter(tag_parent_tag=model_object.offer_tag)
                    self.context_data['offer_availability'] = model_object.offer_availability
                except Offers.DoesNotExist:
                    pass
                self.context_data['offer_subtags'] = result_list_tags
                self.context_data['offer_availability_all'] = Availability.objects.all()

            template = loader.get_template(self.URL_TO_TEMPLATES + file_name_template)
            return HttpResponse(template.render(self.context_data, request))
        return HttpResponseForbidden()

    def post(self, request):
        file_name_template = request.path.split('/')[-1]
        if file_name_template in self.ADMIN_EDIT_FORM:
            form = self.ADMIN_EDIT_FORM[file_name_template]
            form().save_to_database(request)
            return HttpResponse('Данные успешно сохранены')
        return HttpResponseForbidden()

    def __init__(self, *args, **kwargs):
        self.context_data = {}
