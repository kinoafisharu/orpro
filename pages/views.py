# -*- coding: utf-8 -*-
import os
import json
import urllib

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.views import View
from django.views.generic import UpdateView, FormView
from django.conf import settings
from django.contrib import messages
from django.forms import formset_factory, modelformset_factory
from django.db.models import Q, F, Avg
from django.core.urlresolvers import reverse
from .models import Reviews, Post, Tags, Category, Offers, Subtags, MainBaner, FBlocks, LBlocks, AboutCompany, \
    TopOffers, Support, Personal, Company, HeaderPhoto, Images
from .forms import *
import boto3
from .models import *
from django.utils.datastructures import MultiValueDictKeyError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from urllib.parse import urlsplit
import requests
from pages.import_export_views import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from pages.utils.ajax import BaseAjaxView

from pages.data_box import pars_cat, pars_goods


def api_import(request):
    offers_list = Offers.objects.all().order_by("-created")
    page = request.GET.get('page', 1)

    paginator = Paginator(offers_list, 10)
    try:
        offers = paginator.page(page)
    except PageNotAnInteger:
        offers = paginator.page(1)
    except EmptyPage:
        offers = paginator.page(paginator.num_pages)
    field = [f.name for f in Offers._meta.get_fields()]
    if request.POST:
        if "upload" in request.POST:
            for i in offers_list:
                if i.offer_image_url and not i.offer_photo:
                    r = requests.get(i.offer_image_url, verify=False)
                    if r.status_code == requests.codes.ok:
                        img_temp = NamedTemporaryFile()
                        img_temp.write(r.content)
                        img_temp.flush()
                        img_filename = urlsplit(i.offer_image_url).path[1:]
                        i.offer_photo.save(img_filename, File(img_temp), save=True)
                    continue
            messages.success(request, "Фото загружено")
            return render(request, 'api.html', locals())
        else:
            try:
                file = request.FILES['file']
                format_file = request.POST.get("file_format", False)
                if file.name.split(".")[-1].lower() != format_file:
                    messages.error(request, "Формат файла не подходит!")
                else:
                    uploading_file = UploadingProducts({'file': file, 'format_file': format_file})
                    if uploading_file.parsing():
                        messages.success(request, "Загружено и обновлено. {}".format(
                            uploading_file.add if uploading_file.add else ""))
                    else:
                        messages.error(request, "Ошибка. Нет поля: {}".format(uploading_file.err))
            except MultiValueDictKeyError:
                messages.error(request, "Выберите файл!")
    return render(request, 'api.html', locals())


def review(request):
    args = {}

    form = ReviewsForm()
    args['form'] = form
    if 'submit' in request.POST:
        form = ReviewsForm(request.POST)
        if form.is_valid():
            recaptcha_response = request.POST.get('g-recaptcha-response')  # запрос на передачу данных серверу recaptcha
            url = 'https://www.google.com/recaptcha/api/siteverify'
            # данные для передачи на сервер
            values_responce = {
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            # декодирование данных для передачи
            data = urllib.parse.urlencode(values_responce).encode()
            # запрос от сервера после передачи данных
            req = urllib.request.Request(url, data=data)
            # декодирование результата запроса req
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            cd = form.cleaned_data
            name = cd['name']
            email = cd['email']
            text = cd['text']
            g = Reviews(name=name, email=email, text=text, publish=True)

            if result['success']:
                g.save()
                # args['message'] = 'Спасибо за отзыв'
            else:
                args['message'] = 'Отметьте флажок с фразой "Я не робот"'
    else:
        form = ReviewsForm()

    args['hf'] = HeaderPhoto.objects.get(id=1)

    args['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0)).order_by('post_priority')
    args['reviews'] = Reviews.objects.filter(publish=True).order_by('-date')
    args['tags'] = Subtags.objects.all().order_by('?')[0:100]
    return render(request, 'reviews.html', args)


class AdminAjaxEditForm(BaseAjaxView):
    URL_TO_TEMPLATES = 'forms/admin-ajax/'
    ADMIN_EDIT_FORM = {
        'ac_form.html': AboutCompanyForm,
        'hp_form.html': HeaderPhotoForm,
        'to_form.html': TopOffersForm,
        'sup_form.html': SupportForm,
        'lb_form.html': LBlocksForm,
        'fb_form.html': FBlocksForm,
        'subtag_form.html': SubtagsForCatalog,
        'subtag_offer_form.html': SubtagsForm,
        'offer-edit.html': OfferForm,
        'price-edit.html': PriceForm,
        'footer-text-block.html': CategoryFooterTextForm
    }


def comment_delete(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            data = request.POST
            Reviews.objects.get(id=data.get("id")).delete()
            response_data["id"] = data.get("id")
            return JsonResponse(response_data)
    return HttpResponseForbidden()


def comment_admin(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = Reviews.objects.get(id=post_text.get("edit")).id
            Reviews.objects.filter(id=f).update(comment=post_text["comment"])
            response_data['comment'] = Reviews.objects.get(id=f).comment
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
                comment_initial = Reviews.objects.get(id=id_edit)
            form = CommentAdminForm(initial={'comment': comment_initial.comment})
            return render(request, 'comment_admin_form.html', locals())
    return HttpResponseForbidden()


def p_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            post_file = request.FILES
            print(post_text)
            f = Personal.objects.get(id=post_text.get("edit")).id
            Personal.objects.filter(id=f).update(p_name=post_text["p_name"], p_doljnost=post_text["p_doljnost"],
                                                 p_photo=post_file["p_photo"])
            response_data['p_name'] = Personal.objects.get(id=f).p_name
            response_data['p_doljnost'] = Personal.objects.get(id=f).p_doljnost
            response_data['p_photo'] = Personal.objects.get(id=f).p_photo.url
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            p_initial = Personal.objects.get(id=id_edit)
            form = PersonalForm(initial={'p_name': p_initial.p_name, 'p_doljnost': p_initial.p_doljnost,
                                         'p_photo': p_initial.p_photo.url})
            return render(request, 'p_form.html', locals())
    return HttpResponseForbidden()


def company_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = Company.objects.get(id=post_text.get("edit")).id
            Company.objects.filter(id=f).update(name=post_text["name"], email=post_text["email"],
                                                address=post_text["address"], skype=post_text["skype"],
                                                mob_phone=post_text["mob_phone"], rob_phone=post_text["rob_phone"],
                                                facebook_link=post_text["facebook_link"],
                                                twitter_link=post_text["twitter_link"])
            response_data['name'] = Company.objects.get(id=f).name
            response_data['email'] = Company.objects.get(id=f).email
            response_data['address'] = Company.objects.get(id=f).address
            response_data['skype'] = Company.objects.get(id=f).skype
            response_data['mob_phone'] = Company.objects.get(id=f).mob_phone
            response_data['rob_phone'] = Company.objects.get(id=f).rob_phone
            response_data['facebook_link'] = Company.objects.get(id=f).facebook_link
            response_data['twitter_link'] = Company.objects.get(id=f).twitter_link
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            company_initial = Company.objects.get(id=id_edit)
            form = CompanyForm(initial={'name': company_initial.name, 'email': company_initial.email,
                                        'address': company_initial.address, 'skype': company_initial.skype,
                                        'mob_phone': company_initial.mob_phone, 'rob_phone': company_initial.rob_phone,
                                        'facebook_link': company_initial.facebook_link,
                                        'twitter_link': company_initial.twitter_link})
            return render(request, 'company_form.html', locals())
    return HttpResponseForbidden()


class Home(View):
    template_name = 'home.html'

    def get(self, request):
        return render(request, self.template_name, self.context_data)

    @property
    def get_static_context(self):
        self.context_data['fb_elements'] = FBlocks.objects.all()[:4]
        self.context_data['lb_elements'] = LBlocks.objects.all()[:4]

        self.context_data['form'] = FBlocksForm()
        self.context_data['baner'] = MainBaner.objects.all()
        self.context_data['TO'] = TopOffers.objects.all()
        self.context_data['sup'] = Support.objects.all()[0]
        self.context_data['p'] = Personal.objects.all()
        self.context_data['ac1'] = AboutCompany.objects.get(id=1)
        self.context_data['hf'] = HeaderPhoto.objects.get(id=1)
        # self.context_data['company'] = Company.objects.get(id=1)
        self.context_data['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0)).order_by('post_priority')

    def __init__(self, *args, **kwargs):
        ''' Each time the class is initialized, it is required to clear the context variable '''
        self.context_data = {}
        self.get_static_context


def get_signature(request):
    company = get_object_or_404(Company, id=1)
    return render(request, 'signature.html', company)


# def singlepage(request, post_seourl):
#     args = {}
#
#     args['hf'] = HeaderPhoto.objects.get(id=1)
#
#     args['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0))
#     args['post'] = Post.objects.get(post_seourl=post_seourl)
#     args['tags'] = Subtags.objects.all().order_by('?')[0:100]
#
#     return render(request, 'singlpage.html', args)

class SinglePageAjaxUpdateView(UpdateView):
    queryset = Post.objects.all()
    form_class = SinglePageForm
    slug_field = "post_seourl"
    slug_url_kwarg = "post_seourl"
    template_name = "singlpage.html"
    ajax_template_name = "forms/edit-single-page.html"

    # When you save changes to the form, a page with changes is displayed, and "edit" = 0
    is_already_save = False

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().post(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
            'instance': self.object
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def form_valid(self, form):
        form.save()
        self.is_already_save = True
        return self.render_to_response(self.get_context_data(form=self.form_class(instance=self.object)))

    def get_template_names(self):
        if self.request.is_ajax():
            return self.ajax_template_name
        return self.template_name

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not self.request.is_ajax():
            ctx['hf'] = HeaderPhoto.objects.get(id=1)
            ctx['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0)).order_by('post_priority')
            ctx['post'] = Post.objects.get(post_seourl=self.object.post_seourl)
            ctx['tags'] = Subtags.objects.all().order_by('?')[0:100]

        ctx['post_title'] = self.object

        if self.request.user.is_superuser:
            if 'edit' in self.request.GET and not self.is_already_save:
                ctx['edit'] = True
        return ctx


class OfferAjaxUpdateView(UpdateView):
    queryset = Offers.objects.all()
    form_class = OfferForm
    slug_field = "offer_url"
    slug_url_kwarg = "off_url"
    template_name = "offer.html"

    # ajax_template_name = "forms/offer-form.html"

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().post(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
            'instance': self.object
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        images = context['images']

        form.save()
        if images.is_valid():
            images.save()
        else:
            print(images.errors)
        return self.render_to_response(self.get_context_data(form=form))

    def get_template_names(self):
        #    if self.request.is_ajax():
        #        return self.ajax_template_name
        return self.template_name

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not self.request.is_ajax():
            ctx['hf'] = HeaderPhoto.objects.get(id=1)
            ctx['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0)).order_by('post_priority')
            ctx['tags'] = Tags.objects.filter(tag_publish=True).order_by('tag_priority')
            # ctx['subtags'] = Subtags.objects.filter(tag_parent_tag=self.object.offer_subtags)\
            #    .order_by('tag_priority')[0:100]
        ctx['subtags'] = self.object.offer_subtags.all()
        ctx['offer'] = self.object

        if self.request.user.is_superuser:
            ctx['images'] = ImageFormSet(instance=self.object)
            if 'edit' in self.request.GET:
                ctx['edit'] = True
        return ctx


class OfferImagesAjaxUpdateView(FormView):
    http_method_names = ['post', 'get']
    form_class = ImageFormSet
    slug_field = "off_url"
    template_name = 'images_inline_form.html'

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser:
            super().post(request, *args, **kwargs)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
        return HttpResponseForbidden()

    def dispatch(self, request, *args, **kwargs):
        slug = kwargs.get(self.slug_field)
        self.object = get_object_or_404(Offers, offer_url=slug)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return self.render_to_response(self.get_context_data(form=self.form_class(instance=self.object)))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['images'] = ctx['form']
        print(ctx)
        return ctx

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = {'initial': self.get_initial(), 'instance': self.object}
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs


def catalog(request, cat_url='nothing'):
    sort_by = request.GET.get('sort_by', 'priority')

    search_title = request.GET.get('search_title', '')
    if len(search_title) < 2:
        search_title = None

    search_price_from = request.GET.get('search_price_from', None)
    try:
        int(search_price_from)
    except Exception:
        search_price_from = None

    search_price_to = request.GET.get('search_price_to', None)
    try:
        int(search_price_to)
    except Exception:
        search_price_to = None

    if cat_url == 'nothing':
        cat_url = Tags.objects.filter(tag_publish=True).order_by('tag_priority')[0].tag_url
    args = {}
    try:
        args['pre'] = 'Группа товаров'
        mt = Tags.objects.get(tag_url=cat_url)
        offers = Offers.objects.filter(offer_tag=mt)
        args['subtags'] = Subtags.objects.filter(tag_parent_tag=mt).order_by('tag_priority')[0:100]
    except Exception:
        args['pre'] = 'КЛЮЧЕВОЕ СЛОВО'
        print(cat_url)
        mt = Subtags.objects.get(tag_url=cat_url)
        offers = Offers.objects.filter(offer_subtags=mt)

        args['subtags'] = Subtags.objects.filter(tag_parent_tag=mt.tag_parent_tag).order_by('tag_priority')[0:100]

    args['hf'] = HeaderPhoto.objects.get(id=1)

    if search_title is not None:
        offers = offers.filter(offer_title__icontains=search_title)

    if search_price_from is not None:
        offers = offers.filter(
            prices__price_type__is_default=True,
            prices__value__gte=search_price_from)

    if search_price_to is not None:
        offers = offers.filter(
            prices__price_type__is_default=True,
            prices__value__lte=search_price_to)

    if sort_by == 'name':
        offers = sorted(offers, key=lambda x: x.offer_title)

    elif sort_by == 'priority':
#        offers = offers.annotate(priority=models.Sum('offer_subtags__tag_priority')(models.Count('offer_subtags') or 0)).order_by('priority')
# Изменение Иванова Михаила
        offers = sorted(Offers.objects.aggregate.offer_subtags(Avg('priority')))

    elif sort_by == 'price':
        offers = offers.extra(select={
            'default_price': """
                SELECT p.value
                FROM pages_price AS p
                LEFT JOIN pages_pricetype AS pt on p.price_type_id = pt.id
                WHERE pt.is_default = TRUE 
                AND p.offer_id = pages_offers.id
            """
        }).order_by('default_price')

    args['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0)).order_by('post_priority')
    args['offer'] = offers
    args['cat_title'] = mt
    args['tags'] = Tags.objects.filter(tag_publish=True).order_by('tag_priority')
    args['company'] = Company.objects.get(id=1)
    args['sort'] = sort_by
    args['category_page'] = True
    args['search_title'] = search_title if search_title is not None else ''
    args['search_price_from'] = search_price_from if search_price_from is not None else ''
    args['search_price_to'] = search_price_to if search_price_to is not None else ''

    return render(request, 'catalog.html', args)
