from django import forms
from django.forms import widgets
from django.core.urlresolvers import reverse
from django.forms import formset_factory
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django.core.files.storage import default_storage as storage

# from tinymce.widgets import TinyMCE
from django_summernote.widgets import SummernoteWidget

from pages.utils.ajax import FormAjaxBase
from .models import *

SUMMERNOTE_ATTRS = {'toolbar': [
    ['style', ['style']],
    ['font', ['bold', 'italic', 'underline', 'clear']],
    ['font', ['fontsize', 'color']],
    ['para', ['paragraph']],
    ['insert', ['picture', 'link', 'video', 'hr']],
    ['misc', ['codeview', 'undo', 'redo']],
]}

SUMMERNOTE_SUBTAGS_ATTRS = {'toolbar': [
    ['style', ['style']],
    ['font', ['bold', 'italic', 'underline', 'clear']],
    ['insert', ['link']],
    ['misc', ['codeview', 'undo', 'redo']],
]}


class CommentAdminForm(forms.ModelForm):
    class Meta:
        model = Reviews
        fields = ['comment']
        widgets = {
            'comment': SummernoteWidget(attrs=SUMMERNOTE_ATTRS),
        }


class ReviewsForm(forms.Form):
    class Meta:
        model = Reviews

    name = forms.CharField(label='Ваше Имя', max_length=150, required=False)
    email = forms.CharField(label='Email', max_length=100, required=False)
    text = forms.CharField(label='Отзыв', widget=forms.Textarea)


class FBlocksForm(FormAjaxBase):
    class Meta:
        model = FBlocks
        fields = ['fb_title', 'fb_text', 'fb_icon', 'fb_color', 'fb_url']
        widgets = {
            'fb_text': SummernoteWidget(attrs=SUMMERNOTE_ATTRS),
            'fb_color': forms.TextInput(attrs={'placeholder': '#000..., rgb(...) or rgba(...)'}),
            'fb_icon': forms.TextInput(attrs={'placeholder': 'fa-example'})
        }


class LBlocksForm(FormAjaxBase):
    class Meta:
        model = LBlocks
        fields = ['lb_title', 'lb_text', 'lb_icon', 'lb_color', 'lb_link']
        widgets = {
            'lb_text': SummernoteWidget(attrs=SUMMERNOTE_ATTRS),
            'lb_color': forms.TextInput(attrs={'placeholder': '#000..., rgb(...) or rgba(...)'}),
            'lb_icon': forms.TextInput(attrs={'placeholder': 'fa-example'})
        }


class AboutCompanyForm(FormAjaxBase):
    class Meta:
        model = AboutCompany
        fields = ['ac_title', 'ac_text']
        widgets = {
            'ac_text': SummernoteWidget(attrs=SUMMERNOTE_ATTRS),
        }


class TopOffersForm(FormAjaxBase):
    class Meta:
        model = TopOffers
        fields = ['to_title', 'to_link']


class SupportForm(FormAjaxBase):
    class Meta:
        model = Support
        fields = ['sup_title', 'sup_time', 'sup_slogan', 'sup_phone']


class PersonalForm(forms.ModelForm):
    class Meta:
        model = Personal
        fields = ['p_name', 'p_doljnost', 'p_photo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'email', 'skype', 'address',
            'mob_phone', 'rob_phone', 'facebook_link',
            'twitter_link'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


HEADER_PHOTO_FORM = ['hp_name', 'hp_photo']


class HeaderPhotoForm(FormAjaxBase):
    class Meta:
        model = HeaderPhoto
        fields = HEADER_PHOTO_FORM

    def __init__(self, model_initial=None, *args, **kwargs):
        if model_initial is not None:
            super().__init__(initial={HEADER_PHOTO_FORM[0]: model_initial.hp_name,
                                      HEADER_PHOTO_FORM[1]: model_initial.hp_photo}, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


OFFER_FORM = ['offer_title', 'offer_value', 'offer_text',
              'offer_url', 'offer_availability', 'offer_subtags', 'offer_photo']


class OfferForm(FormAjaxBase):
    class Meta:
        model = Offers
        fields = OFFER_FORM

        widgets = {
            'offer_text': SummernoteWidget(attrs=SUMMERNOTE_ATTRS),
            'offer_photo': forms.FileInput(attrs={'id': 'id-ajax-save-file'}),
        }

    def __init__(self, model_initial=None, *args, **kwargs):
        # super().__init__(*args, **kwargs)

        if model_initial is not None:
            super().__init__(
                initial={OFFER_FORM[0]: model_initial.offer_title, OFFER_FORM[1]: model_initial.offer_value, 
                         OFFER_FORM[2]: model_initial.offer_text,
                         OFFER_FORM[3]: model_initial.offer_url, OFFER_FORM[4]: model_initial.offer_availability,
                         OFFER_FORM[6]: model_initial.offer_photo}, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


SUBTAG_MAIN_FIELDS = ['tag_url', 'tag_title', 'tag_priority']


class SubtagsForm(FormAjaxBase):
    class Meta:
        model = Subtags
        fields = SUBTAG_MAIN_FIELDS
        # widgets = {
        #    'delete_stag': forms.CheckboxInput(attrs={'class': 'main-check'})
        # }

    def __init__(self, model_initial=None, *args, **kwargs):
        if model_initial is not None:
            super().__init__(initial={SUBTAG_MAIN_FIELDS[0]: model_initial.tag_url,
                                      SUBTAG_MAIN_FIELDS[1]: model_initial.tag_title,
                                      SUBTAG_MAIN_FIELDS[3]: model_initial.tag_priority}, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


SUBTAGS_FIELDS_CATALOG = ['tag_url', 'tag_title', 'tag_description', 'tag_image', 'tag_priority']


class SubtagsForCatalog(FormAjaxBase):
    class Meta:
        model = Subtags
        fields = SUBTAGS_FIELDS_CATALOG
        widgets = {
            'tag_description': SummernoteWidget(attrs=SUMMERNOTE_SUBTAGS_ATTRS),
            'tag_image': forms.FileInput(attrs={'id': 'id-ajax-save-file'})
        }

    def __init__(self, model_initial=None, *args, **kwargs):
        if model_initial is not None:
            super().__init__(initial={SUBTAGS_FIELDS_CATALOG[0]: model_initial.tag_url,
                                      SUBTAGS_FIELDS_CATALOG[1]: model_initial.tag_title,
                                      SUBTAGS_FIELDS_CATALOG[2]: model_initial.tag_description,
                                      SUBTAGS_FIELDS_CATALOG[4]: model_initial.tag_priority,
                                      SUBTAGS_FIELDS_CATALOG[3]: model_initial.tag_image}, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


class SinglePageForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['post_text', 'post_title', 'post_cat_level', 'post_priority']
        widgets = {
            'post_text': SummernoteWidget(attrs={'rows': 45}),
        }


class TagsForm(forms.ModelForm):
    class Meta:
        model = Tags
        fields = ['tag_title', 'tag_url', 'tag_priority', 'delete_tag']
        widgets = {
            'delete_tag': forms.CheckboxInput(attrs={'class': 'main-check'})
        }


class ImageForm(forms.ModelForm):
    max_width = forms.IntegerField(
        label='Ширина',
        widget=forms.NumberInput(attrs={'style': 'width:100px', 'data-toggle': 'tooltip', 'data-placement': 'top'}),
        required=False,
        min_value=1,
        help_text='измените один из размеров'
    )
    max_height = forms.IntegerField(
        label='Высота',
        widget=forms.NumberInput(attrs={'style': 'width:100px', 'data-toggle': 'tooltip', 'data-placement': 'top'}),
        required=False,
        min_value=1,
        help_text='измените один из размеров'
    )

    class Meta:
        model = Images
        exclude = ('offer', 'id')

        labels = {
            'images_url': 'Ссылка на изображение',
            'images_file': 'Загрузка файла',
            'main': 'Главная',
            'delete': 'Удалить'
        }

        widgets = {
            'images_file': forms.FileInput(),
            'main': forms.CheckboxInput(attrs={'class': 'main-check'})
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        # r = kwargs.get('request')
        if self.instance:
            try:
                # Было (os.path.isfile(self.instance.images_file.path))
                # Для доступа к S3 AWS используется storages
                # - метода isfile нет в пакете, используется метод open;
                # - отлавдивается ошибка OSerror, если файл отсутсвует;
                # - если файл открываеться, применяются настройки к картинке ниже.
                if self.instance.images_file and storage.open(self.instance.images_file.name):
                    base_attrs = {
                        'min': 1, 'max': '', 'style': 'width:100px', 'data-toggle': 'tooltip',
                        'data-placement': 'top', 'title': 'измените один из размеров'
                    }

                    base_attrs['max'] = self.instance.images_file.width
                    self.fields['max_width'].widget = forms.NumberInput(attrs=base_attrs)
                    self.fields['max_width'].initial = self.instance.images_file.width

                    base_attrs['max'] = self.instance.images_file.height
                    self.fields['max_height'].widget = forms.NumberInput(attrs=base_attrs)
                    self.fields['max_height'].initial = self.instance.images_file.height

                if self.instance.images_file and not self.instance.images_url:
                    self.fields['images_url'].widget = forms.TextInput(
                        attrs={'placeholder': self.instance.images_file.url})
            except OSError as err:
                raise forms.ValidationError('File missing')

    def clean(self):
        cleaned_data = super().clean()
        images_url = cleaned_data.get("images_url")
        images_file = cleaned_data.get("images_file")
        if not images_url and not images_file:
            # Only do something if both fields are valid so far.

            raise forms.ValidationError(
                "One of the field images_url or images_file must be filled"
            )

    def save(self, commit=True):
        """
        Save this form's self.instance object if commit=True. Otherwise, add
        a save_m2m() method to the form which can be called after the instance
        is saved manually at a later time. Return the model instance.
        """
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )
        max_w = self.cleaned_data.get('max_width', 0) if self.cleaned_data.get('max_width') else 0
        max_h = self.cleaned_data.get('max_height', 0) if self.cleaned_data.get('max_height', 0) else 0
        if commit:
            # If committing, save the instance and the m2m data immediately.
            self._save_m2m()
            #raise commit
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.save_m2m = self._save_m2m
        self.instance.save(max_width=max_w, max_height=max_h)
        return self.instance


ImageFormSet = forms.inlineformset_factory(Offers, Images, ImageForm)


class PriceForm(FormAjaxBase):
    class Meta:
        model = Price
        fields = ('price_type', 'value',)

    def get_context(self):
        return {
            'price_types': PriceType.objects.all()
        }

    def save_to_database(self, request):
        model_id = request.POST.get('model-id', None)
        offer_id = request.POST.get('offer-id', None)

        try:
            int(model_id)
        except Exception:
            model_id = None

        if model_id is not None:
            exist_model = self.Meta.model.objects.get(id=model_id)
        else:
            exist_model = self.Meta.model()
            exist_model.offer_id = offer_id

        delete = True if request.POST.get('delete', False) == 'on' else False
        if delete:
            exist_model.delete()
            return

        exist_model.value = request.POST.get('value', None)
        exist_model.price_type_id = request.POST.get('price_type_id', None)
        exist_model.offer_id = offer_id

        exist_model.save()


class CategoryFooterTextForm(FormAjaxBase):

    class Meta:
        model = Tags
        fields = ('footer_text',)

        widgets = {
            'footer_text': SummernoteWidget(attrs=SUMMERNOTE_ATTRS)
        }

    def __init__(self, model_initial_id=None, *args, **kwargs):
        obj = self.Meta.model.objects.filter(id=model_initial_id).first()

        if obj is not None:
            super().__init__(*args, model_initial_id=model_initial_id, **kwargs)
        else:
            super().__init__(*args, **kwargs)
