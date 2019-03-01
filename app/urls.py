"""cmsproj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.conf.urls import url, include
	2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.simple import direct_to_template

urlpatterns = [
	url(r'^admin/', admin.site.urls),
	url(r'^summernote/', include('django_summernote.urls')),
	#url(r'^tinymce/', include('tinymce.urls')),
	url(r'^captcha/', include('captcha.urls')),
	url(r'^', include('pages.urls')),
	(r'^robots\.txt$', direct_to_template,
     {'template': 'robots.txt', 'mimetype': 'text/plain'}),
]
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
