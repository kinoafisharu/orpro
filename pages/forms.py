from django import forms
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.bootstrap import Field, InlineRadios, TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Fieldset
from django.core.files.storage import default_storage as storage
from tinymce.widgets import TinyMCE

from captcha.fields import CaptchaField

from .models import Reviews, Offers, Images


class ReviewsForm(forms.Form):

    captcha = CaptchaField()

    class Meta:
        model = Reviews

    name = forms.CharField(label='Ваше Имя', max_length=150, required=False)
    email = forms.CharField(label='Email', max_length=100, required=False)
    text = forms.CharField(label='Отзыв', widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(ReviewsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper ()
        self.helper.form_id = 'id-personal-data-form'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse ('review')
        self.helper.add_input (Submit ('submit', 'Добавить', css_class='btn-success '))
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout(
            Fieldset('',
                    Field ('name', placeholder=''),
                    Field ('email', placeholder=''),
                    Field ('number', placeholder=''),
                    Field ('text', placeholder=''),
                    ))


class OfferForm(forms.ModelForm):

    class Meta:
        model = Offers
        fields = ['offer_title', 'offer_minorder', 'offer_minorder_value',
                  'offer_availability', 'offer_article', 'offer_price',
                  'offer_price_from', 'offer_price_to', 'offer_text']

        widgets = {
            'offer_text': TinyMCE(attrs={'rows': 45}),
        }

    class Media:
        js = ('/static/js/tiny_mce/tiny_mce.js',
              '/static/js/tiny_mce/textareas.js',)


class ImageForm(forms.ModelForm):

    max_width = forms.IntegerField(
        label='Ширина',
        widget=forms.NumberInput(attrs={'style': 'width:100px', 'data-toggle':'tooltip', 'data-placement':'top'}),
        required=False,
        min_value=1,
        help_text='измените один из размеров'
    )
    max_height = forms.IntegerField(
        label='Высота',
        widget=forms.NumberInput(attrs={'style': 'width:100px', 'data-toggle':'tooltip', 'data-placement':'top'}),
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
        #r = kwargs.get('request')
        if self.instance:
            try:
                # Было (os.path.isfile(self.instance.images_file.path))
                # Для доступа к S3 AWS используется storages
                # - метода isfile нет в пакете, используется метод open;
                # - отлавдивается ошибка OSerror, если файл отсутсвует;
                # - если файл открываеться, применяются настройки к картинке ниже.
                if self.instance.images_file and storage.open(self.instance.images_file.name):
                    base_attrs = {'min': 1, 'max': '', 'style': 'width:100px', 'data-toggle':'tooltip', 'data-placement':'top', 'title': 'измените один из размеров'}

                    base_attrs['max'] = self.instance.images_file.width
                    self.fields['max_width'].widget = forms.NumberInput(attrs=base_attrs)
                    self.fields['max_width'].initial = self.instance.images_file.width

                    base_attrs['max'] = self.instance.images_file.height
                    self.fields['max_height'].widget = forms.NumberInput(attrs=base_attrs)
                    self.fields['max_height'].initial = self.instance.images_file.height

                if self.instance.images_file and not self.instance.images_url:
                    self.fields['images_url'].widget = forms.TextInput(attrs={'placeholder': self.instance.images_file.url})
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
            raise commit
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.save_m2m = self._save_m2m
        self.instance.save(max_width=max_w, max_height=max_h)
        return self.instance


ImageFormSet = forms.inlineformset_factory(Offers, Images, ImageForm)