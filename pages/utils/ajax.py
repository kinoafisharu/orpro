from django import forms, views
from django.template import loader
from django.http import HttpResponse, HttpResponseForbidden


__all__ = ('FormAjaxBase', )


class FormAjaxBase(forms.ModelForm):
    def get_model_object(self, *args):
        pass

    def save_to_database(self, request):
        model_id = request.POST.get('model-id', None)
        if model_id is not None:
            try:
                exist_model = self.__model_class.objects.get(id=model_id)
            except self.__model_class.DoesNotExist:
                raise IndexError('Model not found')

            for field_model in self.__list_fields:
                exist_model.__dict__[field_model] = request.POST[field_model]
            exist_model.save()
        else:
            raise AttributeError('Field "model-id" not found.')



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
                initial_dict[field_name] = form_initial.__dict__[field_name]

            super().__init__(initial=initial_dict, *args, **kwargs)
        #else:
        #    raise ValueError('The variable "model_initial_id" has an empty value')



class BaseAjaxView(views.View):
    def get(self, request):
        file_name_template = request.path.split('/')[-1]

        if file_name_template in self.ADMIN_EDIT_FORM:

            class_form = self.ADMIN_EDIT_FORM[file_name_template]
            model_id = request.GET.get('model-id', None)

            self.context_data['form'] = class_form(model_initial_id=model_id)
            self.context_data['template_send'] = file_name_template
            self.context_data['model_id'] = model_id

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
