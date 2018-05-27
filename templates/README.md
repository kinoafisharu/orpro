# Templates

* [base/](.#base-id)
* [forms/](.#forms)
  * [admin-ajax/](.#admin-ajax)
* [lists/](.#lists)

***
# Base
  Базовые шаблоны, от которых наследуются остальные


# Forms
### admin-ajax
  В папке находятся шаблоны, которые необходимы для отображения формы "быстрого редактирования"

##### Простой пример использования:

```python
#pages/forms.py
from pages.utils.ajax import FormAjaxBase
from pages.models import TestModel

class EditForm(FormAjaxBase):
  class Meta:
    model = TestModel
    fields = ['title', 'text']
```

Во `views.py` прописывается название формы, и путь к `html` файлу.

```python
#pages/views.py
from pages.utils.ajax import BaseAjaxView

class AdminAjaxEditForm(BaseAjaxView):
  URL_TO_TEMPLATES = 'forms/admin-ajax/'
  ADMIN_EDIT_FORM = {
    'edit_form.html': EditForm
}
```

```html
<!-- templates/forms/admin-ajax/edit_form.html -->
<div class="admin-form-group">
    <input type="hidden" name="template-name-edit" value="{{ template_send }}">
    <div><input type="hidden" name="model-id" value="{{ model_id }}"></div>
    <div>Название: <p style="color: black">{{ form.title }}</p></div>
    <div>Текст: <p style="color: black"> {{ form.text }}</p></div>

    <div><button class="home-button" type="submit">Сохранить</button></div>
</div>
```

Готово. Теперь остаётся в шаблоне, где выводятся поля из модели (`TestModel`), подставить кнопку.

```html
  {% for model in models %}
    <h1>{{model.title}}</h1>
    <p>{{model.text}}</p>

    <a href="javascript:viewFormEdit('custom-name-{{ model.id }}');"
      id="custom-name-{{ model.id }}"
      data-template-name="fb_form.html"
      data-model-id="{{ model.id }}">
  {% endfor %}
```Каталог
В конечном итоге, после нажатия на кнопку, появляется `pop-up` форма. Отправка данных выполняется посредством **AJAX**. Если данные успешно сохранены, страница перезагружается.

<!--![Скриншот формы](//media/1_0.png "Можно задать title")-->




# Lists
Список меню в каталоге и теги в облаке
