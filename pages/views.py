# -*- coding: utf-8 -*-
import os
import json
import urllib
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.views.generic import UpdateView, FormView
from django.conf import settings
from django.contrib import messages
from django.forms import formset_factory, modelformset_factory
from django.db.models import Q
from django.core.urlresolvers import reverse
from .models import Reviews, Post, Tags, Category, Offers, Subtags, MainBaner, FBlocks, LBlocks, AboutCompany, \
    TopOffers, Support, Personal, Company, HeaderPhoto, Images
from .forms import *
import boto3
from .models import *
from django.utils.datastructures import MultiValueDictKeyError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.shortcuts import get_object_or_404
from urllib.parse import urlsplit
import requests
from pages.import_export_views import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def api_import(request):
    offers_list = Offers.objects.all()
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
                    if uploading_file:
                        messages.success(request, "Загружено")
                    else:
                        messages.error(request, "Ошибка")
            except MultiValueDictKeyError:
                messages.error(request, "Выберите файл!")
    return render(request, 'api.html', locals())

def review(request):
    args = {}

    form = ReviewsForm()
    args['form'] = form
    if 'submit' in request.POST:
        form = ReviewsForm(request.POST)
        print('POST')
        if form.is_valid():
            print('valid')
            recaptcha_response = request.POST.get('g-recaptcha-response') # запрос на передачу данных серверу recaptcha
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

    args['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0))
    args['reviews'] = Reviews.objects.filter(publish=True).order_by('-date')
    args['tags'] = Subtags.objects.all().order_by('?')[0:100]
    print(args)
    return render(request, 'reviews.html', args)


def fb_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = FBlocks.objects.get(id=post_text.get("edit")).id
            FBlocks.objects.filter(id=f).update(fb_title=post_text["fb_title"], fb_text=post_text["fb_text"], fb_url=post_text["fb_url"])
            response_data['fb_title'] = FBlocks.objects.get(id=f).fb_title
            response_data['fb_text'] = FBlocks.objects.get(id=f).fb_text
            response_data['fb_url'] = FBlocks.objects.get(id=f).fb_url
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
            id_edit = request.GET["edit"]
            fb_initial = FBlocks.objects.get(id=id_edit)
            form = FBlocksForm(
                initial={'fb_title': fb_initial.fb_title, 'fb_text': fb_initial.fb_text, 'fb_url': fb_initial.fb_url})

            return render(request, 'fb_form.html', locals())
    return HttpResponseForbidden()


def stag_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = Subtags.objects.get(id=post_text.get("edit")).id
            Subtags.objects.filter(id=f).update(tag_title=post_text["tag_title"], tag_url=post_text["tag_url"],
                                                tag_parent_tag=post_text["tag_parent_tag"])
            response_data['tag_title'] = Subtags.objects.get(id=f).tag_title
            response_data['tag_url'] = Subtags.objects.get(id=f).tag_url
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                id_edit = request.GET["edit"]
            stag_initial = Subtags.objects.get(id=id_edit)
            form = SubtagsForm(
                initial={'tag_title': stag_initial.tag_title, 'tag_url': stag_initial.tag_url, 'tag_parent_tag ': stag_initial.tag_parent_tag})
            return render(request, 'stag_form.html', locals())
    return HttpResponseForbidden()


def hp_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            post_file = request.FILES
            print(post_text)
            f = HeaderPhoto.objects.get(id=post_text.get("edit")).id
            HeaderPhoto.objects.filter(id=f).update(hp_name=post_text["hp_name"], hp_photo=post_file["hp_photo"])
            response_data['hp_name'] = HeaderPhoto.objects.get(id=f).hp_name
            response_data['hp_photo'] = HeaderPhoto.objects.get(id=f).hp_photo.url
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            hp_initial = HeaderPhoto.objects.get(id=id_edit)
            hp_photo_url = hp_initial.hp_photo.url
            form = HeaderPhotoForm(initial={'hp_name': hp_initial.hp_name, 'hp_photo': hp_initial.hp_photo })
            return render(request, 'hp_form.html', locals())
    return HttpResponseForbidden()


def lb_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = LBlocks.objects.get(id=post_text.get("edit")).id
            LBlocks.objects.filter(id=f).update(lb_title=post_text["lb_title"], lb_text=post_text["lb_text"],
                                                lb_icon=post_text["lb_icon"], lb_link=post_text["lb_link"])
            response_data['lb_title'] = LBlocks.objects.get(id=f).lb_title
            response_data['lb_text'] = LBlocks.objects.get(id=f).lb_text
            response_data['lb_icon'] = LBlocks.objects.get(id=f).lb_icon
            response_data['lb_link'] = LBlocks.objects.get(id=f).lb_link
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            lb_initial = LBlocks.objects.get(id=id_edit)
            form = LBlocksForm(initial={'lb_title': lb_initial.lb_title, 'lb_text': lb_initial.lb_text,'lb_icon': lb_initial.lb_icon,'lb_link': lb_initial.lb_link})
            return render(request, 'lb_form.html', locals())
    return HttpResponseForbidden()



def ac_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = AboutCompany.objects.get(id=post_text.get("edit")).id
            AboutCompany.objects.filter(id=f).update(ac_title=post_text["ac_title"], ac_text=post_text["ac_text"])
            response_data['ac_title'] = AboutCompany.objects.get(id=f).ac_title
            response_data['ac_text'] = AboutCompany.objects.get(id=f).ac_text
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            ac_initial = AboutCompany.objects.get(id=id_edit)
            form = AboutCompanyForm(initial={'ac_title': ac_initial.ac_title,'ac_text': ac_initial.ac_text})
            return render(request, 'ac_form.html', locals())
    return HttpResponseForbidden()


def to_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = TopOffers.objects.get(id=post_text.get("edit")).id
            TopOffers.objects.filter(id=f).update(to_title=post_text["to_title"], to_link=post_text["to_link"])
            response_data['to_title'] = TopOffers.objects.get(id=f).to_title
            response_data['to_link'] = TopOffers.objects.get(id=f).to_link
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            to_initial = TopOffers.objects.get(id=id_edit)
            form = TopOffersForm(initial={'to_title': to_initial.to_title, 'to_link': to_initial.to_link})
            return render(request, 'to_form.html', locals())
    return HttpResponseForbidden()

def to_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = TopOffers.objects.get(id=post_text.get("edit")).id
            TopOffers.objects.filter(id=f).update(to_title=post_text["to_title"], to_link=post_text["to_link"])
            response_data['to_title'] = TopOffers.objects.get(id=f).to_title
            response_data['to_link'] = TopOffers.objects.get(id=f).to_link
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            to_initial = TopOffers.objects.get(id=id_edit)
            form = TopOffersForm(initial={'to_title': to_initial.to_title, 'to_link': to_initial.to_link})
            return render(request, 'to_form.html', locals())
    return HttpResponseForbidden()


def sup_post(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            response_data = {}
            post_text = request.POST
            print(post_text)
            f = Support.objects.get(id=post_text.get("edit")).id
            Support.objects.filter(id=f).update(sup_title=post_text["sup_title"], sup_time=post_text["sup_time"],
                                                sup_slogan=post_text["sup_slogan"], sup_phone=post_text["sup_phone"])
            response_data['sup_title'] = Support.objects.get(id=f).sup_title
            response_data['sup_time'] = Support.objects.get(id=f).sup_time
            response_data['sup_slogan'] = Support.objects.get(id=f).sup_slogan
            response_data['sup_phone'] = Support.objects.get(id=f).sup_phone
            response_data['id'] = f
            print(response_data)
            return JsonResponse(response_data)
        else:
            args = {}
            if 'edit' in request.GET:
                print(request.GET["edit"])
                args['edit'] = True
                id_edit = request.GET["edit"]
            sup_initial = Support.objects.get(id=id_edit)
            form = SupportForm(initial={'sup_title': sup_initial.sup_title, 'sup_time': sup_initial.sup_time,
                                        'sup_slogan': sup_initial.sup_slogan, 'sup_phone': sup_initial.sup_phone})
            return render(request, 'sup_form.html', locals())
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
            Company.objects.filter(id=f).update(name=post_text["name"], email=post_text["email"], address=post_text["address"], skype=post_text["skype"],
                                                mob_phone=post_text["mob_phone"], rob_phone=post_text["rob_phone"], facebook_link=post_text["facebook_link"],
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
                                        'facebook_link': company_initial.facebook_link, 'twitter_link': company_initial.twitter_link})
            return render(request, 'company_form.html', locals())
    return HttpResponseForbidden()


def home(request):
    args = {}
    if 'edit' in request.GET:
        args['edit'] = True
    args['form'] = FBlocksForm()
    args['baner'] = MainBaner.objects.all()
    args['TO'] = TopOffers.objects.all()
    args['sup'] = Support.objects.all()[0]
    args['p'] = Personal.objects.all()
    args['fb1'] = FBlocks.objects.get(id=1)
    args['fb2'] = FBlocks.objects.get(id=2)
    args['fb3'] = FBlocks.objects.get(id=3)
    args['fb4'] = FBlocks.objects.get(id=4)
    args['lb1'] = LBlocks.objects.get(id=1)
    args['lb2'] = LBlocks.objects.get(id=2)
    args['lb3'] = LBlocks.objects.get(id=3)
    args['lb4'] = LBlocks.objects.get(id=4)
    args['ac1'] = AboutCompany.objects.get(id=1)
    args['hf'] = HeaderPhoto.objects.get(id=1)
    args['company'] = Company.objects.get(id=1)

    args['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0))


    return render(request, 'home.html', args)

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
    ajax_template_name = "singlpage_form.html"

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
            if 'edit' in self.request.GET:
                ctx['edit'] = True
        return ctx

class OfferAjaxUpdateView(UpdateView):
    queryset = Offers.objects.all()
    form_class = OfferForm
    slug_field = "offer_url"
    slug_url_kwarg = "off_url"
    template_name = "offer.html"
    ajax_template_name = "offer_form.html"

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
        if self.request.is_ajax():
            return self.ajax_template_name
        return self.template_name

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not self.request.is_ajax():
            ctx['hf'] = HeaderPhoto.objects.get(id=1)
            ctx['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0))
            ctx['tags'] = Tags.objects.filter(tag_publish=True).order_by('tag_priority')
            ctx['subtags'] = Subtags.objects.filter(tag_parent_tag=self.object.offer_tag).order_by('?')

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
            return super().post(request, *args, **kwargs)
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


class TagsAjaxUpdateView(UpdateView):
    queryset = Tags.objects.all()
    form_class = TagsForm
    slug_field = "tag_url"
    slug_url_kwarg = "cat_url"
    template_name = "catalog.html"
    ajax_template_name = "catalog_form.html"

    def get_object(self):
        return get_object_or_404(Tags, tag_url=Tags.objects.filter(tag_publish=True).order_by('tag_priority')[0].tag_url)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().post(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {'initial': self.get_initial(), 'instance': self.object}

        if self.request.method in 'POST':
            kwargs.update({
                'data': self.request.POST,
            })
            print(kwargs)
        return kwargs

    def form_valid(self, form):
        form.save()
        return self.render_to_response(self.get_context_data(form=self.form_class(instance=self.object)))

    def get_template_names(self):
        if self.request.is_ajax():
            return self.ajax_template_name
        return self.template_name

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not self.request.is_ajax():
            try:
                ctx['pre'] = 'КАТЕГОРИЯ'
                mt = Tags.objects.get(tag_url=self.object.tag_url)
                offers = Offers.objects.filter(offer_tag=mt)
                ctx['subtags'] = Subtags.objects.filter(tag_parent_tag=mt).order_by('?')
            except Exception:
                ctx['pre'] = 'КЛЮЧЕВОЕ СЛОВО'
                mt = Subtags.objects.get(tag_url=self.object.tag_url)
                offers = Offers.objects.filter(offer_subtags=mt)
                ctx['subtags'] = Subtags.objects.filter(tag_parent_tag=mt.tag_parent_tag).order_by('?')

            ctx['hf'] = HeaderPhoto.objects.get(id=1)

            ctx['topmenu_category'] = Post.objects.filter(~Q(post_cat_level=0))
            ctx['offer'] = offers
            ctx['cat_title'] = mt
            ctx['tags'] = Tags.objects.filter(tag_publish=True).order_by('tag_priority')
        ctx['tags_list'] = self.object
        if self.request.user.is_superuser:
            if 'edit' in self.request.GET:
                ctx['edit'] = True
        return ctx

def pars_cat(request):
    rr = {
        "categories": {
            "category": [
                {
                    "-id": "62820",
                    "#text": "Гипс строительный"
                },
                {
                    "-id": "62942",
                    "#text": "Смесь для выравнивания пола"
                },
                {
                    "-id": "179694",
                    "#text": "Клей монтажный"
                },
                {
                    "-id": "136097",
                    "#text": "Пенопласт"
                },
                {
                    "-id": "10695",
                    "#text": " Пигменты и колеры для красок"
                },
                {
                    "-id": "10681",
                    "#text": " Эмали"
                },
                {
                    "-id": "112967",
                    "#text": " Сверла"
                },
                {
                    "-id": "116760",
                    "#text": " Штукатурка"
                },
                {
                    "-id": "116755",
                    "#text": " Шпатлевки"
                },
                {
                    "-id": "116813",
                    "#text": " Плиточный клей"
                },
                {
                    "-id": "271703",
                    "#text": "Клей строительный"
                },
                {
                    "-id": "62761",
                    "#text": "Клей для строительных конструкций"
                },
                {
                    "-id": "10763",
                    "#text": " Грунтовки"
                },
                {
                    "-id": "62782",
                    "#text": "Клей-армирование"
                },
                {
                    "-id": "10685",
                    "#text": " Анкеры"
                },
                {
                    "-id": "239112",
                    "#text": " Ацетон"
                },
                {
                    "-id": "113102",
                    "#text": "Валики малярные"
                },
                {
                    "-id": "115673",
                    "#text": " Вилки электрические"
                },
                {
                    "-id": "115669",
                    "#text": " Выключатель света"
                },
                {
                    "-id": "113381",
                    "#text": " Автоматические выключатели"
                },
                {
                    "-id": "113398",
                    "#text": "УЗО ВД1"
                },
                {
                    "-id": "128388",
                    "#text": "Метан, этан, пропан, бутан"
                },
                {
                    "-id": "10520",
                    "#text": " Блоки строительные"
                },
                {
                    "-id": "135375",
                    "#text": "Герметики"
                },
                {
                    "-id": "135275",
                    "#text": "Гидроизоляция"
                },
                {
                    "-id": "10612",
                    "#text": "Гипсокартон"
                },
                {
                    "-id": "91866",
                    "#text": "Лазерный дальномер"
                },
                {
                    "-id": "98599",
                    "#text": "Пластификатор для бетона"
                },
                {
                    "-id": "273030",
                    "#text": " Дрель аккумуляторная"
                },
                {
                    "-id": "104746",
                    "#text": " Дрель ударная"
                },
                {
                    "-id": "273034",
                    "#text": " Шуруповерт аккумуляторный"
                },
                {
                    "-id": "124988",
                    "#text": " Дюбели"
                },
                {
                    "-id": "116724",
                    "#text": "Затирки"
                },
                {
                    "-id": "143765",
                    "#text": " Кабель нагревательный"
                },
                {
                    "-id": "141632",
                    "#text": " Кабель силовой"
                },
                {
                    "-id": "10453",
                    "#text": " Кабель-канал"
                },
                {
                    "-id": "145466",
                    "#text": "Керамзит"
                },
                {
                    "-id": "10455",
                    "#text": " Кирпич"
                },
                {
                    "-id": "122210",
                    "#text": "Кислород"
                },
                {
                    "-id": "10821",
                    "#text": "Малярные кисти"
                },
                {
                    "-id": "106925",
                    "#text": " Флейцы"
                },
                {
                    "-id": "116768",
                    "#text": "Кладочные смеси"
                },
                {
                    "-id": "151680",
                    "#text": "Клей для минплиты"
                },
                {
                    "-id": "273433",
                    "#text": " Клей-пена"
                },
                {
                    "-id": "136227",
                    "#text": "Зажим клеммный"
                },
                {
                    "-id": "74305",
                    "#text": "Клещи токовые"
                },
                {
                    "-id": "170853",
                    "#text": "Клипса для труб"
                },
                {
                    "-id": "169039",
                    "#text": "Колодка удлинителя"
                },
                {
                    "-id": "115886",
                    "#text": " Коробки монтажные"
                },
                {
                    "-id": "10462",
                    "#text": " Краски"
                },
                {
                    "-id": "10896",
                    "#text": "Растворители, отвердители, дисперсии"
                },
                {
                    "-id": "116397",
                    "#text": " Энергосберегающие лампы"
                },
                {
                    "-id": "135794",
                    "#text": "Битум"
                },
                {
                    "-id": "114473",
                    "#text": " Электролобзик"
                },
                {
                    "-id": "172491",
                    "#text": "Миксеры строительные"
                },
                {
                    "-id": "113103",
                    "#text": "Шпатели"
                },
                {
                    "-id": "135842",
                    "#text": " Монтажная пена"
                },
                {
                    "-id": "101258",
                    "#text": " Пенополистирол"
                },
                {
                    "-id": "114477",
                    "#text": "Перфоратор"
                },
                {
                    "-id": "10781",
                    "#text": "Песок"
                },
                {
                    "-id": "10647",
                    "#text": " Пила циркулярная"
                },
                {
                    "-id": "134946",
                    "#text": " ОСП плита (OSB)"
                },
                {
                    "-id": "106787",
                    "#text": "Плиткорез"
                },
                {
                    "-id": "114790",
                    "#text": "Плиткорез электрический"
                },
                {
                    "-id": "63935",
                    "#text": " Подвес для профиля"
                },
                {
                    "-id": "116818",
                    "#text": " Цемент"
                },
                {
                    "-id": "137976",
                    "#text": " Прожекторы"
                },
                {
                    "-id": "63870",
                    "#text": "Маяк штукатурный"
                },
                {
                    "-id": "10492",
                    "#text": " Профиль"
                },
                {
                    "-id": "115672",
                    "#text": " Розетки"
                },
                {
                    "-id": "124987",
                    "#text": " Саморезы"
                },
                {
                    "-id": "79096",
                    "#text": "Панель светодиодная"
                },
                {
                    "-id": "10840",
                    "#text": " Сетка металлическая"
                },
                {
                    "-id": "140129",
                    "#text": "Сетка фасадная"
                },
                {
                    "-id": "125172",
                    "#text": "Смазки"
                },
                {
                    "-id": "92837",
                    "#text": " Торкретирование"
                },
                {
                    "-id": "116508",
                    "#text": " Моющие и чистящие средства"
                },
                {
                    "-id": "123686",
                    "#text": " Стальной канат, трос"
                },
                {
                    "-id": "271468",
                    "#text": " Уайт-спирит"
                },
                {
                    "-id": "181572",
                    "#text": "Угол ПВХ"
                },
                {
                    "-id": "116661",
                    "#text": " Машина углошлифовальная"
                },
                {
                    "-id": "124993",
                    "#text": " Цепи металлические"
                },
                {
                    "-id": "145463",
                    "#text": " Щебень"
                },
                {
                    "-id": "164964",
                    "#text": " Сварочные инверторы"
                },
                {
                    "-id": "115833",
                    "#text": " Люминесцентные лампы"
                },
                {
                    "-id": "108051",
                    "#text": "Дисковые пилы"
                },
                {
                    "-id": "173306",
                    "#text": "Пила торцовочная"
                },
                {
                    "-id": "142788",
                    "#text": " Провод монтажный"
                },
                {
                    "-id": "114470",
                    "#text": "Электродрели"
                },
                {
                    "-id": "172490",
                    "#text": "Штроборезы"
                },
                {
                    "-id": "81341",
                    "#text": "Краскораспылитель"
                },
                {
                    "-id": "104801",
                    "#text": "Дрель-миксер"
                },
                {
                    "-id": "105037",
                    "#text": "Машина плоско-шлифовальная"
                },
                {
                    "-id": "105078",
                    "#text": "Машина сверлильная"
                },
                {
                    "-id": "105095",
                    "#text": "Машина фрезерная"
                },
                {
                    "-id": "173372",
                    "#text": "Полировальные машины"
                },
                {
                    "-id": "114483",
                    "#text": " Электрорубанки"
                },
                {
                    "-id": "106393",
                    "#text": "Шуруповерт электрический"
                },
                {
                    "-id": "116502",
                    "#text": "Насадки для инструмента"
                },
                {
                    "-id": "173008",
                    "#text": "Линейка угловая"
                },
                {
                    "-id": "174708",
                    "#text": "Стол-верстак"
                }
            ]
        }
    }

    for i in rr['categories']['category']:
        kk = Tags (tag_url=i['-id'], tag_id=i['-id'], tag_title=i['#text'])
        kk.save ()


def pars_goods(request):
    rr = [
        {
            "@id": "58172190",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/58172190-gips_stroitelny_g_5_b_ii_alebastr",
            "price": "234.0",
            "currencyId": "RUR",
            "categoryId": "62820",
            "picture": "http://st12.stpulscen.ru/images/product/108/266/494_original.jpg",
            "name": "Гипс строительный  Г-5 Б-II Алебастр, 25 кг",
            "description": "Без гипса, как и без цемента, в современном строительстве не обойтись. В строительстве он называется алебастром. Алебастр с маркой Г-5 Б-II — это полностью готовое к применению чистое гипсовое вяжущее (без наполнителей или добавок) белого цвета.   ПЕРЕД НАЧАЛОМ РАБОТ: Применяйте алебастр только там, где он наиболее эффективен: при заделке небольших щелей, трещин и углублений внутри помещений, а также для выравнивания кирпичных и бетонных стен, штукатурки, древесины, фанеры, ДВП, ДСП, гипсокартона; Также алебастр незаменим при изготовлении различных декоративных элементов и лепнины. КАК ПРИГОТОВИТЬ АЛЕБАСТР: Залейте в мешалку или специальный сосуд чистую воду и засыпайте сухую смесь, добиваясь консистенции сметаны, без комков. Через пару минут масса готова для работ, которую обязательно нужно использовать в течение 10-15 минут, иначе она застынет. МЫ РЕКОМЕНДУЕМ: Не используйте алебастр с истёкшим сроком хранения — полгода, при условии сохранения в сухом помещении.",
            "sales_notes": "наличный и безналичный расчет, с НДС"
        },
        {
            "@id": "58178662",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/58178662-sr_72_nalivnoy_pol_dlya_naruzhnykh_i_vnutrennikh_rabot_proizvodstvenny",
            "price": "487.0",
            "currencyId": "RUR",
            "categoryId": "62942",
            "picture": "http://st12.stpulscen.ru/images/product/108/266/349_original.jpg",
            "name": "SR-72 Наливной пол для наружных и внутренних работ производственный, 25 кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ: Убедитесь, что основание достаточно крепкое, плотное и сухое. Перед тем, как наливать смесь для выравнивания, тщательно очистите старый пол от пыли и остатков краски или масел. Обязательно прогрунтуйте поверхность пола грунтовкой SR-51. Дайте грунтовке высохнуть в течение 4 часов. КАК ПРИГОТОВИТЬ СМЕСЬ НАЛИВНОГО ПОЛА: Залейте в мешалку пять — пять с половиной литров чистой воды и на малых оборотах засыпайте 25 килограммов сухой смеси, добиваясь консистенции сметаны, без комков. Через 10 минут повторно размешайте. Если используете штукатурную машину — работайте по её инструкции. МЫ РЕКОМЕНДУЕМ: Работать только при температуре воздуха выше +5°С и ниже +30°С, не допуская сквозняков. Разводите вылитый раствор резиновой планкой и подобным инструментом или механизированным способом. Если площадь пола больше двадцати квадратных метров, делайте деформационные швы. Не забывайте мыть инструмент и оборудование сразу после работы. Ходить по наливному полу можно примерно через 6 часов. Плитку можно укладывать через сутки. Линолеум и другие материалы можно укладывать через двое суток. СОСТАВ Полимерные материалы, цемент и фракционированный песок. СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке.",
            "sales_notes": "наличный и безналичный расчет, с НДС"
        },
        {
            "@id": "58178716",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/58178716-sr_67_kley_dlya_blokov_iz_yacheistogo_betona",
            "price": "297.0",
            "currencyId": "RUR",
            "categoryId": "179694",
            "picture": "http://st12.stpulscen.ru/images/product/108/270/799_original.jpg",
            "name": "SR-67 Клей для блоков из ячеистого бетона, 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Влажность поверхности не имеет значения. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпите порошок в удобный для перемешивания сосуд из расчёта пять литров воды на мешок смеси. Вливайте воду, доводя до консистенции густой сметаны. Комочки тут же разминайте. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пятнадцать и ещё раз быстро размешайте. Используйте смесь не позднее, чем через два часа. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс двадцати пяти) — не работайте с клеем. Наносите клей и разравнивайте шпателем с зубьями (3-8мм) — это экономит смесь и предотвращает выдавливание в щели. Наносите раствор как на вертикальные, так и на горизонтальные поверхности соседних блоков зубчатой тёркой (гладилкой) равномерным слоем и затем слегка прижимайте. После прижатия слой раствора между блоками примерно три миллиметра, но не более пяти. Не забывайте тщательно отмывать инструмент после работы. СОСТАВ Полимерные и минеральные материалы, высококачественный цемент, фракционированный песок. СРОК ГОДНОСТИ 6 месяцев в сухих условиях и герметичной упаковке.",
            "sales_notes": "наличный и безналичный расчет, с НДС"
        },
        {
            "@id": "64784081",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64784081-penoplast_eps",
            "price": "50.0",
            "currencyId": "RUR",
            "categoryId": "136097",
            "picture": "http://st2.stpulscen.ru/images/product/111/083/372_original.jpg",
            "name": "Пенопласт EPS",
            "description": "Пенопласт EPS s Optima 1м*1м*2см. Является теплоизоляционным материалом прямоугольной формы и сечения, произведенный из вспененного полистирола. Он широко используется в современном строительстве в качестве звуко-теплоизоляции, а также заполняющего материала в конструкциях, в которых механические нагрузки на плиты  незначительны либо отсутствуют. При применении плит EPS не требуется специальных мер безопасности, так как они не являются токсичными."
        },
        {
            "@id": "64953613",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64953613-kraska_koler_oreol_izumrud_v_d_poliakrilovaya_toniruyushchaya_0_725",
            "price": "144.0",
            "currencyId": "RUR",
            "categoryId": "10695",
            "picture": "http://st17.stpulscen.ru/images/product/109/782/996_original.png",
            "name": "Краска-колер \"ОРЕОЛ\" изумруд в/д полиакриловая тонирующая 0,725",
            "description": "Стойкая формула краски-колера предназначена для покраски материалов, которые подвергаются атмосферному действию, а также поверхностей, находящих в помещениях. В наличии от производителя – всевозможные цвета, стойкость которых сохраняется в течение долгого времени. А лучшая на рынке цена – бесспорный аргумент в пользу покупки данного товара в Крыму."
        },
        {
            "@id": "64953614",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64953614-emal_marshall_export_akva_na_vodnoy_osnove_p_mat_chernaya_0_8",
            "price": "485.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st17.stpulscen.ru/images/product/109/785/147_original.png",
            "name": "Эмаль\"Marshall\" Экспорт Аква на водной основе п/мат. черная (0,8",
            "description": "Эта высококачественная краска на водной основе используется для деревянных и металлических поверхностей, может подходить к радиаторам. Имеет стойкую к ударам и царапинам структуру и не желтеет со временем под влиянием высоких температур. При окрашиванье не распространяет резкий запах, поэтому может использоваться во внутренних помещениях. Все цвета есть в наличии. Краску выгодно покупать, поскольку на нее действует скидка."
        },
        {
            "@id": "64953621",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64953621-sverlo_tsirkulnoye_po_kafelyu_balerinka_20_90mm_16530",
            "price": "303.0",
            "currencyId": "RUR",
            "categoryId": "112967",
            "picture": "http://st17.stpulscen.ru/images/product/109/778/806_original.jpg",
            "name": "Сверло циркульное по кафелю(балеринка) 20-90мм(16530)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64960087",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960087-sr_13_shtukaturka_dekorativnaya_koroyed_25kg_2_5mm",
            "price": "545.0",
            "currencyId": "RUR",
            "categoryId": "116760",
            "picture": "http://st17.stpulscen.ru/images/product/110/692/652_original.jpg",
            "name": "SR-13 Штукатурка декоративная \"Короед\", 25кг 2,5мм",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для короеда. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За четыре часа до нанесения короеда прогрунтуйте основание рекомендованной грунтовкой: SR-51. Закройте плёнкой окна, двери и прочее, на что короед не наносится. КАК ПРИГОТОВИТЬ КОРОЕД: Высыпите весь мешок в удобный для перемешивания сосуд. Вливайте шесть литров воды, доводя до консистенции густой сметаны. Комочки тут же разминайте. Используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пять и ещё раз быстро размешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте с короедом. Наносите короед тёркой из нержавейки, держа её под небольшим углом (примерно 60 град) к поверхности нанесения. Следите за толщиной слоя — она не должна быть больше размера наполнителя.  Дождитесь, пока раствор перестанет быть липким к тёрке и работайте деревянной или пластмассовой тёркой, добиваясь нужной вам структуры поверхности. Меняйте направление движения тёрки и получайте углубления разной формы, держа тёрку параллельно слою. Не работайте при жаре или холоде и высокой влажности (дожде и тумане). СОСТАВ Полимерные материалы, цемент и фракционированный песок. СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64960088",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960088-sr_14_shpaklevka_fasadnaya_finishnaya_vlagostoykaya_morozostoykaya_polimernaya_be",
            "price": "520.0",
            "currencyId": "RUR",
            "categoryId": "116755",
            "picture": "http://st17.stpulscen.ru/images/product/110/694/820_original.jpg",
            "name": "SR-14 Шпаклевка фасадная, белая , 20кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для шпатлевки. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За четыре часа до нанесения короеда прогрунтуйте основание рекомендованной грунтовкой: SR-51. КАК ПРИГОТОВИТЬ ШПАТЛЁВКУ: Высыпите весь мешок в удобный для перемешивания сосуд. Вливайте восемь литров воды, доводя до консистенции густой сметаны. Комочки тут же разминайте. Используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пять-десять и ещё раз быстро размешайте. МЫ РЕКОМЕНДУЕМ: Благодаря морозостойкости шпатлевки применяйте её как внутри, так и снаружи зданий. Берегите глаза и кожу — в составе шпатлевки есть цемент. СОСТАВ Полимерные материалы, модифицирующие добавки, цемент. СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64960089",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960089-sr_15_shtukaturka_peschano_tsementnaya_izvestkovaya_vlagostoykaya_morozostoykaya",
            "price": "321.0",
            "currencyId": "RUR",
            "categoryId": "116760",
            "picture": "http://st17.stpulscen.ru/images/product/110/695/891_original.jpg",
            "name": "SR-15 Штукатурка песчано-цементная-известковая, 25кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За четыре или более часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51. Окна и другие необрабатываемые поверхности должны быть защищены плёнкой. КАК ПРИГОТОВИТЬ ШПАТЛЕВКУ: Высыпайте сухую шпатлевку в удобный для перемешивания сосуд или мешалку, предварительно заполненный водой. На 25 килограмм сухой шпатлевки должно быть 6 литров воды. Всыпайте порошок в воду, перемешивая и доводя до нужной консистенции. Комочки тут же разминайте. Подождите 15 минут и снова перемешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте со шпатлёвкой. Сначала заполните крупные выемки и неровности, и только спустя время набора прочности (сутки) — выравнивающий слой. Наносите смесь типовым инструментом — шпателем или правилом. Не забывайте очищать и мыть инструмент после выполнения работ. СОСТАВ Полимерные материалы, цемент и фракционированный песок, известь. СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64960090",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960090-sr_17_layt_shtukaturka_gipsovaya_start_oblegchennaya_perlitovaya_rn",
            "price": "430.0",
            "currencyId": "RUR",
            "categoryId": "116760",
            "picture": "http://st13.stpulscen.ru/images/product/111/975/815_original.jpg",
            "name": "SR-17 Лайт Штукатурка гипсовая \"Старт\", 30 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для штукатурки. Если есть бугры, счистите их, а отслоения удалите. Ямы и вмятины глубиной более пяти сантиметров заполните отдельно, перед выравниванием поверхности, гипсовой штукатуркой. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Если поверхность сильно впитывает, прогрунтуйте её грунтовкой SR-51, бетон — SR-52, а не впитывающие влагу поверхности — грунтовкой «Бетон-контакт» ТМ «PRO». Наружные углы, дверные и оконные откосы защитите уголками. Стыки укрепите штукатурной сеткой. КАК ПРИГОТОВИТЬ ГИПСОВУЮ ШТУКАТУРКУ: Высыпайте сухую гипсовую штукатурку в удобный для перемешивания сосуд, предварительно заполненный водой. На килограмм сухой штукатурки должно быть 550 миллилитров воды. Всыпайте порошок в воду, перемешивая и доводя до нужной консистенции. Комочки тут же разминайте. Если используете штукатурную машину, работайте по её инструкции. МЫ РЕКОМЕНДУЕМ: Если площадь покрытия большая, используйте специальные маяки — металлические планки. Не работайте при температуре ниже плюс десяти градусов и выше плюс тридцати и в сырых помещениях. Раствор наносите слоем одинаковой толщины — не больше 5 сантиметров, на потолки — не более двух либо с предварительным армированием оцинкованной сеткой. Если собираетесь наносить несколько слоёв, то первый должен остаться шероховатым. Разравнивайте штукатурку правилом или гладилкой. Сразу после схватывания излишки штукатурки срежьте трапециевидным правилом и загладьте шпателем. Не забывайте сразу отмывать инструмент и оборудование! СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64960091",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960091-sr_18_shpaklevka_multifinish_dlya_vnutrennikh_rabot_supertonkaya_p",
            "price": "471.0",
            "currencyId": "RUR",
            "categoryId": "116755",
            "picture": "http://st13.stpulscen.ru/images/product/111/981/550_original.jpg",
            "name": "SR-18 Шпаклевка \"Мультифиниш\", 20кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для короеда. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За два часа до нанесения шпатлевки прогрунтуйте основание рекомендованной грунтовкой: SR-51. КАК ПРИГОТОВИТЬ ШПАТЛЕВКУ: Высыпайте весь мешок в удобный для перемешивания сосуд, предварительно заполненный чистой водой из расчета 10 литров на мешок смеси . Перемешивайте, доводя до консистенции густой сметаны. Комочки тут же разминайте. Используйте механическую мешалку, но только с малой скоростью вращения. МЫ РЕКОМЕНДУЕМ: Не работайте при температуре ниже плюс десяти градусов и выше плюс тридцати. Раствор наносите слоем одинаковой небольшой толщины специальным инструментом, новый слой нанося только после полного высыхания предыдущего. Не забывайте сразу отмывать инструмент и оборудование! СОСТАВ Микромрамор, минеральные наполнители, модифицирующие добавки. СРОК ХРАНЕНИЯ 6 месяцев в сухих условиях и герметичной упаковке. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64960094",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960094-sr_23_kley_dlya_plitki_vlagostoyki_morozostoyki_25_kg",
            "price": "316.0",
            "currencyId": "RUR",
            "categoryId": "116813",
            "picture": "http://st2.stpulscen.ru/images/product/111/281/257_original.jpg",
            "name": "SR-23 Клей для плитки, 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Влажность поверхности не имеет значения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпите порошок в удобный для перемешивания сосуд. Вливайте воду, доводя до консистенции густой сметаны. Комочки тут же разминайте. Соотношение порошка к воде обычно пять-шесть к одному. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пятнадцать и ещё раз быстро размешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте с клеем. Наносите клей и разравнивайте шпателем с зубьями (3-8мм) — это экономит смесь и предотвращает выдавливание в щели. Помните о мере — слишком большие поверхности нужно обработать частями. Прижимайте плитку к нанесённому раствору без усилий. У Вас есть десять минут для исправления положения плитки. Полная готовность работы наступает через сутки для стен и через трое суток для полов — берегите плитку от нагрузок в этот период. ВНИМАНИЕ: ЗАМАЧИВАТЬ ПЛИТКУ ПЕРЕД ПРИКЛЕИВАНИЕМ НЕ ТРЕБУЕТСЯ!"
        },
        {
            "@id": "64960096",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960096-sr_24_kley_dlya_keramogranita_mramora_kamnya_usilenny_25_kg",
            "price": "420.0",
            "currencyId": "RUR",
            "categoryId": "271703",
            "picture": "http://st13.stpulscen.ru/images/product/111/986/080_original.jpg",
            "name": "SR-24 Клей для керамогранита, 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Влажность поверхности не имеет значения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпите порошок в удобный для перемешивания сосуд. Вливайте воду, доводя до консистенции густой сметаны. Комочки тут же разминайте. Соотношение порошка к воде обычно пять-шесть к одному. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пятнадцать и ещё раз быстро размешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте с клеем. Наносите клей слоем не толще пяти миллиметров и разравнивайте шпателем с зубьями (3-8мм) — это экономит смесь и предотвращает выдавливание в щели. Помните о мере — слишком большие поверхности нужно обработать частями. Прижимайте плитку к нанесённому раствору без усилий. У Вас есть десять минут для исправления положения плитки. Полная готовность работы наступает через сутки для стен и через трое суток для полов — берегите плитку от нагрузок в этот период. ВНИМАНИЕ: ЗАМАЧИВАТЬ ПЛИТКУ ПЕРЕД ПРИКЛЕИВАНИЕМ НЕ ТРЕБУЕТСЯ!"
        },
        {
            "@id": "64960097",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960097-sr_26_kley_dlya_listov_gkl_i_gvl_gipsokartona_25_kg_bely",
            "price": "312.0",
            "currencyId": "RUR",
            "categoryId": "62761",
            "picture": "http://st2.stpulscen.ru/images/product/111/100/606_original.jpg",
            "name": "SR-26 Клей для гипсокартона , 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51 с использованием щётки с жёстким ворсом. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпайте смесь в удобный для перемешивания сосуд, заполненный тёплой водой из расчёта восемь — десять литров воды на мешок сухой смеси, тщательно перемешивая. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения и специальной насадкой. Дайте отстояться полученной смеси минуты две-три и ещё раз быстро размешайте. Не используйте готовую смесь, если она простояла более часа. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) или сыро — не работайте с клеем. Наносите клей в паз пазогребневой плиты толстым слоем, добиваясь покрытия раствором всей поверхности соединения. Плотно прижмите очередную подготовленную таким образом плиту к соседней. На листы гипсокартона клей наносите лепёшками толщиной три-пять сантиметров. Общая площадь покрытой клеем поверхности должна быть не менее трети общей площади листа. Прижимайте лист к стене металлическим уровнем. Через пару часов можно приступать к шпатлёвки и прочим работам. СРОК ХРАНЕНИЯ 12 месяцев в сухом помещении в оригинальной закрытой упаковке."
        },
        {
            "@id": "64960098",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960098-sr_51_grunt_glubogo_proniknoveniya_dlya_vnutrennikh_i_naruzhnykh_rabot_10_l",
            "price": "495.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/230/274_original.jpg",
            "name": "SR-51 Грунт глубого проникновения 10 л",
            "description": "SR-51 Грунт глубокого проникновения  для внутренних и наружных работ. Используется для укрепления и пропитки оснований перед укладкой керамических плиток, покрытием краской, обоями, штукатуркой и заливкой полов. Он имеет достаточно большую популярность благодаря своим отличным свойствам, например: - высокая проникающая способность; - укрепляет старые основания; - повышает адгезию."
        },
        {
            "@id": "64960099",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960099-sr_62_kley_dlya_teploizolyatsii_25_kg_armiruyushchi",
            "price": "497.0",
            "currencyId": "RUR",
            "categoryId": "62782",
            "picture": "http://st13.stpulscen.ru/images/product/112/682/850_original.jpg",
            "name": "SR-62 Клей для теплоизоляции, 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51 или «Бетон-Контакт» в зависимости от типа основания. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпайте смесь в удобный для перемешивания сосуд, заполненный тёплой водой из расчёта четыре — пять литров воды на мешок сухой смеси (или 2 части объема воды на 5 частей сухой смеси), тщательно перемешивая. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пять-десять и ещё раз быстро размешайте. Не используйте готовую смесь, если она простояла более двух с половиной часов. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс двадцати пяти) или сыро — не работайте с клеем. Избегайте попадания солнца, ветра и дождя, а также минусовых температур, на свежую клеевую поверхность (при работе на фасадах). Наносите клей на внутреннюю сторону плиты полосой три-четыре сантиметра по контуру и лепёшками в центр плиты — несколько штук диаметром примерно десять сантиметров и толщиной примерно два сантиметра. Перед укладкой армирующей сетки нанесите смесь с помощью зубчатой тёрки. Уложите сетку и тщательно выровняйте и загладьте поверхность. Правильное положение сетки — снаружи утепляющей системы."
        },
        {
            "@id": "64960105",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960105-sr_73_pol_nalivnoy_dlya_vnutrennikh_rabot_25_kg",
            "price": "445.0",
            "currencyId": "RUR",
            "categoryId": "62942",
            "picture": "http://st13.stpulscen.ru/images/product/112/774/570_original.jpg",
            "name": "SR-73, Наливной пол для внутренних работ, 25кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ: Перед тем, как наливать смесь для выравнивания, тщательно очистите старый пол от пыли и остатков краски или масел. Обязательно прогрунтуйте поверхность пола грунтовками SR-51 или SR-52. Дайте грунтовке высохнуть в течение 4 часов. Если основание пола неоднородное, из разных материалов, а также если выравнивающий слой не более 5 миллиметров, используйте армирующую сетку. КАК ПРИГОТОВИТЬ СМЕСЬ НАЛИВНОГО ПОЛА: Залейте в мешалку семь литров чистой воды и на малых оборотах засыпайте 25 килограммов сухой смеси, добиваясь консистенции сметаны, без комков. Если используете штукатурную машину — работайте по её инструкции. МЫ РЕКОМЕНДУЕМ: Работать только при температуре воздуха выше +10°С. Если площадь пола больше двадцати квадратных метров, делайте деформационные швы. Не забывайте мыть инструмент и оборудование сразу после работы. Ходить по наливному полу можно примерно через 4-5 часов. Плитку можно укладывать через сутки. Линолеум можно укладывать через трое суток. Деревянные покрытия (паркет и т.п) укладывайте в соответствии с рекомендациями поставщика покрытия."
        },
        {
            "@id": "64960106",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960106-sr_74_styazhka_rovnitel_dlya_teplykh_polov_25_kg",
            "price": "360.0",
            "currencyId": "RUR",
            "categoryId": "62942",
            "picture": "http://st13.stpulscen.ru/images/product/112/776/734_original.jpg",
            "name": "SR-74, Стяжка для\" теплых \" полов, 25 кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТ:  Нужно обязательно очистить основание. Убедитесь, что оно прочное, плотное и сухое. Следы краски удалите. Трещины расширьте шпателем и очистите. Не позднее, чем за 4 часа до работ со стяжкой, прогрунтуйте основание, используя грунтовки SR-51 или SR-52. КАК ПРИГОТОВИТЬ СТЯЖКУ: Используйте механическую мешалку на малых оборотах. Залейте в неё пять литров воды, затем высыпайте сухой ровнитель, пока не получите однородную массу без комков. На 5 литров — 25 кг сухой смеси. Подождите около 10 минут и снова перемешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте со стяжкой. Также не допускайте сквозняка. Готовый раствор вылейте на выравниваемый пол и распределите по всей поверхности резиновой планкой или другим специальным инструментом, в том числе механизированным. Через 24 часа можете ходить по стяжке. Спустя 7 дней можете укладывать напольное покрытие. Если нарушен климатический режим, сроки высыхания и схватывания могут быть больше."
        },
        {
            "@id": "64960125",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960125-anker_zabivnoy_drm_10_12x40_1000_50sht",
            "price": "6534.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/594/614_original.jpg",
            "name": "Анкер забивной DRM 10 12x40",
            "description": "Анкер изготовлен с оцинкованной стали, имеет внутреннюю резьбу. Благодаря расширяющему конусу легко обеспечивает надежную установку в твердых материалах. В наличии разные размеры для необходимого применения по лучшей цене. Используется для работы во внутренных помещениях. Имеет специальную кромку для установки."
        },
        {
            "@id": "64960126",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960126-anker_zabivnoy_drm_20_25kh80_100_25_sht",
            "price": "52452.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/594/677_original.jpg",
            "name": "Анкер забивной DRM 20 25х80",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960127",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960127-anker_zabivnoy_drm_16_20kh64_200_25_sht",
            "price": "23527.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/594/679_original.jpg",
            "name": "Анкер забивной DRM 16 20х64",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960128",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960128-anker_zabivnoy_drm_8_10kh30_1600_100_sht",
            "price": "3793.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/594/680_original.jpg",
            "name": "Анкер забивной DRM 8 10х30",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960134",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960134-anker_klin_man_6_x_37",
            "price": "5495.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/595/323_original.jpg",
            "name": "Анкер-клин MAN 6 x 37",
            "description": "Анкеры от производителя отлично подходят для крепления рам, конструкций, металлических профилей к каменной, бетонной и кирпичной поверхности. Изготовлен с оцинкованной стали, поэтому обладает пожароустойчивостью и прочностью. Крепиться с помощью молотка в отверствие, просвердленное заранее. Широкий диапазон размеров для монтажа каркасов, разных конструкций, рам, барьеров в магазинах Ялты, Гурзуфы."
        },
        {
            "@id": "64960135",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960135-anker_klin_man_6_x_65_1000_100_sht",
            "price": "9236.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/595/375_original.jpg",
            "name": "Анкер-клин MAN 6 x 65",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960136",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960136-anker_klin_wam_6_x_95_1000_100sht",
            "price": "7411.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/595/552_original.png",
            "name": "Анкер-клин WAM 6 x 95 (1000/100шт)",
            "description": "Анкер являет собой стержень со стали, который имеет цилиндрическую муфту, гайку и конусообразный хвостовик. Используется для крепления особо тяжелых конструкций в твердых материалах. Изготовлены стальные анкеры методом горячего цинка. Для того чтобы надежно закрепить анкер, не нужно специальной очистки отверствия. Лучшая цена на товар, а при оптовом заказе – скидки."
        },
        {
            "@id": "64960137",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960137-anker_klin_wam_8_x_105_500_50sht",
            "price": "10740.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/595/795_original.png",
            "name": "Анкер-клин WAM 8 x 105 (500/50шт)",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960139",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960139-anker_klin_wam_8_x_120_500_50sht",
            "price": "11310.0",
            "currencyId": "RUR",
            "categoryId": "10685",
            "picture": "http://st2.stpulscen.ru/images/product/111/595/801_original.png",
            "name": "Анкер-клин WAM 8 x 120 (500/50шт)",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64960161",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960161-atseton_vershina_0_5_l_10_20",
            "price": "74.0",
            "currencyId": "RUR",
            "categoryId": "239112",
            "picture": "http://st2.stpulscen.ru/images/product/110/965/824_original.jpg",
            "name": "Ацетон \"Вершина\" 0,5 л (10/20)",
            "description": "Один из самых популярных растворителей."
        },
        {
            "@id": "64960162",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960162-atseton_1l_g_ufa",
            "price": "152.0",
            "currencyId": "RUR",
            "categoryId": "239112",
            "name": "Ацетон 1л г.Уфа",
            "description": "Растворяет не только лаки, эмали, краски, но и масла, эпоксидные смолы, хлоркаучук. Хорошо обезжиривает поверхности. Использовать нужно на свежем воздухе или в хорошо проветриваемом помещенье. Продается в магазине возле Артека в Крыму."
        },
        {
            "@id": "64960553",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960553-valik_stayer_master_velyur_v_sb_vors_4mm_byugel_6m",
            "price": "116.0",
            "currencyId": "RUR",
            "categoryId": "113102",
            "picture": "http://st2.stpulscen.ru/images/product/110/791/716_original.jpg",
            "name": "Валик \"STAYER\" \"MASTER\" Велюр в сб. ворс 4мм, бюгель 6м",
            "description": "Всё для малярки."
        },
        {
            "@id": "64960571",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960571-valik_usp_sintex_94kh230mm_byugel_8mm_vors_18mm_v_sbore_02188",
            "price": "243.0",
            "currencyId": "RUR",
            "categoryId": "113102",
            "picture": "http://st21.stpulscen.ru/images/product/118/548/292_original.jpg",
            "name": "Валик USP синтекс 94х230мм, бюгель 8мм, ворс 18мм в сборе (02188)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64960662",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960662-vilka_16a_s_z_pryamaya_buko",
            "price": "115.0",
            "currencyId": "RUR",
            "categoryId": "115673",
            "picture": "http://st2.stpulscen.ru/images/product/111/919/397_original.jpg",
            "name": "Вилка 16А с/з прямая BUKO",
            "description": "Прямая вилка используется для того чтобы присоединить к электросети разные электрические приборы. Выдерживает мощность до 4 кВт. Широко используется во всех сферах деятельности, в том числе в быту. Продаются прямые вилки в магазине возле Артека, рядом с Ришелье Шато.."
        },
        {
            "@id": "64960708",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960708-vyklyuchatel_1_y_vera",
            "price": "161.0",
            "currencyId": "RUR",
            "categoryId": "115669",
            "picture": "http://st13.stpulscen.ru/images/product/112/945/603_original.jpg",
            "name": "Выключатель 1-й VERA",
            "description": "Выключатель сделан из белого пластика и монтируется встроенным образом. Номинальное напряжение – 250 В, а номинальный ток – 10А. используются для того чтобы оперативно включать и отключать электросеть. Мы предлагаем выключатели по лучшей цене от производителя. ."
        },
        {
            "@id": "64960710",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960710-vyklyuchatel_avtomaticheski_va_101_1r_16a_krivaya_s_4_5_ka",
            "price": "97.0",
            "currencyId": "RUR",
            "categoryId": "113381",
            "picture": "http://st13.stpulscen.ru/images/product/112/945/848_original.jpg",
            "name": "Выключатель автоматический ВА -101 1Р 16А кривая С 4,5 кА",
            "description": "Предназначение автоматических выключателей – защищать групповые и распределительные цепи, у которых разная нагрузка. Широко используются в индивидуальных домах и организациях. Продаются в наших строительных магазинах в Крыму со скидками. ."
        },
        {
            "@id": "64960711",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960711-vyklyuchatel_avtomaticheski_va_101_1r_25a_krivaya_s_4_5_ka",
            "price": "97.0",
            "currencyId": "RUR",
            "categoryId": "113381",
            "picture": "http://st13.stpulscen.ru/images/product/113/011/991_original.jpg",
            "name": "Выключатель автоматический ВА -101 1Р 25А кривая С 4,5 кА",
            "description": "Автовыключатель от производителя – это защита от замыканий в сети, а значит, потребители света могут быть спокойны. При появленье сверхтоков выключатель автоматически выключается. Срок эксплуатации достаточно долгий. Покупайте в нашем магазине и участвуйте в акциях и распродажах.   ."
        },
        {
            "@id": "64960712",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960712-vyklyuchatel_avtomaticheski_va63_3r_50a_krivaya_s_4_5_ka",
            "price": "1704.0",
            "currencyId": "RUR",
            "categoryId": "113381",
            "picture": "http://st13.stpulscen.ru/images/product/113/012/069_original.jpg",
            "name": "Выключатель автоматический ВА63 3Р 50А кривая С 4,5 кА",
            "description": "Автоматические выключатели созданы с целью защиты низковольтных электрических цепей от короткого замыкания. Используются в промышленности, в быту, на разных строительных объектах. Реализовываются в Крыму, Ялте и Гурзуфе."
        },
        {
            "@id": "64960715",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960715-vyklyuchatel_differentsialny_vd1_63_uzo_2r_25a_30ma_mdv10_2_025_030_i",
            "price": "97.0",
            "currencyId": "RUR",
            "categoryId": "113398",
            "picture": "http://st13.stpulscen.ru/images/product/113/012/115_original.jpg",
            "name": "Выключатель дифференциальный ВД1-63 (УЗО) 2Р 25А 30мА | MDV10-2-025-030 | И",
            "description": "Выключатель тонко реагирует на дифференциальный ток и создает дополнительную защиту для людей от поражения электрическим током. Имеет высокую износостойкость, предотвращает возможные пожары благодаря тому, что позволяет ему протекать в землю. Только лучшая цена, высокие скидки и постоянные распродажи выключателей для вас."
        },
        {
            "@id": "64960718",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960718-gaz_20_kg_v_ballone",
            "price": "1930.0",
            "currencyId": "RUR",
            "categoryId": "128388",
            "picture": "http://st17.stpulscen.ru/images/product/110/241/872_original.jpg",
            "name": "Газ 20 кг в баллоне Метан, этан, пропан, бутан",
            "description": "Пропан – попутный нефтяной горючий газ, применяемый как в быту, так и строительных работах. Смесь из сжиженного пропана и бутана применяется для пайки и сварки материалов с небольшой толщиной. Сжиженный пропан может использоваться для резки металла. При строительстве данная смесь может применяться при производстве сварных кровельных конструкций и для сборки конструкций из металла. Существуют два варианта заполнения смесью баллона: зимний и летний. Зимняя смесь содержит в себе 90% пропана и 10% бутана. В летней смеси количество пропановой части смеси колеблется от 40% до 60% и бутановой от 60% до 40%. В наличии и под заказ в Крыму (г. Ялта, пгт. Гурзуф) можно купить баллоны объемом 50 л (м3) с массой смеси 20-22 кг. ПРОСИМ УЧЕСТЬ: во избежание ошибок при работе и наилучшего качества, просим правильно включать горелку перед началом работ. А именно, подача газовой смеси должна быть плавной при зажигании и при достижении максимальной температуры, тогда будет получен наилучший эффект для достижения необходимых целей. ВНИМАНИЕ!!! При самовывозе просим обеспечить 100%-е безопасное закрепление баллонов. Мы проверяем. Предоставляются услуги доставки (в том числе бесплатной) в зависимости от объемов заказа. ДОПОЛНИТЕЛЬНО: 1. Обмен баллонов. 2. Залог баллонов от 3000 руб. Наша компания имеет большой опыт комплексного снабжения объектов капитального строительства. В наличии имеются все паспорта и сертификаты на весь предоставленный товар. Возможен как наличный, так и безналичный расчет. Мы работаем с НДС. У нас Вы можете получить скидки, которые Вас несомненно порадуют."
        },
        {
            "@id": "64960721",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960721-gazobeton_600_200_100_massiv",
            "price": "70.0",
            "currencyId": "RUR",
            "categoryId": "10520",
            "picture": "http://st2.stpulscen.ru/images/product/110/974/233_original.jpg",
            "name": "Газобетон 600*200*100 Массив",
            "description": "Сочетает прочность с легкостью."
        },
        {
            "@id": "64960722",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960722-gazobeton_600_300_200_massiv",
            "price": "130.0",
            "currencyId": "RUR",
            "categoryId": "10520",
            "picture": "http://st2.stpulscen.ru/images/product/110/974/860_original.jpg",
            "name": "Газобетон 600*300*200 Массив",
            "description": "Сочетает прочность с легкостью."
        },
        {
            "@id": "64960835",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960835-germetik_bitumny_sika_blackseal_300ml",
            "price": "462.0",
            "currencyId": "RUR",
            "categoryId": "135375",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/274_original.png",
            "name": "Герметик битумный Sika Blackseal 300мл",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64960853",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960853-gidroizolyatsiya_odnokomponentnaya_sukhaya_sika_101_25kg",
            "price": "1252.0",
            "currencyId": "RUR",
            "categoryId": "135275",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/278_original.png",
            "name": "Гидроизоляция однокомпонентная сухая Sika-101 25кг",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64960869",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960869-gipsokarton_knauf_12_5_1_2_2_5_3_0m2",
            "price": "346.0",
            "currencyId": "RUR",
            "categoryId": "10612",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/873_original.jpg",
            "name": "Гипсокартон KNAUF 12.5*1.2*2.5 (3.0м2)",
            "description": "Стеновой гиспсокартон для устройства перегородок в обычных помещениях."
        },
        {
            "@id": "64960870",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960870-gipsokarton_knauf_12_5_1_2_2_5_vlagostoykaya",
            "price": "444.0",
            "currencyId": "RUR",
            "categoryId": "10612",
            "picture": "http://st2.stpulscen.ru/images/product/111/086/556_original.jpg",
            "name": "Гипсокартон KNAUF 12.5*1.2*2.5 Влагостойкая",
            "description": "Стеновой гиспсокартон для устройства перегородок во влажных помещениях."
        },
        {
            "@id": "64960872",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960872-gipsokarton_knauf_9_5_1_2_2_5",
            "price": "320.0",
            "currencyId": "RUR",
            "categoryId": "10612",
            "picture": "http://st2.stpulscen.ru/images/product/111/087/146_original.jpg",
            "name": "Гипсокартон KNAUF 9,5*1.2*2.5",
            "description": "Потолочный гиспсокартон для любых помещений."
        },
        {
            "@id": "64960874",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960874-gipsokarton_knauf_vlag_9_5_1_2_2_5_3_0m2",
            "price": "400.0",
            "currencyId": "RUR",
            "categoryId": "10612",
            "picture": "http://st2.stpulscen.ru/images/product/111/086/565_original.jpg",
            "name": "Гипсокартон KNAUF влаг. 9,5*1.2*2.5 (3.0м2)",
            "description": "Потолочный гиспсокартон для устройства перегородок во влажных помещениях."
        },
        {
            "@id": "64960887",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960887-grunt_dulux_bindo_base_v_d_glubokogo_proniknoveniya_dlya_naruzhnikh",
            "price": "989.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/424/041_original.jpg",
            "name": "Грунт \"Dulux\" Bindo Base в/д глубокого проникновения для наружних",
            "description": "Грунт предназначен для грунтования поверхностей в домах и офисах. Может использоваться не только для внутренних, но и наружных работ – обработка фасадов. Правильное использованье грунта значительно сократит расходы последующих средств. Нужное количество товара можно купить в магазине рядом с Ришелье Шато. Для организаций действует расчет по безналу НДС. ."
        },
        {
            "@id": "64960888",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960888-grunt_marshall_export_base_v_d_dlya_naruzhnikh_i_vnutrennikh_rabot",
            "price": "207.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/424/654_original.jpg",
            "name": "Грунт \"Marshall\" Export Base в/д для наружних и внутренних работ 0,9л",
            "description": "Благодаря высокой концентрации грунтовочных веществ грунт глубоко проникает в поверхность. А значит – хорошо пропитывает ее перед нанесением краски или лака. В итоге декоративное покрытие хранится намного дольше и лучше. Покупая по лучшей цене можно использовать как для внутренних помещений, так и снаружи. Систематически действует акция и скидка постоянным клиентам. ."
        },
        {
            "@id": "64960889",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960889-grunt_dulux_bindo_base_v_d_glubokogo_proniknoveniya_dlya_naruzhnikh",
            "price": "318.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/424/385_original.jpg",
            "name": "Грунт \"Dulux\" Bindo Base в/д глубокого проникновения для наружних",
            "description": "."
        },
        {
            "@id": "64960898",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960898-grunt_kontakt_beton_12_kg",
            "price": "864.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/231/795_original.jpg",
            "name": "Грунт KONTAKT-BETON 12 кг",
            "description": "Применяется для предварительной обработки гипсокартона и бетонных поверхностей, масленых и алкидных покрытий, не поддающихся полному удалению, в качестве грунтовки при укладке новой керамической плитки на старую. Для внутренних и наружных работ. - придает шероховатость гладким и слабовпитывающим основаниям; - повышает адгезию; - гарантийный срок хранения 12 месяцев"
        },
        {
            "@id": "64960899",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960899-grunt_kontakt_beton_fasad",
            "price": "956.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st2.stpulscen.ru/images/product/111/231/044_original.jpg",
            "name": "Грунт KONTAKT-BETON фасад, 12 кг",
            "description": "Для наружных внутренних работ. Применятся для предварительной обработки различных оснований с целью повышения адгезии последующих декоративных отделочных материалов (декоративных штукатурок, фактурных красок). - хорошая адгезия к бетону, кирпичу, штукатурке и другим основаниям; - водостойкая; - образует шероховатую поверхность. Грунт фасадный Подготовка поверхности Основание должно быть сухим и очищенным от загрязнений. Старые отслаивающиеся покрытия должны быть удалены. Способ нанесения Перед применением тщательно перемешать. Грунтовку наносят кистью, валиком в один слой. Не рекомендуется: Нанесение на поверхности, имеющие повышенную влажность и при температуре ниже +7°С"
        },
        {
            "@id": "64960924",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960924-gruntovka_sika_primer_3_n_1000ml",
            "price": "2066.0",
            "currencyId": "RUR",
            "categoryId": "10763",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/279_original.png",
            "name": "Грунтовка Sika Primer-3 N 1000мл",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64960946",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960946-dalnomer_lazerny_elitech_ld15",
            "price": "2104.0",
            "currencyId": "RUR",
            "categoryId": "91866",
            "name": "Дальномер лазерный ELITECH ЛД15",
            "description": []
        },
        {
            "@id": "64960947",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64960947-dalnomer_lazerny_elitech_ld60",
            "price": "4888.0",
            "currencyId": "RUR",
            "categoryId": "91866",
            "name": "Дальномер лазерный ELITECH ЛД60",
            "description": []
        },
        {
            "@id": "64961033",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961033-dobavka_v_beton_sika_1_plus_0_9l",
            "price": "370.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/200_original.png",
            "name": "Добавка в бетон Sika -1 Plus 0.9л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961034",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961034-dobavka_v_beton_sika_1_plus_5l",
            "price": "1330.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/236_original.png",
            "name": "Добавка в бетон Sika -1 Plus 5л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961035",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961035-dobavka_v_beton_sika_mix_plus_0_9l",
            "price": "344.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/237_original.png",
            "name": "Добавка в бетон Sika Mix Plus 0.9л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961036",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961036-dobavka_v_beton_sika_mix_plus_5l",
            "price": "1255.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/238_original.png",
            "name": "Добавка в бетон Sika Mix Plus 5л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961037",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961037-dobavka_v_beton_sika_plastiment_bv_3m_1l",
            "price": "308.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/239_original.png",
            "name": "Добавка в бетон Sika Plastiment BV-3M 1л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961038",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961038-dobavka_v_beton_sika_plastiment_bv_3m_6_kg",
            "price": "1107.0",
            "currencyId": "RUR",
            "categoryId": "98599",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/240_original.png",
            "name": "Добавка в бетон Sika Plastiment BV-3M 6 кг",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961057",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961057-drel_akkumulyatornaya_energomash_12v_profi",
            "price": "5634.0",
            "currencyId": "RUR",
            "categoryId": "273030",
            "name": "Дрель аккумуляторная Энергомаш 12В, профи",
            "description": "Профессиональный инструмент имеет двухскоростной редуктор, который помогает сверлить нужные отверстия в дереве и металле. А также может использоваться как шуруповерт. Надежный японский двигатель продлит срок эксплуатации инструмента. Купить можно в городах Ялте, Гурзуфе."
        },
        {
            "@id": "64961058",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961058-drel_udarnaya_elitech_du800re_800vt_2_2kg_13mm",
            "price": "2465.0",
            "currencyId": "RUR",
            "categoryId": "104746",
            "name": "Дрель ударная ELITECH ДУ800РЭ 800Вт/2,2кг/13мм",
            "description": "Ударная дрель хорошо справляется с сверлением отверстий в пластику, дереве, металле, кирпичу. Есть функции включения и выключения ударного режима, регулировки оборотов, реверсный режим. Всегда есть в наличии в нашем магазине, а для постоянных клиентов – со скидкой."
        },
        {
            "@id": "64961059",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961059-drel_udarnaya_interskol_du13_780_er",
            "price": "3434.0",
            "currencyId": "RUR",
            "categoryId": "104746",
            "name": "Дрель ударная ИНТЕРСКОЛ ДУ13/780 ЭР",
            "description": "Отлично сверлит кирпич, плитку, отверстия ровные и аккуратные. Скорость плавно регулируется. Удобный в работе инструмент с прочным корпусом обеспечен от механических повреждений. Клиентам предлагаем акции и скидки на товар в наших магазинах."
        },
        {
            "@id": "64961060",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961060-drel_udarnaya_profi_energomash_1000vt",
            "price": "3611.0",
            "currencyId": "RUR",
            "categoryId": "104746",
            "name": "Дрель ударная ПРОФИ Энергомаш 1000Вт",
            "description": "Это сверхмощная дрель, которая профессионально сверлит с ударом, вкручивает саморезы. Ручка прорезиненная, поэтому инструмент удобно держать в руке. Можно регулировать количество оборотов и пользоваться реверсным режимом. Купить можно в Крыму по лучшей цене."
        },
        {
            "@id": "64961063",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961063-drel_shurupovert_akk_elitech_da18lk2_18v_1_6kg_akb_li_ion_1_5ach",
            "price": "7879.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "name": "Дрель-шуруповерт акк. ELITECH ДА18ЛК2 18В/1,6кг/акб li-ion/1.5Ач",
            "description": []
        },
        {
            "@id": "64961064",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961064-drel_shurupovert_akk_elitech_da14lk2_14_4v_1_5kg_2akb_li_ion_1_5ach",
            "price": "7353.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "name": "Дрель-шуруповерт акк. ELITECH ДА14ЛК2 14,4В/1,5кг/2акб li-ion/1.5Ач",
            "description": "Это безударная модель дрели-шуруповерта, которая имеет съемный аккумулятор и дополнительный в комплекте. Максимальный крутящий момент достигает 32 Нм. Покупая дрель в нашем магазине, вы получаете скидку и становитесь участником распродаж."
        },
        {
            "@id": "64961065",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961065-drel_shurupovert_akk_makita_6281dwae_14_4v_1_6kg_2a_ch_2akb_nicd_bzp_keys",
            "price": "9885.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "name": "Дрель-шуруповерт акк. Makita 6281DWAE 14,4В/1,6кг/2А.ч/2АКБ NiCD/БЗП/кейс",
            "description": "Это низкооборотный инструмент, который не только сверлит отверстия, но и перемешивает строительные смеси. Имеет прочный ключевой патрон, ведется электронная регулировка количества оборотов. Редуктор имеет алюминиевое покрытие, что хорошо влияет на работу инструмента. Отменное качество по лучшей цене только в магазинах Крыма."
        },
        {
            "@id": "64961066",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961066-drel_shurupovert_profi_energomash_450vt",
            "price": "2832.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "name": "Дрель-шуруповерт ПРОФИ Энергомаш 450Вт",
            "description": "Дрель имеет быстрозажимный патрон и блокировку шпинделя, что позволяет экономить время на выполнение операций. Мягкие накладки ручки уменьшают вибрацию при работе дрели. Купить можно в магазинах рядом Ришелье Шато или возле Артека."
        },
        {
            "@id": "64961076",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961076-dyubel_dlya_izolyatsii_izl_t_10_x_100_1000_sht",
            "price": "4085.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/907_original.jpg",
            "name": "Дюбель для изоляции IZL-T 10 x 100",
            "description": "Дюбель сделан специально для крепления теплоизоляции. Подходит для минеральных поверхностей, а также для крепления изоляционных материалов на звукопоглощающих и утеплительных поверхностях – пенопласте, полистироле, стекловате. Необходимые товары можете найти в магазине рядом с Ришелье Шато, где постоянно действуют распродажи."
        },
        {
            "@id": "64961077",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961077-dyubel_dlya_izolyatsii_izl_t_10_x_200_500_sht",
            "price": "6214.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/961_original.jpg",
            "name": "Дюбель для изоляции IZL-T 10 x 200",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961078",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961078-dyubel_dlya_izolyatsii_izm_10_x_120",
            "price": "6160.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/966_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 120",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961079",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961079-dyubel_dlya_izolyatsii_izm_10_x_140_1000_sht",
            "price": "6700.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/967_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 140",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961080",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961080-dyubel_dlya_izolyatsii_izm_10_x_160_500sht",
            "price": "4898.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/968_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 160",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961081",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961081-dyubel_dlya_izolyatsii_izm_10_x_180_500sht",
            "price": "4675.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/969_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 180",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961082",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961082-dyubel_dlya_izolyatsii_izm_10_x_200_400_sht",
            "price": "5073.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/970_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 200",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961083",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961083-dyubel_dlya_izolyatsii_izm_10_x_220",
            "price": "6881.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/971_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 220",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961084",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961084-dyubel_dlya_izolyatsii_izm_10_x_260",
            "price": "8000.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/972_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 260",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961085",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961085-dyubel_dlya_izolyatsii_izm_10_x_300_400sht",
            "price": "10614.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/974_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 300",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961086",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961086-dyubel_dlya_izolyatsii_izm_10_x_90",
            "price": "3303.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/975_original.jpg",
            "name": "Дюбель для изоляции IZM 10 x 90",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961087",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961087-dyubel_dlya_izolyatsii_izo_10_x_100_1000_sht",
            "price": "1948.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/976_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 100",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961088",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961088-dyubel_dlya_izolyatsii_izo_10_x_110_1000_sht",
            "price": "1896.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/977_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 110",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961089",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961089-dyubel_dlya_izolyatsii_izo_10_x_120_1000_sht",
            "price": "1994.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/980_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 120",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961090",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961090-dyubel_dlya_izolyatsii_izo_10_x_140_500sht",
            "price": "2073.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/982_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 140",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961091",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961091-dyubel_dlya_izolyatsii_izo_10_x_160_500_sht",
            "price": "2179.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/983_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 160",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961092",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961092-dyubel_dlya_izolyatsii_izo_10_x_180_500_sht",
            "price": "2642.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/984_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 180",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961093",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961093-dyubel_dlya_izolyatsii_izo_10_x_200_500_sht",
            "price": "5881.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/985_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 200",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961094",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961094-dyubel_dlya_izolyatsii_izo_10_x_80",
            "price": "2565.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/987_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 80",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961095",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961095-dyubel_dlya_izolyatsii_izs_10_x_120",
            "price": "3202.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/988_original.jpg",
            "name": "Дюбель для изоляции IZS 10 x 120",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961096",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961096-dyubel_dlya_izolyatsii_izo_10_x_90_1000_sht",
            "price": "1565.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/989_original.jpg",
            "name": "Дюбель для изоляции IZO 10 x 90",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961097",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961097-dyubel_dlya_izolyatsii_izs_10_x_140",
            "price": "3594.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/990_original.jpg",
            "name": "Дюбель для изоляции IZS 10 x 140",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961098",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961098-dyubel_dlya_izolyatsii_izs_10_x_160",
            "price": "3867.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/992_original.jpg",
            "name": "Дюбель для изоляции IZS 10 x 160",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961099",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961099-dyubel_dlya_izolyatsii_izs_10_x_200",
            "price": "4845.0",
            "currencyId": "RUR",
            "categoryId": "124988",
            "picture": "http://st2.stpulscen.ru/images/product/111/589/994_original.jpg",
            "name": "Дюбель для изоляции IZS 10 x 200",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64961300",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961300-zatirka_zhasmin_40_ceresit_se_40_2_elastichnaya_vodootal_prot",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/054_original.jpg",
            "name": "Затирка Жасмин №40 \"Ceresit\" СЕ-40/2 эластичная водоотал. прот",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961301",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961301-zatirka_antratsit_13_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/131_original.jpg",
            "name": "Затирка Антрацит №13 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961302",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961302-zatirka_antratsit_13_ceresit_se_40_2_vodostoykaya",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/134_original.jpg",
            "name": "Затирка Антрацит №13 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961303",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961303-zatirka_bagama_43_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/136_original.jpg",
            "name": "Затирка Багама №43 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961304",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961304-zatirka_bagama_43_ceresit_se_40_2_elastichnaya_vodootal_protiv",
            "price": "356.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/137_original.jpg",
            "name": "Затирка Багама №43 \"Ceresit\" СЕ-40/2 эластичная водоотал.против",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961305",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961305-zatirka_belaya_1_ceresit_se_40_2_elastichnaya_vodootal_protivo",
            "price": "321.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/201_original.jpg",
            "name": "Затирка Белая №1 \"Ceresit\" СЕ-40/2 эластичная водоотал.противо",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961306",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961306-zatirka_belaya_1_ceresit_se_33_2_kg",
            "price": "174.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/205_original.jpg",
            "name": "Затирка Белая №1 \"Ceresit\" СЕ 33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961308",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961308-zatirka_biryuza_77_ceresit_se_40_2_vodostoykaya",
            "price": "376.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/206_original.jpg",
            "name": "Затирка Бирюза №77 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961309",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961309-zatirka_belaya_1_ceresit_se_33_5kg",
            "price": "398.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/207_original.jpg",
            "name": "Затирка Белая №1 \"Ceresit\" СЕ 33/5кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961310",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961310-zatirka_golubaya_82_ceresit_se_33_2_kg",
            "price": "435.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/274_original.jpg",
            "name": "Затирка Голубая № 82 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961311",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961311-zatirka_golubaya_82_ceresit_se_40_2_vodostoykaya",
            "price": "606.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/278_original.jpg",
            "name": "Затирка Голубая № 82 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961312",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961312-zatirka_grafit_16_ceresit_se_33_2_kg",
            "price": "220.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/280_original.jpg",
            "name": "Затирка Графит №16\"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961313",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961313-zatirka_zhasmin_40_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/281_original.jpg",
            "name": "Затирка Жасмин №40 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961314",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961314-zatirka_zelenaya_70_ceresit_se_40_2_vodostoykaya",
            "price": "461.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/324_original.jpg",
            "name": "Затирка Зелёная № 70 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961315",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961315-zatirka_zelenaya_70_ceresit_se_33_2_kg",
            "price": "435.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/328_original.jpg",
            "name": "Затирка Зелёная № 70 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961316",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961316-zatirka_chili_37_ceresit_se_40_2_vodostoykaya",
            "price": "607.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/329_original.jpg",
            "name": "Затирка Чили №37 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961348",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961348-zatirka_ultracolor_plus_bezhevy_132_2_kg",
            "price": "332.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/079_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS бежевый № 132/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961349",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961349-zatirka_ultracolor_plus_bely_100_2_kg",
            "price": "301.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/080_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS белый № 100/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961350",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961350-zatirka_ultracolor_plus_biryuzovy_171_2_kg",
            "price": "645.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/082_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS бирюзовый № 171/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961351",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961351-zatirka_ultracolor_plus_vanil_131_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/083_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS ваниль № 131/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961352",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961352-zatirka_ultracolor_plus_granatovy_61_2_kg",
            "price": "645.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/085_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS гранатовый № 61/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961353",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961353-zatirka_ultracolor_plus_goncharnaya_glina_136_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/086_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS гончарная глина № 136/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961354",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961354-zatirka_ultracolor_plus_zhasmin_130_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/088_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS жасмин № 130/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961355",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961355-zatirka_ultracolor_plus_zolotisty_pesok_135_2_kg",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/090_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS золотистый песок № 135/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961356",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961356-zatirka_ultracolor_plus_korichnevy_142_2_kg",
            "price": "325.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/092_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS коричневый № 142/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961357",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961357-zatirka_ultracolor_plus_karamel_141_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/094_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS карамель № 141/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961358",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961358-zatirka_ultracolor_plus_krasny_koral_140_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/095_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS красный корал № 140/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961359",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961359-zatirka_ultracolor_plus_lilovy_161_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/096_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS лиловый № 161/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961360",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961360-zatirka_ultracolor_plus_myata_180_2_kg",
            "price": "381.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/097_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS мята № 180/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961361",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961361-zatirka_ultracolor_plus_nefrit_181_2_kg",
            "price": "645.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/098_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS нефрит № 181/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961362",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961362-zatirka_ultracolor_plus_olivkovy_260_2_kg",
            "price": "645.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/099_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS оливковый № 260/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961363",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961363-zatirka_ultracolor_plus_pesochny_133_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/100_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS песочный № 133/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961365",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961365-zatirka_ultracolor_plus_sv_sery_111_2_kg",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/102_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS св-серый № 111/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961366",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961366-zatirka_ultracolor_plus_terrakotovy_143_2_kg",
            "price": "325.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/103_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS терракотовый № 143/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961367",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961367-zatirka_ultracolor_plus_shelk_134_2_kg",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/105_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS шёлк № 134/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961368",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961368-zatirka_ultracolor_plus_cherny_120_2_kg",
            "price": "357.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/107_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS чёрный № 120/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961369",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961369-zatirka_ultracolor_plus_shokolad_144_2_kg",
            "price": "325.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st17.stpulscen.ru/images/product/110/224/110_original.jpg",
            "name": "Затирка ULTRACOLOR PLUS шоколад № 144/2 кг",
            "description": "Все характеристирики - на сайте производителя: http://www.mapei.com/RU-RU/"
        },
        {
            "@id": "64961374",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961374-zatirka_grafit_ceresit_se_40_2_elastichnaya_vodootal_protivogrib",
            "price": "348.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/331_original.jpg",
            "name": "Затирка Графит \"Ceresit\" СЕ-40/2 эластичная водоотал.противогриб",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961377",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961377-zatirka_kakao_52_ceresit_se_40_2_vodostoykaya",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/367_original.jpg",
            "name": "Затирка Какао №52 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961379",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961379-zatirka_karamel_46_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/372_original.jpg",
            "name": "Затирка Карамель №46 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961381",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961381-zatirka_karamel_46_ceresit_se_40_2_elastichnaya_vodootal_proti",
            "price": "348.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/373_original.jpg",
            "name": "Затирка Карамель №46 \"Ceresit\" СЕ-40/2 эластичная водоотал.проти",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961382",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961382-zatirka_kivi_67_ceresit_se_40_2_vodostoykaya",
            "price": "461.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/374_original.jpg",
            "name": "Затирка Киви №67 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961383",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961383-zatirka_kirpich_49_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/458_original.jpg",
            "name": "Затирка Кирпич №49 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961384",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961384-zatirka_kirpich_49_ceresit_se_40_2_elastichnaya_vodootal_protivo",
            "price": "356.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/462_original.jpg",
            "name": "Затирка Кирпич №49 \"Ceresit\" СЕ-40/2 эластичная водоотал.противо",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961386",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961386-zatirka_krokus_79_ceresit_se_40_2_elastichnaya_vodootal_protiv",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/466_original.jpg",
            "name": "Затирка Крокус №79 \"Ceresit\" СЕ-40/2 эластичная водоотал.против",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961387",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961387-zatirka_lavanda_87_ceresit_se_40_2_vodostoykaya",
            "price": "451.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/467_original.jpg",
            "name": "Затирка Лаванда №87 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961389",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961389-zatirka_mankhetten_10_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/501_original.jpg",
            "name": "Затирка Манхеттен №10 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961390",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961390-zatirka_mankhetten_10_ceresit_se_40_2_vodostoykaya",
            "price": "348.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/504_original.jpg",
            "name": "Затирка Манхеттен №10 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961391",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961391-zatirka_melba_22_ceresit_se_40_2_elastichnaya_vodootal_protiv",
            "price": "348.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/505_original.jpg",
            "name": "Затирка Мельба №22 \"Ceresit\" СЕ-40/2 эластичная водоотал.против",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961392",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961392-zatirka_myata_64_ceresit_se_40_2_elastichnaya_vodootal_protivog",
            "price": "367.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/507_original.jpg",
            "name": "Затирка Мята №64 \"Ceresit\" СЕ-40/2 эластичная водоотал.противог",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961393",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961393-zatirka_natura_41_ceresit_se_40_2_elastichnaya_vodootal_proti",
            "price": "348.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/556_original.jpg",
            "name": "Затирка Натура № 41 \"Ceresit\" СЕ-40/2 эластичная водоотал.проти",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961394",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961394-zatirka_natura_41_ceresit_se_33_2kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/558_original.jpg",
            "name": "Затирка Натура №41 \"Ceresit\" СЕ-33/2кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961395",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961395-zatirka_nebesny_80_ceresit_se_40_2_vodostoykaya",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/560_original.jpg",
            "name": "Затирка Небесный №80 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961396",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961396-zatirka_olivkovaya_73_ceresit_se_33_2kg",
            "price": "234.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/561_original.jpg",
            "name": "Затирка Оливковая №73 \"Ceresit\" СЕ 33/2кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961397",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961397-zatirka_persik_28_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/606_original.jpg",
            "name": "Затирка Персик №28 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961398",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961398-zatirka_persik_28_ceresit_se_40_2_vodostoykaya",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/608_original.jpg",
            "name": "Затирка Персик №28 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961399",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961399-zatirka_rozovaya_34_ceresit_se_33_2kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/609_original.jpg",
            "name": "Затирка Розовая №34 \"Ceresit\" СЕ-33/2кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961400",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961400-zatirka_rozovaya_34_ceresit_se_40_2_vodostoykaya",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/610_original.jpg",
            "name": "Затирка Розовая №34 \"Ceresit\" СЕ-40/2 водостойкая",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961401",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961401-zatirka_rosa_31_ceresit_se_40_2_elastichnaya_vodootal_protivogr",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/643_original.jpg",
            "name": "Затирка Роса №31 \"Ceresit\" СЕ-40/2 эластичная водоотал.противогр",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961402",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961402-zatirka_rosa_31_ceresit_se_33_2_kg",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "116724",
            "picture": "http://st21.stpulscen.ru/images/product/118/607/646_original.jpg",
            "name": "Затирка Роса №31 \"Ceresit\" СЕ-33/2 кг",
            "description": "Все характеристики затирок на сайте производителя: www.ceresit.ru"
        },
        {
            "@id": "64961477",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961477-kabel_greyushchi_iq_floor_cable_20vt_2_30_m",
            "price": "7272.0",
            "currencyId": "RUR",
            "categoryId": "143765",
            "picture": "http://st2.stpulscen.ru/images/product/111/895/059_original.jpg",
            "name": "Кабель греющий IQ FLOOR CABLE (20Вт/ь2) 30 м",
            "description": "Используется для монтажа теплого пола. Кабель фиксируется на самоклеющуюся сетку, а тонкий мат можно использовать под любую плитку. Если правильно установить кабель, то теплые полы по всему помещению обеспечены. Делайте покупки в нашем магазине и участвуйте в акциях и распродажах.."
        },
        {
            "@id": "64961480",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961480-kabel_pvs_2_1_5",
            "price": "39.0",
            "currencyId": "RUR",
            "categoryId": "141632",
            "picture": "http://st2.stpulscen.ru/images/product/111/897/390_original.jpg",
            "name": "Кабель ПВС 2*1,5",
            "description": "Провод применяют при установки электричества в осветительных сетях. Первый класс гибкости позволяет использовать его при фиксированном монтаже не только машин механизмов, но и станков. Продается в магазине возле Артека или рядом с Ришелье Шато.."
        },
        {
            "@id": "64961481",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961481-kabel_pvs_3_2_5",
            "price": "80.0",
            "currencyId": "RUR",
            "categoryId": "141632",
            "picture": "http://st2.stpulscen.ru/images/product/111/904/735_original.jpg",
            "name": "Кабель ПВС 3*2,5",
            "description": "Провод применяют при установки электричества в осветительных сетях. Первый класс гибкости позволяет использовать его при фиксированном монтаже не только машин механизмов, но и станков. Продается в магазине возле Артека или рядом с Ришелье Шато. ."
        },
        {
            "@id": "64961483",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961483-kabel_shvvp_3_2_5",
            "price": "77.0",
            "currencyId": "RUR",
            "categoryId": "141632",
            "picture": "http://st2.stpulscen.ru/images/product/111/905/601_original.jpg",
            "name": "Кабель ШВВП 3*2,5",
            "description": "Кабель удобно использовать для того, чтобы монтировать скрытую проводку в стене он имеет плоскую форму и отличается высокой гибкостью. Больше всего используется для внутренней проводки. Есть в наличии в наших магазинах в Ялте, Гурзуфе. ."
        },
        {
            "@id": "64961484",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961484-kabel_kanal_16_16",
            "price": "25.0",
            "currencyId": "RUR",
            "categoryId": "10453",
            "picture": "http://st2.stpulscen.ru/images/product/111/905/785_original.jpg",
            "name": "Кабель-канал 16*16",
            "description": "Длина: 2 метра."
        },
        {
            "@id": "64961486",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961486-kabelny_korob_20kh10mm_2_0m_ideal",
            "price": "25.0",
            "currencyId": "RUR",
            "categoryId": "10453",
            "picture": "http://st14.stpulscen.ru/images/product/113/146/481_original.jpg",
            "name": "Кабельный короб 20х10мм 2,0м \"Идеал\"",
            "description": "Наш магазин в шаговой доступности - Гурзуф, Коаснокаменка, возле Артека, рядом с Ришелье Шато. Сухие смеси от производителя, каждому покупателю - скидка, постоянно распродажа, именно сейчас - акция."
        },
        {
            "@id": "64961567",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961567-keramzit_10kg_b_u",
            "price": "140.0",
            "currencyId": "RUR",
            "categoryId": "145466",
            "picture": "http://st2.stpulscen.ru/images/product/111/079/394_original.jpg",
            "name": "Керамзит в мeшках фр.10-20мм",
            "description": "Самый популярный насыпной утеплитель."
        },
        {
            "@id": "64961581",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961581-kirpich_m_100_ryadovoy",
            "price": "19.0",
            "currencyId": "RUR",
            "categoryId": "10455",
            "picture": "http://st17.stpulscen.ru/images/product/110/712/451_original.jpg",
            "name": "Кирпич М-100 рядовой (забутовочный)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961582",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961582-kirpich_ogneuporny_shamotny",
            "price": "74.0",
            "currencyId": "RUR",
            "categoryId": "10455",
            "picture": "http://st17.stpulscen.ru/images/product/110/710/662_original.jpg",
            "name": "Кирпич огнеупорный Шамотный",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961583",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961583-kislorod_gazoobrazny_tekhnicheski_40l_6_3m3",
            "price": "760.0",
            "currencyId": "RUR",
            "categoryId": "122210",
            "picture": "http://st17.stpulscen.ru/images/product/110/780/964_original.jpg",
            "name": "Кислород газообразный технический ( 40л-6,3м3)",
            "description": "В большинстве случаев для сварки и резки металла «испокон веков» применяется сжатый под давлением кислород. Для строительства коммунальных сетей (подвод/починка водопровода, отопления и газификации) наиболее часто применяют газовую сварку. Газовая резка используются для разделки изделий  из металлопроката по предварительным чертежам или «на месте». После чего применяется газовая сварка. Баллоны соответствуют ПБ 10-115-96 и ГОСТ 949-73, их содержимое – ГОСТ 5583-78. В наличии и под заказ в Крыму (г. Ялта, пгт. Гурзуф) можно купить баллоны объемом 40 л. Все ГОСТы и ПБ соблюдены.   ПРОСИМ УЧЕСТЬ: во избежание ошибок при работе и наилучшего качества, просим правильно включать горелку перед началом работ. А именно, подача газовой смеси должна быть плавной при зажигании и при достижении максимальной температуры, тогда будет получен наилучший эффект для достижения необходимых целей.   ВНИМАНИЕ!!! При самовывозе просим обеспечить 100%-е безопасное закрепление баллонов. Мы проверяем.   Предоставляются услуги доставки (в том числе бесплатной) в зависимости от объемов заказа.   ДОПОЛНИТЕЛЬНО: 1. Обмен баллонов. 2. Залог баллонов от 3000 руб.   Наша компания имеет большой опыт комплексного снабжения объектов капитального строительства. В наличии имеются все паспорта и сертификаты на весь предоставленный товар. Возможен как наличный, так и безналичный расчет. Мы работаем с НДС. У нас Вы можете получить скидки, которые Вас несомненно порадуют."
        },
        {
            "@id": "64961584",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961584-kist_matrix_kruglaya_s_derevyannoy_ruchkoy_8_35mm_12_480",
            "price": "35.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/282/940_original.jpg",
            "name": "Кисть \"Matrix\" круглая с деревянной ручкой № 8 (35мм) (12/480)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961585",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961585-kist_matrix_kruglaya_s_derevyannoy_ruchkoy_12_45mm_12_240",
            "price": "87.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/282/980_original.jpg",
            "name": "Кисть \"Matrix\" круглая с деревянной ручкой №12 (45мм) (12/240)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961586",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961586-kist_matrix_kruglaya_s_derevyannoy_ruchkoy_14_50mm_1_12_240",
            "price": "105.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/282/984_original.jpg",
            "name": "Кисть \"Matrix\" круглая с деревянной ручкой №14 (50мм) (1/12/240)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961587",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961587-kist_matrix_kruglaya_s_derevyannoy_ruchkoy_18_60mm_1_12_120",
            "price": "159.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/282/985_original.jpg",
            "name": "Кисть \"Matrix\" круглая с деревянной ручкой №18 (60мм) (1/12/120)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961598",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961598-kist_malyarnaya_ploskaya_slim_50_mm",
            "price": "27.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/284/050_original.jpg",
            "name": "Кисть малярная плоская \"Slim\", 50 мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961599",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961599-kist_malyarnaya_ploskaya_standart_20mm_hobby",
            "price": "15.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/284/109_original.jpg",
            "name": "Кисть малярная плоская \"Standart\" 20мм HOBBY",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961601",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961601-kist_malyarnaya_ploskaya_standart_50mm",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/284/113_original.jpg",
            "name": "Кисть малярная плоская \"Standart\" 50мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961603",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961603-kist_ploskaya_profi_100mm_svetlaya_naturalnaya_shchetina_plastik",
            "price": "210.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/285/245_original.jpg",
            "name": "Кисть плоская \"Профи\" 100мм, светлая, натуральная щетина, пластик",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961604",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961604-kist_ploskaya_profi_25mm_svetlaya_naturalnaya_shchetina_plastiko",
            "price": "31.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/285/295_original.jpg",
            "name": "Кисть плоская \"Профи\" 25мм, светлая, натуральная щетина, пластико",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961605",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961605-kist_ploskaya_profi_50mm_svetlaya_naturalnaya_shchetina_plastiko",
            "price": "75.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/285/303_original.jpg",
            "name": "Кисть плоская \"Профи\" 50мм, светлая, натуральная щетина, пластико",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961606",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961606-kist_ploskaya_profi_75mm_svetlaya_naturalnaya_shchetina_plastiko",
            "price": "123.0",
            "currencyId": "RUR",
            "categoryId": "106925",
            "picture": "http://st2.stpulscen.ru/images/product/111/285/304_original.jpg",
            "name": "Кисть плоская \"Профи\" 75мм, светлая, натуральная щетина, пластико",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961607",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961607-kist_ploskaya_stayer_universal_profi_100mm_0104_100",
            "price": "230.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/286/228_original.jpg",
            "name": "Кисть плоская STAYER \"UNIVERSAL-PROFI\" 100мм(0104-100)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961608",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961608-kist_ploskaya_stayer_universal_profi_20mm_0104_020",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/286/280_original.jpg",
            "name": "Кисть плоская STAYER \"UNIVERSAL-PROFI\" 20мм(0104-020)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961609",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961609-kist_ploskaya_stayer_universal_profi_38mm_0104_038",
            "price": "68.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/286/287_original.jpg",
            "name": "Кисть плоская STAYER \"UNIVERSAL-PROFI\" 38мм(0104-038)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961610",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961610-kist_ploskaya_stayer_universal_profi_50mm_0104_050",
            "price": "86.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/286/290_original.jpg",
            "name": "Кисть плоская STAYER \"UNIVERSAL-PROFI\" 50мм(0104-050)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961611",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961611-kist_ploskaya_stayer_universal_profi_75mm_0104_075",
            "price": "185.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/286/292_original.jpg",
            "name": "Кисть плоская STAYER \"UNIVERSAL-PROFI\" 75мм(0104-075)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961618",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961618-kist_radiatornaya_2_0_sigma",
            "price": "52.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/287/929_original.jpg",
            "name": "Кисть радиаторная 2,0 SIGMA",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961619",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961619-kist_radiatornaya_1_0_sigma",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/288/059_original.jpg",
            "name": "Кисть радиаторная 1,0\" SIGMA",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961620",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961620-kist_radiatornaya_1_0_25mm_work",
            "price": "21.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/288/067_original.jpg",
            "name": "Кисть радиаторная 1,0\"/25мм WORK",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961621",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961621-kist_radiatornaya_1_5_sigma",
            "price": "42.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/288/068_original.jpg",
            "name": "Кисть радиаторная 1,5 SIGMA",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961622",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961622-kist_radiatornaya_1_5_38mm_work",
            "price": "33.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/288/070_original.jpg",
            "name": "Кисть радиаторная 1,5\"/38мм WORK",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961623",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961623-kist_radiatornaya_2_5_63mm_work",
            "price": "45.0",
            "currencyId": "RUR",
            "categoryId": "10821",
            "picture": "http://st2.stpulscen.ru/images/product/111/288/071_original.jpg",
            "name": "Кисть радиаторная 2,5\"/63мм WORK",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961698",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961698-kley_dlya_keramogranita_mramora_kamnya_universal_25_kg",
            "price": "381.0",
            "currencyId": "RUR",
            "categoryId": "116768",
            "picture": "http://st13.stpulscen.ru/images/product/112/682/283_original.jpg",
            "name": "Клей для керамогранита, мрамора, камня, \"UNIVERSAL\", 25 кг",
            "description": "ПОДГОТОВКА ОСНОВАНИЯ Основание должно быть плотным, обладать достаточными несущими способностями и предварительно очищенными от разного рода загрязнений, препятствующих адгезии веществ (пыли, грязи, жиров, масел, копоти, следов краски). Поверхность может быть сухой или влажной. Большие неровности и осыпающийся слой необходимо устранить. Окрашенные поверхности следует тщательно очистить. Рекомендуется не менее чем за 2 часа до проведения работ обработать основание грунтом глубокого проникновения SR-51. ПРИГОТОВЛЕНИЕ РАСТВОРНОЙ СМЕСИ Клей готовится путем смешивания сухого клея с чистой водой до получения однородной массы без комков. Рекомендуемое количество воды: около 1л на 6 кг сухого клея. При больших количествах замешиваемого клея необходимо использовать мешалку с малыми оборотами. После перемешивания клея отстоять 5-10 минут и снова перемешать. Клей готов к применению. РЕКОМЕНДАЦИИ ПРИ ВЫПОЛНЕНИИ РАБОТ Работы выполнять при температуре основания от +5 до + 30°С. На подготовленное основание клей наносится слоем не более 5мм. И распределяется по поверхности при помощи зубчатой терки с размерами зубьев от 3 до 8 мм. Не рекомендуется наносить клей сразу на большую поверхность, так как он сохраняет свои клеящие свойства в течение 15 минут после нанесения на основания."
        },
        {
            "@id": "64961699",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961699-kley_dlya_krepleniya_teploizolyatsii_universal_25_kg",
            "price": "440.0",
            "currencyId": "RUR",
            "categoryId": "151680",
            "picture": "http://st13.stpulscen.ru/images/product/112/682/334_original.jpg",
            "name": "Клей для крепления теплоизоляции \"UNIVERSAL\", 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Влажность поверхности не имеет значения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51 или «Бетон-Контакт» в зависимости от типа основания. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпайте смесь в удобный для перемешивания сосуд, заполненный тёплой водой из расчёта четыре — пять литров воды на мешок сухой смеси, тщательно перемешивая. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пять-десять и ещё раз быстро размешайте. Не используйте готовую смесь, если она простояла более двух с половиной часов. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) или сыро — не работайте с клеем. Избегайте попадания солнца, ветра и дождя на свежую клеевую поверхность (при работе на фасадах). Наносите клей на внутреннюю сторону плиты полосой три-четыре сантиметра по контуру и лепёшками в центр плиты — несколько штук диаметром примерно десять сантиметров и толщиной примерно два сантиметра. Нанесите смесь, приложите плиту к поверхности стены, слегка прижмите и корректируйте её положение в течение десяти-пятнадцати минут. Крепление дюбелями-«парашютами» делайте не раньше, чем через двое суток. Берегите глаза от попадания раствора."
        },
        {
            "@id": "64961705",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961705-kley_dlya_plitki_universal_dlya_vnutrennikh_rabot_25_kg",
            "price": "290.0",
            "currencyId": "RUR",
            "categoryId": "116813",
            "picture": "http://st13.stpulscen.ru/images/product/112/682/420_original.jpg",
            "name": "Клей для плитки \"UNIVERSAL\", 25 кг",
            "description": "ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для клея. Если есть бугры, счистите их, а отслоения удалите. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Влажность поверхности не имеет значения. За два часа до нанесения клея прогрунтуйте основание рекомендованной грунтовкой: SR-51. КАК ПРИГОТОВИТЬ КЛЕЙ: Высыпите порошок в удобный для перемешивания сосуд. Вливайте воду, доводя до консистенции густой сметаны. Комочки тут же разминайте. Соотношение порошка к воде обычно шесть к одному. Если готовите очень много клея, используйте механическую мешалку, но только с малой скоростью вращения. Дайте отстояться полученной смеси минут пятнадцать и ещё раз быстро размешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте с клеем. Наносите клей и разравнивайте шпателем с зубьями (3-8мм) — это экономит смесь и предотвращает выдавливание в щели. Помните о мере — слишком большие поверхности нужно обработать частями. Прижимайте плитку к нанесённому раствору без усилий. У Вас есть десять минут для исправления положения плитки. Полная готовность работы наступает через сутки для стен и через трое суток для полов — берегите плитку от нагрузок в этот период. ВНИМАНИЕ: ЗАМАЧИВАТЬ ПЛИТКУ ПЕРЕД ПРИКЛЕИВАНИЕМ НЕ ТРЕБУЕТСЯ!"
        },
        {
            "@id": "64961708",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961708-kley_dlya_plitki_universal_sika_ceram_universal_25kg",
            "price": "675.0",
            "currencyId": "RUR",
            "categoryId": "116813",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/244_original.png",
            "name": "Клей для плитки универсал. Sika Ceram Universal 25кг",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961709",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961709-kley_dlya_plitki_universal_sika_ceram_pro_25kg",
            "price": "1009.0",
            "currencyId": "RUR",
            "categoryId": "116813",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/245_original.png",
            "name": "Клей для плитки универсал. Sika Ceram Pro 25кг",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64961748",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961748-kley_pena_poliuret_bytovoy_montazh_vsesez_dlya_teploiz_plit_i_dekora_quot",
            "price": "349.0",
            "currencyId": "RUR",
            "categoryId": "273433",
            "picture": "http://st17.stpulscen.ru/images/product/110/778/520_original.jpg",
            "name": "Клей-пена полиурет бытовой монтаж. всесез. для теплоиз. плит и декора \"PROF",
            "description": "Однокомпонентный полиуретановый вспенивающийся клей благодаря применению технологии MMA® имеет низкое расширение и высокую адгезию к большинству строительных материалов, за исключением полиэтилена, полипропилена и тефлона. Рекомендуется для крепления теплоизоляционных плит из пенополистирола (EPS и XPS), пенополиуретана (PUR и PIR), минеральной ваты на бетонные, кирпичные, каменные, металлические, оштукатуренные, битумные и деревянные поверхности в различных системах наружной и внутренней теплоизоляции, при теплоизоляции кровель, а также уплотнения стыков между плитами при этих работах."
        },
        {
            "@id": "64961749",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961749-klema_3_kont_universal_0_08_2_5mm",
            "price": "38.0",
            "currencyId": "RUR",
            "categoryId": "136227",
            "picture": "http://st14.stpulscen.ru/images/product/113/146/638_original.png",
            "name": "Клема 3-конт.универсал.0,08-2,5мм",
            "description": "Мы находимся в поселке Гурзуф, Ялта. Бесплатная доставка при покупке свыше 5000 рублей. Крым - наши лучшие покупатели! Товар (сухие смеси) весегда в наличии. Так как у нас свое производство, то и лучшая цена, а для организаций - безнал с НДС. Живете в Краснокаменке или Гурзуфе - мы рядом с домом, в шаговой доступности: возле Артека, рядом с Ришелье Шато. Ищете товар от производителя - тогда к нам! При первой же покупке скидка 5%, постоянная распродажа, сейчас - акция."
        },
        {
            "@id": "64961754",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961754-kleshchi_tokovyye_266_ngy",
            "price": "1823.0",
            "currencyId": "RUR",
            "categoryId": "74305",
            "picture": "http://st14.stpulscen.ru/images/product/113/146/770_original.jpg",
            "name": "Клещи токовые 266 NGY",
            "description": "Мы находимся в поселке Гурзуф, Ялта. Бесплатная доставка при покупке свыше 5000 рублей. Крым - наши лучшие покупатели! Товар (сухие смеси) весегда в наличии. Так как у нас свое производство, то и лучшая цена, а для организаций - безнал с НДС. Живете в Краснокаменке или Гурзуфе - мы рядом с домом, в шаговой доступности: возле Артека, рядом с Ришелье Шато. Ищете товар от производителя - тогда к нам! При первой же покупке скидка 5%, постоянная распродажа, сейчас - акция."
        },
        {
            "@id": "64961767",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961767-klipsy_nabornyye_d_16mm",
            "price": "3.0",
            "currencyId": "RUR",
            "categoryId": "170853",
            "picture": "http://st14.stpulscen.ru/images/product/113/146/857_original.png",
            "name": "Клипсы наборные D-16мм",
            "description": "Клипсы – это пластиковые крепления для металлопластиковых труб, металлорукавов и гофрорукавов. Благодаря клипсам разных диаметров можно максимально аккуратно прокладывать трубы. Для того чтобы купить нужное количество клипс, обратитесь в магазины Крыма – рядом с Артеком, возле Ришелье Шато."
        },
        {
            "@id": "64961809",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961809-kolodka_3gn_s_z_era_k_3e",
            "price": "331.0",
            "currencyId": "RUR",
            "categoryId": "169039",
            "picture": "http://st14.stpulscen.ru/images/product/113/401/006_original.jpg",
            "name": "Колодка 3гн. с/з ЭРА (К-3е)",
            "description": "Колодка сделана из прочного пластика, не имеет в составе токсических веществ. Защитные шторки оберегают контакты от попадания пыли и сторонних предметов. Крепление проводов с помощью колодки – надежное и долговечное. Предлагаем жителям Крыма по лучшей цене.."
        },
        {
            "@id": "64961882",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961882-korobka_raspredelitelnaya_85_85_40",
            "price": "92.0",
            "currencyId": "RUR",
            "categoryId": "115886",
            "picture": "http://st14.stpulscen.ru/images/product/113/402/326_original.jpg",
            "name": "Коробка распределительная 85*85*40",
            "description": "Распределительные коробки используют в слаботочных и силовых сетях. Установка труд через специальные сальники обеспечивают хорошую изоляцию проводки. Коробка легко монтируется с помощью специальных креплений. Есть в наличии в магазинах Ялты.   ."
        },
        {
            "@id": "64961932",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961932-kraska_dulux_acryl_matt_v_d_dlya_sten_i_potolkov_matovaya_baza",
            "price": "1499.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/788/935_original.jpg",
            "name": "Краска \"Dulux\" Acryl Matt в/д для стен и потолков матовая база 9л",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961933",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961933-kraska_dulux_acryl_matt_v_d_dlya_sten_i_potolkov_matovaya_baza",
            "price": "819.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/789/405_original.jpg",
            "name": "Краска \"Dulux\" Acryl Matt в/д для стен и потолков матовая база",
            "description": "Акриловое матовое покрытие можно купить по лучшей цене. Оно помогает скрыть неровности поверхностей, а также создать стильный декор в помещение. Благодаря большому количеству цветов, которые всегда есть в наличии можно выбрать нужный оттенок. Отличается экономностью в расходовании и легкостью нанесения."
        },
        {
            "@id": "64961935",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961935-kraska_dulux_bindo_2_v_d_dlya_potolkov_glubokomatovaya_snezhno_be",
            "price": "2529.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/790/135_original.jpg",
            "name": "Краска \"Dulux\" Bindo 2 в/д для потолков глубокоматовая снежно-бе",
            "description": "Краска гарантирует глубокое окрашиванье с высокой степенью яркости цвета. Отлично подходит для окрашивания новых минеральных поверхностей (все цвета есть в магазине возле Артека). Благодаря специально разработанной текстуре краску удобно наносить на потолок и разравнивать. Во время акции приобретение краски становится еще выгоднее."
        },
        {
            "@id": "64961936",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961936-kraska_dulux_bindo_2_v_d_dlya_potolkov_glubokomatovaya_snezhno_be",
            "price": "1476.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/790/770_original.jpg",
            "name": "Краска \"Dulux\" Bindo 2 в/д для потолков глубокоматовая снежно-бе",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961937",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961937-kraska_dulux_bindo_3_v_d_dlya_sten_i_potolkov_glubokomatovaya_ba",
            "price": "427.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/536/702_original.jpg",
            "name": "Краска \"Dulux\" Bindo 3 в/д для стен и потолков глубокоматовая база BW 1л.",
            "description": "Краску можно применять в помещениях с невысоким уровнем влажности. Она быстро высыхает и не оставляет резкого запаха. Равномерно наносится на поверхности из кирпича, штукатурки, бетона и другие. Окрашенная поверхность требует аккуратного ухода и легкого мытья. Купить краску можно в сети магазинов Ялты по наличному, а также безналичному расчету с НДС."
        },
        {
            "@id": "64961938",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961938-kraska_dulux_bindo_3_v_d_dlya_sten_i_potolkov_glubokomatovaya_ba",
            "price": "3503.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/795/876_original.jpg",
            "name": "Краска \"Dulux\" Bindo 3 в/д для стен и потолков глубокоматовая база 10л",
            "description": "Краска от производителя с глубокой матовостью цветов создана для окрашивания кирпичных, бетонных стен, а также гипсокартона. Безвредный состав краски подходит для использованья в больницах и поликлиниках. Применять следует в помещениях с ограниченным количеством уборок и средней влажностью. Предлагаем краску по лучшей цене."
        },
        {
            "@id": "64961939",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961939-kraska_dulux_bindo_3_v_d_dlya_sten_i_potolkov_glubokomatovaya_ba",
            "price": "1994.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/791/667_original.jpg",
            "name": "Краска \"Dulux\" Bindo 3 в/д для стен и потолков матовая база BW (5л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961941",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961941-kraska_dulux_bindo_7_v_d_dlya_sten_i_potolkov_matovaya_baza_bc",
            "price": "353.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/542/197_original.jpg",
            "name": "Краска \"Dulux\" Bindo 7 в/д для стен и потолков матовая база BC (0,9л)",
            "description": "Латексная краска наносится ровным тонким слоем, под которым хорошо видно очертание декоративной штукатурки, лепки или рельефных обоев. Подходит для жилых помещений, имеет сертификат для использованья в государственных учреждениях. Окрашенную поверхность можно чистить с помощью моющих средств. В наличии – самые популярные и стильные цвета. На большое количество заказа полагается скидка."
        },
        {
            "@id": "64961943",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961943-kraska_dulux_bindo_7_v_d_dlya_sten_i_potolkov_matovaya_baza_bc",
            "price": "932.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/542/198_original.jpg",
            "name": "Краска \"Dulux\" Bindo 7 в/д для стен и потолков матовая база BC (2,25л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961944",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961944-kraska_dulux_bindo_7_v_d_dlya_sten_i_potolkov_matovaya_baza_bw",
            "price": "511.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/542/074_original.jpg",
            "name": "Краска \"Dulux\" Bindo 7 в/д для стен и потолков матовая база BW (1,0л)",
            "description": "Глубокая матовая краска всех цветов подходит для создания комфорта и уюта в доме, кабинете или организации. Наносить надо на полностью высохшие поверхности, чтобы достичь идеального результата. Используется только для проведения внутренних работ. Купить можно по лучшей цене без переплат от производителя."
        },
        {
            "@id": "64961946",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961946-kraska_dulux_bindo_7_v_d_dlya_sten_i_potolkov_matovaya_baza_bw",
            "price": "4014.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/542/127_original.jpg",
            "name": "Краска \"Dulux\" Bindo 7 в/д для стен и потолков матовая база BW (10л)",
            "description": "."
        },
        {
            "@id": "64961947",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961947-kraska_dulux_bindo_7_v_d_dlya_sten_i_potolkov_matovaya_baza_bw",
            "price": "2407.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/542/172_original.jpg",
            "name": "Краска \"Dulux\" Bindo 7 в/д для стен и потолков матовая база BW (5л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961950",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961950-kraska_dulux_easy_v_d_dlya_oboyev_i_sten_matovaya_baza_bw_10l",
            "price": "3761.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/689/280_original.jpg",
            "name": "Краска \"Dulux\" Easy в/д для обоев и стен матовая база BW (10л)",
            "description": "Краска от производителя специально предназначена не только для стен, но и для обоев. Даже после многочисленного перекрашивания она ложится равномерным слоем, создавая визуально эффект идеально ровной поверхности. Краска имеет высокую укрывистость. Реализовывается в магазинах Гурзуфа, Ялты, Крыма."
        },
        {
            "@id": "64961951",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961951-kraska_dulux_easy_v_d_dlya_oboyev_i_sten_matovaya_baza_bw_2_5l",
            "price": "1221.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/689/310_original.jpg",
            "name": "Краска \"Dulux\" Easy в/д для обоев и стен матовая база BW (2.5л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961952",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961952-kraska_dulux_easy_v_d_dlya_oboyev_i_sten_matovaya_baza_bw_5l",
            "price": "2248.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/689/354_original.jpg",
            "name": "Краска \"Dulux\" Easy в/д для обоев и стен матовая база BW (5л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961953",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961953-kraska_dulux_kitchen_bathroom_v_d_dlya_sten_i_potolkov_matovaya",
            "price": "871.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/689/707_original.jpg",
            "name": "Краска \"Dulux\" Kitchen & Bathroom в/д для стен и потолков матовая",
            "description": "Благодаря специальным добавкам краска создает качественное укрытие, которое не поддается разрушительному действию грибка, конденсата и паров. Приобретая по лучшей цене, ее можно наносить на поверхности со старыми покрытиями. Подходит для применения в комнатах, которые поддаются постоянным уборкам с химическими средствами. Во время распродажи клиенты существенно экономят на покупке."
        },
        {
            "@id": "64961954",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961954-kraska_dulux_master_alkidnaya_universalnaya_polumat_baza_bw_2",
            "price": "1943.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/698/393_original.jpg",
            "name": "Краска \"Dulux\" Master алкидная универсальная полумат. база BW (2,5л.)",
            "description": "Краска от производителя отлично подходит для окрашиванья дерева и метала. Использовать можно как во внутренних помещениях, так и снаружи. Создает полуматовый блеск, который со временем не теряется и не выцветает. Если ухаживать за окрашенной поверхностью без абразивных средств, то она долго будет хранить первобытный вид. Предлагаем все цвета по лучшей цене."
        },
        {
            "@id": "64961955",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961955-kraska_dulux_master_alkidnaya_universalnaya_polumat_baza_bw_2",
            "price": "1973.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/698/394_original.jpg",
            "name": "Краска \"Dulux\" Master алкидная универсальная полумат. база BW (2,5л.)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961956",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961956-kraska_dulux_master_alkidnaya_universalnaya_glyantsevaya_baza_bw",
            "price": "889.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/695/545_original.jpg",
            "name": "Краска \"Dulux\" Master алкидная универсальная глянцевая база BW (1л) (10113",
            "description": "Одна из немногих видов красок, которая выдерживает высокие температуры и постоянную влажность. Быстро наносится на поверхность, экономя не только время, но и количество расходуемого материала. Ведь при окрашиванье потеки не образовываются, а сама краска не разбрызгивается. Если действует акция, то цена на краску значительно уменьшается. Нужный оттенок можно купить в магазине возле Артека."
        },
        {
            "@id": "64961959",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961959-kraska_dulux_master_alkidnaya_universalnaya_polumatovaya_baza_bw",
            "price": "889.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/699/782_original.jpg",
            "name": "Краска \"Dulux\" Master алкидная универсальная полуматовая база BW (1л)",
            "description": "Экологичная краска от мирового брэнда."
        },
        {
            "@id": "64961960",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64961960-kraska_dulux_master_alkidnaya_universalnaya_polumat_baza_bs_2",
            "price": "1554.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st13.stpulscen.ru/images/product/112/699/340_original.jpg",
            "name": "Краска \"Dulux\" Master алкидная универсальная полумат. база BС (2,25л)",
            "description": "Краска обладает универсальностью применения. Ее можно использовать для окрашивания радиаторов, поскольку она хорошо переносит высокие температуры. А также – для придания цвета деревянным и бетонным поверхностям. Краска от производителя отлично подходит для окрашиванья окон, дверей. Покупая по лучшей цене, вы почувствуете существенную экономию."
        },
        {
            "@id": "64962061",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962061-kraska_marshall_fasad_v_d_dlya_fasadnykh_poverkhnostey_glubokomat",
            "price": "401.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st17.stpulscen.ru/images/product/110/562/469_original.png",
            "name": "Краска \"Marshall\" Фасад+ в/д для фасадных поверхностей глубокомат 2,5л",
            "description": "Глубокоматовая краска от производителя подходит для окрашивания наружных объектов (балконов, гаражей, лоджий в Ялте, Крыму) и внутренних помещений. Благодаря созданию матового покрытия она скрывает небольшие дефекты и царапины. На протяжении восьми лет сохраняет цвет и структуру, несмотря на атмосферное влияние."
        },
        {
            "@id": "64962063",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962063-kraska_marshall_fasad_v_d_dlya_fasadnykh_poverkhnostey_glubokomat",
            "price": "1501.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st17.stpulscen.ru/images/product/110/562/494_original.png",
            "name": "Краска \"Marshall\" Фасад+ в/д для фасадных поверхностей глубокомат 9л",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64962124",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962124-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_alaya_425ml_1213_1",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/913_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ алая 425мл(1213-1)",
            "description": "Аэрозольная краска от производителя имеет акриловую основу и подходит для окрашиванья окон, дверей, других деревянных, кирпичных, бетонных поверхностей. Помогает создать нужный декор в других видах работ. Может использоваться во внутренних помещениях и наружных. Рекомендуется для приобретения оптовыми партиями по расчету безнал с НДС."
        },
        {
            "@id": "64962125",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962125-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_belaya_425ml_1210_1",
            "price": "167.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/992_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ белая 425мл(1210-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962126",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962126-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_belaya_s_fluorests_effektom_4",
            "price": "252.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/994_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ белая с флуоресц. эффектом 4",
            "description": "Краски созданы специально для автомобильной промышленности. Государственные учреждения имеют возможность рассчитываться за покупку по безналичному расчету с НДС. Краски содержат специальные светоотражающие частицы, которые святятся под ультрафиолетом и помогают достичь флоп-эффекта. В зависимости от того, с какого угла вы будете смотреть на окрашенную поверхность, так она и будет отражаться. В наличии большие и компактные фасовки."
        },
        {
            "@id": "64962128",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962128-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_bestsv_lak_425ml_1218_1",
            "price": "167.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/996_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ бесцв.лак 425мл(1218-1)",
            "description": "Отличается экономностью в использованье и нанесении. Хорошо подходит для декоративно-защитных покрытий, помогает им становиться яркими и гладкими. Для того чтобы краска максимально хорошо покрыла материал, надо нанести пару слоев. Держать баллончик следует на расстояние до 25 см, чтобы краска равномерно попадала на поверхность. Нужный цвет можно купить по лучшей цене в магазине возле Артека."
        },
        {
            "@id": "64962129",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962129-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_zheltaya_425ml_1214_1",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/998_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ желтая 425мл(1214-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962130",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962130-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_zelenaya_425ml_1215_2",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/218/999_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ зеленая 425мл(1215-2)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962131",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962131-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_zeleny_list_425ml_1215_1",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/001_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ зелёный лист 425мл(1215-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962132",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962132-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_zolotaya_425ml_1220_1",
            "price": "229.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/003_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ золотая 425мл(1220-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962133",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962133-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_nefritovaya_zelenaya_425ml_121",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/005_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ нефритовая-зелёная 425мл(121",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962134",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962134-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_serebristo_seraya_425ml_1216",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/007_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ серебристо-серая 425мл(1216-",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962135",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962135-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_sinyaya_425ml_1212_1",
            "price": "167.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/008_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ синяя 425мл(1212-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962136",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962136-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_tem_seraya_425ml_1216_1",
            "price": "167.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/009_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ тем.серая 425мл(1216-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962137",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962137-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_serebristaya_425ml_1216_4",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/010_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ серебристая 425мл(1216-4)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962138",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962138-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_temno_zelenaya_425ml_1216_1",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/011_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ тёмно-зелёная 425мл(1216-1)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962139",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962139-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_chernaya_425ml_1211_2",
            "price": "167.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/012_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ черная 425мл(1211-2)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962140",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962140-kraska_aerozolnaya_empils_dlya_vn_i_nar_rabot_yarko_sinyaya_425ml_1212_4",
            "price": "176.0",
            "currencyId": "RUR",
            "categoryId": "10462",
            "picture": "http://st2.stpulscen.ru/images/product/111/219/013_original.png",
            "name": "Краска аэрозольная Empils для вн. и нар. работ Ярко-синяя 425мл(1212-4)",
            "description": "До 3 кв.метров поверхности. Сохнет за 10 минут."
        },
        {
            "@id": "64962209",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962209-kraska_emal_empils_dlya_razmetki_dorog_poliakr_belaya_s_25kg",
            "price": "4137.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/178/161_original.png",
            "name": "Краска Эмаль \"EMPILS\" для разметки дорог полиакр. белая С 25кг",
            "description": "Краска от производителя широко применяется для нанесения горизонтальных дорожных разметок на проезжей части, а также на площадках и территориях автозаправочных станций. Создает надежное покрытие на асфальте и бетоне, которое хранится долгое время. Можно купить со скидкой."
        },
        {
            "@id": "64962210",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962210-kraska_emal_empils_dlya_razmetki_dorog_poliakr_zheltaya_s_25kg",
            "price": "4505.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/178/202_original.png",
            "name": "Краска Эмаль \"EMPILS\" для разметки дорог полиакр. желтая С 25кг",
            "description": "Дорожная краска. Для нанесения разметки."
        },
        {
            "@id": "64962266",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962266-kraska_emal_pf_115_prostokrasheno_belaya_1_9l",
            "price": "274.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/173/008_original.jpg",
            "name": "Краска Эмаль ПФ-115 \"ПРОСТОКРАШЕНО\" белая 1,9л",
            "description": "Бюджетный вариант окраски любых поверхностей."
        },
        {
            "@id": "64962267",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962267-kraska_emal_pf_115_prostokrasheno_belaya_0_9l",
            "price": "135.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/173/221_original.jpg",
            "name": "Краска Эмаль ПФ-115 \"ПРОСТОКРАШЕНО\" белая 0,9л",
            "description": "Краска быстро и равномерно покрывает назначенную поверхность, глубоко проникая внутрь. Не выцветает под действием лучей солнца и высоких температур. В итоге глубокий цвет обеспечен надолго, а влагостойкие свойства будут препятствовать возникновению грибка. Лучшая цена на краску привлекает многих клиентов. Отовариться можно в строймагазинах Ялты, Гурзуфы."
        },
        {
            "@id": "64962268",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962268-kraska_emal_pf_115_prostokrasheno_seraya_0_9l",
            "price": "128.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/173/265_original.jpg",
            "name": "Краска Эмаль ПФ-115 \"ПРОСТОКРАШЕНО\" серая 0,9л",
            "description": "Бюджетный вариант окраски любых поверхностей."
        },
        {
            "@id": "64962269",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962269-kraska_emal_pf_115_prostokrasheno_seraya_1_9l",
            "price": "264.0",
            "currencyId": "RUR",
            "categoryId": "10681",
            "picture": "http://st2.stpulscen.ru/images/product/111/173/323_original.jpg",
            "name": "Краска Эмаль ПФ-115 \"ПРОСТОКРАШЕНО\" серая 1,9л",
            "description": "Бюджетный вариант окраски любых поверхностей."
        },
        {
            "@id": "64962418",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962418-xilol_0_5l_novbytkhim",
            "price": "92.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st17.stpulscen.ru/images/product/110/774/567_original.jpg",
            "name": "Ксилол 0,5л НовБытХим",
            "description": "Удалитель старых эмалей. Наиболее популярный у строителей, потому что не требует применения щеток и соскабливателей - старая эмаль отслаивается легко и легко удаляется."
        },
        {
            "@id": "64962485",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962485-lampa_kll_20w_2700_k_ye_27_spiral",
            "price": "164.0",
            "currencyId": "RUR",
            "categoryId": "116397",
            "picture": "http://st14.stpulscen.ru/images/product/113/403/825_original.png",
            "name": "Лампа КЛЛ 20W 2700 К Е-27 спираль",
            "description": "Распределительные коробки используют в слаботочных и силовых сетях. Установка труд через специальные сальники обеспечивают хорошую изоляцию проводки. Коробка легко монтируется с помощью специальных креплений. Есть в наличии в магазинах Ялты.   ."
        },
        {
            "@id": "64962504",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962504-lenta_bitumnaya_dlya_krovli_tytan_professional_rs_tape_10sm_kh10m_alyum",
            "price": "962.0",
            "currencyId": "RUR",
            "categoryId": "135794",
            "picture": "http://st2.stpulscen.ru/images/product/111/165/268_original.jpg",
            "name": "Лента битумная для кровли TYTAN Professional RS TAPE 10см х10м алюм.",
            "description": "Двуслойная алюминиево-битумная изоляция для любых кровельных стыков и соединений."
        },
        {
            "@id": "64962578",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962578-lobzik_interskol_mp_100e",
            "price": "4478.0",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик ИНТЕРСКОЛ МП-100Э",
            "description": "Лобзик имеет мощный двигатель, редуктор с металлическим корпусом, а замок крепления пилки – бесключевой. Можно работать на протяжение длительного периода благодаря четырем уровням подкачки. Продается в магазинах Гурзуфа и Ялты со скидками."
        },
        {
            "@id": "64962579",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962579-lobzik_elektricheski_profi_energomash_700vt",
            "price": "5359.0",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический профи Энергомаш 700Вт",
            "description": "Лобзиком от производителя легко можно совершать фигурную и прямую распилку дерева, пластика, металла. Благодаря лазерному указатель линии будут идеальные и точные. Пилка имеет два плоскости и меняется быстро и легко. Работает под углом наклона до 45 градусов. Предлагаем купить по лучшей цене."
        },
        {
            "@id": "64962691",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962691-mixer_professionalny_1500_vt_energomash",
            "price": "11090.0",
            "currencyId": "RUR",
            "categoryId": "172491",
            "name": "Миксер профессиональный, 1500 ВТ Энергомаш",
            "description": "Надежный лобзик не только быстро режет, но и имеет функцию пылесоса, которая автоматически позволяет держать рабочую поверхность в чистоте. Возможность отклонения опорной плиты позволяет работать под углом. Лобзики от производителя есть в наших магазинах в Ялте."
        },
        {
            "@id": "64962738",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962738-nabor_sibrtekh_shpateli_40_60_80_mm_belaya_rezinaya_3sht_1_200",
            "price": "43.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Набор \"СИБРТЕХ\" шпатели, 40-60-80 мм, белая резиная, -3шт- (1/200",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64962749",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962749-nabor_shpateley_3_sht_zelenyye_usp_06881",
            "price": "43.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Набор шпателей 3 шт. зеленые \"USP\"(06881)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64962750",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962750-nabor_shpateley_3_sht_chernyye_usp_06880",
            "price": "40.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Набор шпателей 3 шт. чёрные \"USP\"(06880)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64962982",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962982-pena_montazhnaya_profpur_mega_prof_870ml",
            "price": "323.0",
            "currencyId": "RUR",
            "categoryId": "135842",
            "picture": "http://st17.stpulscen.ru/images/product/110/775/186_original.jpeg",
            "name": "Пена монтажная \"PROFPUR MEGA\" проф., 870мл",
            "description": "Жёлтого цвета. Наиболее популярная профессиональная пена."
        },
        {
            "@id": "64962992",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962992-pena_poliuretanovaya_montazhnaya_professionalnaya_rush_power_flex",
            "price": "303.0",
            "currencyId": "RUR",
            "categoryId": "135842",
            "picture": "http://st17.stpulscen.ru/images/product/110/775/416_original.jpg",
            "name": "Пена полиуретановая монтажная профессиональная \"Rush Power Flex\"",
            "description": "Жёлтого цвета. Работы рекомендуется проводить при температуре от –10°С до +35°С и относительной влажности воздуха не менее 50%. Для получения максимального объема выхода и оптимальных физико-механических показателей пены перед использованием выдержать баллон при температуре от +18°С до +20°С не менее 10 часов. Для аккуратного выполнения работ рекомендуется закрыть пленкой прилегающие поверхности. Пену наносить на предварительно очищенные от пыли, грязи, жира, льда и инея поверхности. Рабочие поверхности перед нанесением пены увлажнить при температуре окружающей среды выше 0°С. Рабочее положение баллона — ДНОМ ВВЕРХ. Выход пены регулировать с помощью винта пистолета. В процессе работы периодически встряхивать баллон. После нанесения увлажнить пену водой с помощью распылителя при температуре окружающей среды выше 0°С. Избыток пены после полного затвердевания срезать ножом. Незатвердевшую пену удалить «Очистителем монтажной пены FOAM&GUN CLEANER» KUDO®. Для отвержденной пены использовать «Удалитель застывшей монтажной пены FOAM REMOVER» KUDO®. После полной полимеризации (24–48 часов), затвердевшую пену можно резать, штукатурить, окрашивать. Беречь от воздействия УФ-лучей и атмосферных осадков."
        },
        {
            "@id": "64962993",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962993-pena_poliuretanovaya_montazhnaya_professionalnaya_rush_power_flex",
            "price": "325.0",
            "currencyId": "RUR",
            "categoryId": "135842",
            "picture": "http://st17.stpulscen.ru/images/product/110/776/576_original.jpg",
            "name": "Пена полиуретановая монтажная профессиональная \"Rush Power Flex\"",
            "description": "Жёлтого цвета. Работы рекомендуется проводить при температуре от –10°С до +35°С и относительной влажности воздуха не менее 50%. Для получения максимального объема выхода и оптимальных физико-механических показателей пены перед использованием выдержать баллон при температуре от +18°С до +20°С не менее 10 часов. Для аккуратного выполнения работ рекомендуется закрыть пленкой прилегающие поверхности. Пену наносить на предварительно очищенные от пыли, грязи, жира, льда и инея поверхности. Рабочие поверхности перед нанесением пены увлажнить при температуре окружающей среды выше 0°С. Рабочее положение баллона — ДНОМ ВВЕРХ. Выход пены регулировать с помощью винта пистолета. В процессе работы периодически встряхивать баллон. После нанесения увлажнить пену водой с помощью распылителя при температуре окружающей среды выше 0°С. Избыток пены после полного затвердевания срезать ножом. Незатвердевшую пену удалить «Очистителем монтажной пены FOAM&GUN CLEANER» KUDO®. Для отвержденной пены использовать «Удалитель застывшей монтажной пены FOAM REMOVER» KUDO®. После полной полимеризации (24–48 часов), затвердевшую пену можно резать, штукатурить, окрашивать. Беречь от воздействия УФ-лучей и атмосферных осадков."
        },
        {
            "@id": "64962994",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64962994-pena_poliuretanovaya_montazhnaya_professionalnaya_hauser_65_910g",
            "price": "293.0",
            "currencyId": "RUR",
            "categoryId": "135842",
            "picture": "http://st17.stpulscen.ru/images/product/110/777/741_original.jpg",
            "name": "Пена полиуретановая монтажная профессиональная HAUSER 65, 910г",
            "description": "Жёлтого цвета."
        },
        {
            "@id": "64963000",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963000-pena_poliuretanovaya_montazhnaya_professionalnaya_tytan_professional_65_uni_75",
            "price": "319.0",
            "currencyId": "RUR",
            "categoryId": "135842",
            "picture": "http://st17.stpulscen.ru/images/product/110/778/045_original.jpg",
            "name": "Пена полиуретановая монтажная профессиональная TYTAN Professional 65 UNI 75",
            "description": "Жёлтого цвета. Производительность: до 65 л (при темп.+20°C) Звукоизоляция: до 61 dB*** Время предварительной обработки: до 40 мин. (при темп. +20°C) Температура применения: от -20°C до +30°C  Температура баллона: от +5°C до +30°C Водопоглощение (после 24 ч.): ≤ 1,5 % Класс огнестойкости: F / B3 (EN 13 501 / DIN 4102-1) Срок годности: 12 месяцев"
        },
        {
            "@id": "64963003",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963003-penoplast_extrudirovanny_ravaterm_xps_standart_1185_585_30_mm",
            "price": "169.0",
            "currencyId": "RUR",
            "categoryId": "101258",
            "picture": "http://st2.stpulscen.ru/images/product/111/084/130_original.jpg",
            "name": "Пенопласт экструдированный \"Ravaterm\" XPS STANDART 1185*585*30 мм",
            "description": "Прочный пенопласт незаменим для обшивки фасадов."
        },
        {
            "@id": "64963004",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963004-penoplast_extrudirovanny_ravaterm_xps_standart_1185_585_40_mm",
            "price": "175.0",
            "currencyId": "RUR",
            "categoryId": "101258",
            "picture": "http://st2.stpulscen.ru/images/product/111/084/133_original.jpg",
            "name": "Пенопласт экструдированный \"Ravaterm\" XPS STANDART 1185*585*40 мм",
            "description": "Прочный пенопласт незаменим для обшивки фасадов."
        },
        {
            "@id": "64963005",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963005-penoplast_extrudirovanny_ravaterm_xps_standart_1185_585_50_mm",
            "price": "213.0",
            "currencyId": "RUR",
            "categoryId": "101258",
            "picture": "http://st2.stpulscen.ru/images/product/111/084/134_original.jpg",
            "name": "Пенопласт экструдированный \"Ravaterm\" XPS STANDART 1185*585*50 мм",
            "description": "Прочный пенопласт незаменим для обшивки фасадов."
        },
        {
            "@id": "64963006",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963006-penoplast_extrudirovanny_ravaterm_xps_standart_1200_600_20_mm",
            "price": "91.0",
            "currencyId": "RUR",
            "categoryId": "101258",
            "picture": "http://st2.stpulscen.ru/images/product/111/084/135_original.jpg",
            "name": "Пенопласт экструдированный \"Ravaterm\" XPS STANDART 1200*600*20 мм",
            "description": "Прочный пенопласт незаменим для обшивки фасадов."
        },
        {
            "@id": "64963016",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963016-perforator_elitech_p1032rem_1050vt_3_65kg_3_4dzh_sds",
            "price": "7885.0",
            "currencyId": "RUR",
            "categoryId": "114477",
            "name": "Перфоратор ELITECH П1032РЭМ 1050Вт/3,65кг/3,4Дж/SDS+",
            "description": "Перфоратор имеет три рабочие режима – сверление ударное, обычное сверление и долбление. Может сверлить буры в бетоне диаметром до 3 сантиметров. Компактный и удобен в использованье. В наличии перфораторы в магазине рядом с Ришелье Шато или возле Артека."
        },
        {
            "@id": "64963019",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963019-perforator_energomash_1000vt",
            "price": "7611.0",
            "currencyId": "RUR",
            "categoryId": "114477",
            "name": "Перфоратор Энергомаш 1000Вт",
            "description": "Перфоратор имеет три рабочих режима, а также режим поворота бура. На рукоятке есть лампочка, с которой удобно работать в темном помещенье. Идет в комплекте с кейсом, в котором удобно хранить инструмент. Среди других товаров есть в наличии. Высокие скидки постоянным клиентам."
        },
        {
            "@id": "64963020",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963020-perforator_energomash_1050vt",
            "price": "7805.0",
            "currencyId": "RUR",
            "categoryId": "114477",
            "name": "Перфоратор Энергомаш 1050Вт",
            "description": "Мощный инструмент, который сверлит все твердые материалы. Пылезащитный колпачок препятствует попаданию пыли. Вибрация существенно снижается за счет антивибрационной задней ручки. А передняя рукоятка поворачивается на 360 градусов. Продается в магазинах Гурзуфа и Ялты."
        },
        {
            "@id": "64963039",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963039-pesok_kvartsevy_fraktsiya_0_01_0_63mm",
            "price": "5000.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st2.stpulscen.ru/images/product/110/975/492_original.jpg",
            "name": "Песок кварцевый сухой СТАВРОПОЛЬСКИЙ, фр.0,01-0,63мм",
            "description": "Кварцевый песок - самый используемый материал из категории \"сыпучие строительные материалы\".  Название этой категории описывает, кроме песка, ещё гравий, цемент, керамзит, щебень и другие материалы, отпускаемые обычно насыпью или в мешках. Кварцевый песок - это тот самый материал, из которого изготавливается стекло. Всем известны качества стекла — высочайшая стойкость практически к любым воздействиям. Эти качества взяты стеклом от своего материала — кварцевого песка. Незаменим для цементных растворов. Наша компания открывает производство кварцевого песка для строительства в Крыму, поэтому лучшая цена на кварцевый песок в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество кварцевого песка, который всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64963040",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963040-pesok_morskoy",
            "price": "100.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st2.stpulscen.ru/images/product/110/976/000_original.jpg",
            "name": "Песок морской 40кг мешок",
            "description": "Для большинства растворов, бетонов и других смесей используется песок. Песок в строительстве используется различных фракций. 1). В строительстве чаще всего бытовом применяется мелкозернистый, среднезернистый и крупнозернистый речной песок. Данный вид песка используется также на детских площадках россыпью или в песочнице. 2). На территории Российской Федерации, в том числе Республике Крым для промышленного строительства в основном используется песок крупной фракции (морской песок).   Место и способ добычи, как и основные параметры песков, должны соответствовать ГОСТ 8736-93.   Очистка морского песка выполняется после его добычи и перед производством различных материалов. В связи с этим, морской песок - песок высокого класса. Данный вид песка, благодаря своим свойствам, используется повсеместно. Область применения огромна. На его основе изготавливают: 1) различные строительные смеси (бетон, штукатурка и т.д.); 2) дренажные системы; 3) затирки, заполнители, некоторые красители;   Также морской песок применим и для производства колец для колодцев, и для основы дорожных покрытий, и для декоративных целей.   Наша Компания имеет возможность добычи и поставки как одного, так и другого вида песка. У нас большой опыт комплексного снабжения объектов капитального строительства. В наличии имеются паспорта и сертификаты на весь предоставленный товар. Возможен как наличный, так и безналичный расчет. Мы работаем с НДС. У нас Вы можете получить скидки, которые Вас несомненно порадуют."
        },
        {
            "@id": "64963041",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963041-pesok_rechnoy_40_kg_meshok",
            "price": "100.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st2.stpulscen.ru/images/product/110/976/122_original.jpg",
            "name": "Песок речной 40 кг мешок",
            "description": "Для большинства растворов, бетонов и других смесей используется песок. Песок в строительстве используется различных фракций. 1). В строительстве чаще всего бытовом применяется мелкозернистый, среднезернистый и крупнозернистый речной песок. Данный вид песка используется также на детских площадках россыпью или в песочнице. 2). На территории Российской Федерации, в том числе Республике Крым для промышленного строительства в основном используется песок крупной фракции (морской песок).   Место и способ добычи должны соответствовать ГОСТ 8736-93.   Речной песок имеет ряд преимуществ: 1) отличная влагонепроницаемость; 2) обладает хорошей шумоизоляцией; 3) не подвергается воздействию микроорганизмов и грибков; 4) безвреден.   Применяется при: 1) производстве материалов для строительства и отделки, таких как: бетон, кирпич, бордюры, сухие смеси и т.д.; 2) изготовлении цементных стяжек и штукатурки; 3) укладке дорожных покрытий.   Наша Компания имеет возможность добычи и поставки как одного, так и другого вида песка. У нас большой опыт комплексного снабжения объектов капитального строительства. В наличии имеются паспорта и сертификаты на весь предоставленный товар. Возможен как наличный, так и безналичный расчет. Мы работаем с НДС. У нас Вы можете получить скидки, которые Вас несомненно порадуют."
        },
        {
            "@id": "64963042",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963042-pesok_sm_fr_0_63_2_00_viko",
            "price": "8000.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st2.stpulscen.ru/images/product/110/975/815_original.jpg",
            "name": "Песок кварцевый сухой СТАВРОПОЛЬСКИЙ, фр. 0,63-1мм",
            "description": "Отгружаем как оптом в бигбэгах весом одна тонна, так и мешками. Кварцевый песок - самый используемый материал из категории \"сыпучие строительные материалы\".  Название этой категории описывает, кроме песка, ещё гравий, цемент, керамзит, щебень и другие материалы, отпускаемые обычно насыпью или в мешках. Кварцевый песок - это тот самый материал, из которого изготавливается стекло. Всем известны качества стекла — высочайшая стойкость практически к любым воздействиям. Эти качества взяты стеклом от своего материала — кварцевого песка. Незаменим для цементных растворов. Наша компания открывает производство кварцевого песка для строительства в Крыму, поэтому лучшая цена на кварцевый песок в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество кварцевого песка, который всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "64963064",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963064-pila_tsirkulyarnaya_energomash_profi_235mm_2000_vt",
            "price": "10192.0",
            "currencyId": "RUR",
            "categoryId": "10647",
            "name": "Пила циркулярная Энергомаш \"профи\" 235мм, 2000 ВТ",
            "description": "Циркулярная пила может использоваться не только в строительных работах, но и в быту. Легко регулируется глубина пропила. Для того чтобы работа с инструментом была надежной, установлена система блокировки шпинделя. Отводя автоматически стружку и пыль с поверхности, пила оберегает здоровье дыхательных органов. Лучшая цена от производителя."
        },
        {
            "@id": "64963217",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963217-plita_osb_3_12kh1250kh2500mm_mogilev",
            "price": "990.0",
            "currencyId": "RUR",
            "categoryId": "134946",
            "picture": "http://st17.stpulscen.ru/images/product/110/548/356_original.jpg",
            "name": "Плита OSB-3 12х1250х2500мм (Могилев)",
            "description": "Преимущества плит OSB: - повышенная прочность на изгиб и скалывание (в 2,5 раза выше, чем у ДСП), отличная упругость; - влагостойкость - низкий коэффициент набухания (около 10%) и огнестойкость; - незначительное содержание формальдегида А: 0,5 мг/л; - хорошие звукоизоляционные свойства; - лёгкость обработки и монтажа (плиты без труда сверлятся и режутся; - высокая плотность при небольшом весе; - не подвержены порче насекомыми; - коэффициент удержания крепежа выше, чем у ДСП на 25%; - отсутствие стандартных дефектов древесины (каверны, сучки); - невысокая цена OSB плит по сравнению с хвойной фанерой; - долговечность."
        },
        {
            "@id": "64963218",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963218-plita_osb_3_t_22mm_2_44kh1_22_kronospan",
            "price": "1680.0",
            "currencyId": "RUR",
            "categoryId": "134946",
            "picture": "http://st17.stpulscen.ru/images/product/110/548/407_original.jpg",
            "name": "Плита OSB-3 т.22мм 2,44х1,22 Kronospan",
            "description": "Преимущества плит OSB: - повышенная прочность на изгиб и скалывание (в 2,5 раза выше, чем у ДСП), отличная упругость; - влагостойкость - низкий коэффициент набухания (около 10%) и огнестойкость; - незначительное содержание формальдегида А: 0,5 мг/л; - хорошие звукоизоляционные свойства; - лёгкость обработки и монтажа (плиты без труда сверлятся и режутся; - высокая плотность при небольшом весе; - не подвержены порче насекомыми; - коэффициент удержания крепежа выше, чем у ДСП на 25%; - отсутствие стандартных дефектов древесины (каверны, сучки); - невысокая цена OSB плит по сравнению с хвойной фанерой; - долговечность."
        },
        {
            "@id": "64963219",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963219-plita_osb_3_t_9mm_2_44kh1_22_kronospan",
            "price": "800.0",
            "currencyId": "RUR",
            "categoryId": "134946",
            "picture": "http://st17.stpulscen.ru/images/product/110/548/430_original.jpg",
            "name": "Плита OSB-3 т.9мм 2,44х1,22 Kronospan",
            "description": "Преимущества плит OSB: - повышенная прочность на изгиб и скалывание (в 2,5 раза выше, чем у ДСП), отличная упругость; - влагостойкость - низкий коэффициент набухания (около 10%) и огнестойкость; - незначительное содержание формальдегида А: 0,5 мг/л; - хорошие звукоизоляционные свойства; - лёгкость обработки и монтажа (плиты без труда сверлятся и режутся; - высокая плотность при небольшом весе; - не подвержены порче насекомыми; - коэффициент удержания крепежа выше, чем у ДСП на 25%; - отсутствие стандартных дефектов древесины (каверны, сучки); - невысокая цена OSB плит по сравнению с хвойной фанерой; - долговечность."
        },
        {
            "@id": "64963220",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963220-plita_osb_3_9_1250_2500",
            "price": "891.0",
            "currencyId": "RUR",
            "categoryId": "134946",
            "picture": "http://st17.stpulscen.ru/images/product/110/548/435_original.jpg",
            "name": "Плита OSB-3 9*1250*2500",
            "description": "Преимущества плит OSB: - повышенная прочность на изгиб и скалывание (в 2,5 раза выше, чем у ДСП), отличная упругость; - влагостойкость - низкий коэффициент набухания (около 10%) и огнестойкость; - незначительное содержание формальдегида А: 0,5 мг/л; - хорошие звукоизоляционные свойства; - лёгкость обработки и монтажа (плиты без труда сверлятся и режутся; - высокая плотность при небольшом весе; - не подвержены порче насекомыми; - коэффициент удержания крепежа выше, чем у ДСП на 25%; - отсутствие стандартных дефектов древесины (каверны, сучки); - невысокая цена OSB плит по сравнению с хвойной фанерой; - долговечность."
        },
        {
            "@id": "64963290",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963290-plitkorez_matrix_600kh14mm_87625",
            "price": "1800.0",
            "currencyId": "RUR",
            "categoryId": "106787",
            "name": "Плиткорез \"Matrix\" 600х14мм(87625)",
            "description": "Плиткорез используется для придания нужной формы кафелю, керамической и другой плите. Имеет режущий элемент и специальный угольник угломер. Им можно вырезать круглые отверстия в плите. Продается в магазине возле Ришелье Шато или рядом с Артеком."
        },
        {
            "@id": "64963291",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963291-plitkorez_elektricheski_redverg_rd_184303_450vt_7_1kg_disk_180kh22_2mm_glub",
            "price": "5455.0",
            "currencyId": "RUR",
            "categoryId": "114790",
            "name": "Плиткорез электрический RedVerg RD-184303 450Вт/7, 1кг/диск 180х22,2мм/глуб",
            "description": "Поршневой электрический плиткорез легко режет плитку всех видов и форм. Наносит правильные и аккуратные отверстия. Отличается высокой производительностью, компактный и удобен в использованье. В наличии в магазинах Крыма – Ялты, Гурзуфа."
        },
        {
            "@id": "64963316",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963316-podves_profilny_p_175",
            "price": "10.0",
            "currencyId": "RUR",
            "categoryId": "63935",
            "picture": "http://st13.stpulscen.ru/images/product/112/702/371_original.jpg",
            "name": "Подвес профильный П-175",
            "description": "Это крепежный материал, который используют для крепления профилей к основанию. С помощью дюбелей или шурупов можно надежно зафиксировать нужный профиль. Учитывая расстояние между стеною и профилем надо подобрать подвес с отверстиями нужной глубины. Мы поможем вам совершить покупку в магазинах Ялты и Гурзуфа.."
        },
        {
            "@id": "64963317",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963317-podves_pryamoy_p_125",
            "price": "5.0",
            "currencyId": "RUR",
            "categoryId": "63935",
            "picture": "http://st13.stpulscen.ru/images/product/112/702/653_original.jpg",
            "name": "Подвес профиля прямой (П-крепление) П-125 (0,7 мм)",
            "description": "Профиль П-крепления применяется для крепления CD-профиля к основанию помещения. Отверстия разных глубин позволяют надежно прикрепить материалы между собой. Монтируют подвес с помощью шурупов или дюбелей. Продается по лучшей цене от производителя.."
        },
        {
            "@id": "64963333",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963333-pol_nalivnoy_bystrotverdeyushchi_universal_25_kg",
            "price": "413.0",
            "currencyId": "RUR",
            "categoryId": "62942",
            "picture": "http://st13.stpulscen.ru/images/product/112/773/737_original.jpg",
            "name": "Пол наливной \"UNIVERSAL\", 25 кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ: Перед тем, как наливать смесь для выравнивания, тщательно очистите старый пол от пыли и остатков краски или масел. Обязательно прогрунтуйте поверхность пола грунтовками SR-51 или SR-52. Дайте грунтовке высохнуть в течение 4 часов. Если основание пола неоднородное, из разных материалов, а также если выравнивающий слой не более 5 миллиметров, используйте армирующую сетку. КАК ПРИГОТОВИТЬ СМЕСЬ НАЛИВНОГО ПОЛА: Залейте в мешалку восемь литров чистой воды и на малых оборотах засыпайте 25 килограммов сухой смеси, добиваясь консистенции сметаны, без комков. Если используете штукатурную машину — работайте по её инструкции. МЫ РЕКОМЕНДУЕМ: Работать только при температуре воздуха выше +10°С. Разливайте смесь слоем от 2 до 150 миллиметров максимально равномерно. Если площадь пола больше двадцати квадратных метров, делайте деформационные швы. Не забывайте мыть инструмент и оборудование сразу после работы. Ходить по наливному полу можно примерно через 3-5 часов. Плитку можно укладывать через сутки. Линолеум можно укладывать через трое суток. Деревянные покрытия (паркет и т.п) укладывайте в соответствии с рекомендациями поставщика покрытия с обязательным контролем влажности основания."
        },
        {
            "@id": "64963358",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963358-portlandtsement_m_500_50_kg",
            "price": "380.0",
            "currencyId": "RUR",
            "categoryId": "116818",
            "picture": "http://st2.stpulscen.ru/images/product/110/970/161_original.jpg",
            "name": "Портландцемент М 500, 50 кг",
            "description": "Представляем вашему вниманию цемент М-500 50 килограмм. На текущий момент достаточно сложно представить строительство без использования цемента. Он используется практически при любых строительных работах.  Этот материал является тонкомолотым минеральным порошком, который имеет серо-зеленый цвет.  В его состав входит достаточно большой процент силикатов  кальция.  Бетоны и растворы, в состав которых входит этот компонент, способны придать строительным конструкциям особую прочность и долговечность."
        },
        {
            "@id": "64963359",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963359-portlandtsement_m_400_25kg",
            "price": "165.0",
            "currencyId": "RUR",
            "categoryId": "116818",
            "picture": "http://st2.stpulscen.ru/images/product/110/970/494_original.jpg",
            "name": "Портландцемент М-400 25кг",
            "description": "Упаковка по 25 кг - наиболее удобна для домашнего строительства."
        },
        {
            "@id": "64963404",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963404-prozhektor_led_100w",
            "price": "4044.0",
            "currencyId": "RUR",
            "categoryId": "137976",
            "picture": "http://st14.stpulscen.ru/images/product/113/465/515_original.jpg",
            "name": "Прожектор LED 100W",
            "description": "Этот прожектор являет собой альтернативный вариант рядом с галогенными прожекторами. Он имеет высокую степень защиты от влаги и пыли. Можно использовать внутри помещений, а можно на наружных объектах. Он гарантирует высокий световой поток с углом рассеивания света до 145 градусов. Покупайте прожектора со скидками и во время акций.   ."
        },
        {
            "@id": "64963462",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963462-profil_mayachkovy_pm_10_3m",
            "price": "26.0",
            "currencyId": "RUR",
            "categoryId": "63870",
            "picture": "http://st13.stpulscen.ru/images/product/112/780/269_original.jpg",
            "name": "Профиль маячковый (ПМ 10) 3м",
            "description": "Маяк штукатурный высотой 10 миллиметров, длиной 3 метра. Для проведения работ по оштукатуриванию поверхностей является практически незаменимым. Когда поверхность стены подготовлена под штукатурные работы, она помыта и очищена, с неё сняты большие выступы, можно устанавливать штукатурный маяк. Для проведения работ надо выбрать штукатурные маяки, которые будут монтироваться. Они бывают разные, по высоте салазки, а длина всех металлических направляющих – около трёх метров."
        },
        {
            "@id": "64963464",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963464-profil_mayachkovy_pm_6_3m",
            "price": "25.0",
            "currencyId": "RUR",
            "categoryId": "63870",
            "picture": "http://st13.stpulscen.ru/images/product/112/780/086_original.jpg",
            "name": "Профиль маячковый (ПМ 6) 3м",
            "description": "Маяк штукатурный высотой 6 миллиметров, длиной 3 метра. Для проведения работ по оштукатуриванию поверхностей является практически незаменимым. Когда поверхность стены подготовлена под штукатурные работы, она помыта и очищена, с неё сняты большие выступы, можно устанавливать штукатурный маяк. Для проведения работ надо выбрать штукатурный маяк, который будет монтироваться. Они бывают разные по высоте салазки, а длина всех металлических направляющих – около трёх метров."
        },
        {
            "@id": "64963470",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963470-profil_napravlyayushchi_potolochny_pnp_ud_28_27_0_4_3",
            "price": "60.0",
            "currencyId": "RUR",
            "categoryId": "10492",
            "picture": "http://st13.stpulscen.ru/images/product/112/702/840_original.jpg",
            "name": "Профиль направляющий потолочный ПНП (UD) 28*27 - 0,4мм - 3м",
            "description": "Используется при монтаже подвесных потолков и облицовке стен. Профиль мало весит и легко прикрепляется. Стойко переносит пожары и является экологически безопасным. Физическим лицам предлагаем наличный расчет за покупку в наших магазинах Крыма, а юридическим – безнал с НДС.."
        },
        {
            "@id": "64963473",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963473-profil_potolochny_pp_cd_60_27_0_4_3",
            "price": "100.0",
            "currencyId": "RUR",
            "categoryId": "10492",
            "picture": "http://st13.stpulscen.ru/images/product/112/703/177_original.jpg",
            "name": "Профиль потолочный ПП (CD) 60*27 - 0,4мм -3м",
            "description": "Потолочный профиль надежно крепит конструкцию к потолку, ведь он сделан из качественного металла, стойко переносит коррозию. Высокая прочность позволяет ему сохранять форму во время монтажа, не загибаться. Профиль с гарантией от производителя реализовывается в наших магазинах возле Артека и рядом с Ришелье Шато.."
        },
        {
            "@id": "64963517",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963517-rastvoritel_646_vershina_1_l_6_12",
            "price": "130.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/271/251_original.jpg",
            "name": "Растворитель 646 \"Вершина\" 1 л (6/12)",
            "description": "Универсальный растворитель, который разбавляет все типы нитроэмалей и акроэмалей, лаков, шпатлевки. Используется для того, чтобы обезжирить рабочую поверхность перед началом покраски или нанесенья лака. Есть в наличии нашего магазина в Ялте."
        },
        {
            "@id": "64963518",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963518-rastvoritel_646_dzerzhinsk_1_l_15",
            "price": "82.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/272/137_original.JPG",
            "name": "Растворитель 646 Дзержинск 1 л (15)",
            "description": "Высококачественный растворитель, в котором нет воды. Состоит из эфиров, кетонов, спиртов и аромо углеводов. Добавляется в краску небольшими дозами и тщательно перемешивается. Предлагаем купить товар по лучшей цене, а для учреждений – возможность расчета по безналу с НДС."
        },
        {
            "@id": "64963519",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963519-rastvoritel_646_khimprodukt_0_5l",
            "price": "51.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/272/215_original.jpg",
            "name": "Растворитель 646\"Химпродукт\" 0,5л",
            "description": "Подходит для разбавления лаков и красок. При этом он помогает сделать из них покрытие высокого качества для разных поверхностей. Краски быстро высыхают и долго хранят свой цвет. Есть в ассортименте магазина в Ялте, Гурзуфе. Для постоянных клиентов – накопительные скидки."
        },
        {
            "@id": "64963520",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963520-rastvoritel_646_khimprodukt_1_0l",
            "price": "107.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/272/275_original.jpg",
            "name": "Растворитель 646\"Химпродукт\" 1,0л",
            "description": "Следуйте иструкции и требованиям техники безопасности."
        },
        {
            "@id": "64963522",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963522-rastvoritel_647_0_5l_garus",
            "price": "51.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/272/719_original.png",
            "name": "Растворитель 647 0,5л ГаРус",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64963523",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963523-rastvoritel_647_1l_garus",
            "price": "85.0",
            "currencyId": "RUR",
            "categoryId": "10896",
            "picture": "http://st2.stpulscen.ru/images/product/111/272/760_original.png",
            "name": "Растворитель 647 1л ГаРус",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64963561",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963561-rozetka_1_ya_belaya_vera",
            "price": "202.0",
            "currencyId": "RUR",
            "categoryId": "115672",
            "picture": "http://st14.stpulscen.ru/images/product/113/466/020_original.jpg",
            "name": "Розетка 1-я белая VERA",
            "description": "Розетку удобно подключать, ведь ее клеммы расположены в одном ряду. Механизм сделан из прочного термостойкого пластика, а суппорт противостоит коррозии. Благодаря дополнительной скобе можно избежать расшатывания вилки. Розетки есть в наличии по лучшей цене.."
        },
        {
            "@id": "64963646",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963646-samorezy_gips_derevo_3_5_kh_16",
            "price": "188.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/838_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 16",
            "description": "Саморезы подходят для того, чтобы прикрепить гипсокартон к деревянным конструкциям. Имеют резьбу крупного шага, легко монтируются и выступают надежным крепителем. Продаются по оптовой цене в магазинах возле Артека и рядом с Ришелье Шато."
        },
        {
            "@id": "64963648",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963648-samorezy_gips_derevo_3_5_kh_19",
            "price": "206.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/925_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 19",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963649",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963649-samorezy_gips_derevo_3_5_kh_25",
            "price": "301.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/932_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 25",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963650",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963650-samorezy_gips_derevo_3_5_kh_32",
            "price": "350.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/933_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 32",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963651",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963651-samorezy_gips_derevo_3_5_kh_41",
            "price": "437.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/935_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 41",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963652",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963652-samorezy_gips_derevo_3_5_kh_35",
            "price": "392.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/937_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 35",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963653",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963653-samorezy_gips_derevo_3_5_kh_45",
            "price": "422.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/938_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 45",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963654",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963654-samorezy_gips_derevo_3_5_kh_51",
            "price": "638.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/939_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 51",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963655",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963655-samorezy_gips_derevo_3_5_kh_55",
            "price": "722.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/940_original.jpg",
            "name": "Саморезы гипс/дерево 3,5 х 55",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963656",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963656-samorezy_gips_derevo_3_8_kh_65",
            "price": "1084.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/941_original.jpg",
            "name": "Саморезы гипс/дерево 3,8 х 65",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963657",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963657-samorezy_gips_derevo_4_2_kh_75",
            "price": "958.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/942_original.jpg",
            "name": "Саморезы гипс/дерево 4,2 х 75",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963658",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963658-samorezy_gips_derevo_4_2_kh_70",
            "price": "1134.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/946_original.jpg",
            "name": "Саморезы гипс/дерево 4,2 х 70",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963659",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963659-samorezy_gips_derevo_4_2kh90_2000_250sht",
            "price": "1530.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/948_original.jpg",
            "name": "Саморезы гипс/дерево 4,2х90 (2000/250шт.)",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963660",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963660-samorezy_gips_derevo_4_8_kh_100",
            "price": "1641.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/949_original.jpg",
            "name": "Саморезы гипс/дерево 4,8 х 100",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963661",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963661-samorezy_gips_derevo_4_8_kh_120",
            "price": "3010.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/951_original.jpg",
            "name": "Саморезы гипс/дерево 4,8 х 120",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963663",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963663-samorezy_gips_derevo_5_kh_150",
            "price": "2963.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/953_original.jpg",
            "name": "Саморезы гипс/дерево 5 х 150",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963664",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963664-samorezy_gips_derevo_4_8_kh_130",
            "price": "2171.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/586/954_original.jpg",
            "name": "Саморезы гипс/дерево 4,8 х 130",
            "description": "Цена за 1000 штук."
        },
        {
            "@id": "64963665",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963665-samorezy_gips_metall_3_5_kh_16",
            "price": "269.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/585_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 16",
            "description": "Благодаря этим саморезам легко можно прикрутить гипсокартон к металлическим профилям. При этом не нужно предварительно сверлить отверстия. Частая резьба саморезов от производителя помогает надежно зафиксировать нужную конструкцию. Станьте покупателем нашего магазина и ощутите преимущества скидок и акций."
        },
        {
            "@id": "64963666",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963666-samorezy_gips_metall_3_5_kh_19",
            "price": "254.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/645_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 19",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963667",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963667-samorezy_gips_metall_3_5_kh_32",
            "price": "341.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/646_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 32",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963668",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963668-samorezy_gips_metall_3_5_kh_25",
            "price": "257.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/647_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 25",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963669",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963669-samorezy_gips_metall_3_5_kh_41",
            "price": "513.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/649_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 41",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963670",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963670-samorezy_gips_metall_3_5_kh_35",
            "price": "540.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/650_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 35",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963671",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963671-samorezy_gips_metall_3_5_kh_41_bely_tsink_6500sht",
            "price": "646.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/651_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 41 белый цинк 6500шт",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963672",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963672-samorezy_gips_metall_3_5_kh_55",
            "price": "612.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/652_original.jpg",
            "name": "Саморезы гипс/металл 3,5 х 55",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963673",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963673-samorezy_gips_metall_3_8_kh_65",
            "price": "650.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/653_original.jpg",
            "name": "Саморезы гипс/металл 3,8 х 65",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963674",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963674-samorezy_gips_metall_4_2_kh_70",
            "price": "1006.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/654_original.jpg",
            "name": "Саморезы гипс/металл 4,2 х 70",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963675",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963675-samorezy_gips_metall_4_2_kh_75",
            "price": "933.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/655_original.jpg",
            "name": "Саморезы гипс/металл 4,2 х 75",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963676",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963676-samorezy_gips_metall_4_2_kh_90",
            "price": "1840.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/656_original.jpg",
            "name": "Саморезы гипс/металл 4,2 х 90",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963677",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963677-samorezy_gips_metall_4_8_kh_100",
            "price": "1926.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/657_original.jpg",
            "name": "Саморезы гипс/металл 4,8 х 100",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963678",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963678-samorezy_gips_metall_4_8_kh_120",
            "price": "1676.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/659_original.jpg",
            "name": "Саморезы гипс/металл 4,8 х 120",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963679",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963679-samorezy_gips_metall_4_8_kh_130",
            "price": "1779.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/661_original.jpg",
            "name": "Саморезы гипс/металл 4,8 х 130",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64963680",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64963680-samorezy_gips_metall_4_8_kh_90",
            "price": "880.0",
            "currencyId": "RUR",
            "categoryId": "124987",
            "picture": "http://st2.stpulscen.ru/images/product/111/588/662_original.jpg",
            "name": "Саморезы гипс/металл 4,8 х 90",
            "description": "Цена указана за 1000 штук."
        },
        {
            "@id": "64964073",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964073-svetilnik_svetodiodny_universalny_lpu_eco_36t_6500k_prizma",
            "price": "1823.0",
            "currencyId": "RUR",
            "categoryId": "79096",
            "picture": "http://st14.stpulscen.ru/images/product/113/466/711_original.jpg",
            "name": "Светильник светодиодный универсальный LPU-ECO 36т 6500К \"Призма\"",
            "description": "Универсальный светильник отлично подойдет дл всех помещений, где нужен естественный и одновременно яркий свет. Используется в больницах, школах, в залах с выставками, торговых домах. Продается по лучшей цене в Ялте и Гурзуфе.."
        },
        {
            "@id": "64964113",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964113-setka_kladochnaya_50_50_1_2_f_4",
            "price": "370.0",
            "currencyId": "RUR",
            "categoryId": "10840",
            "picture": "http://st2.stpulscen.ru/images/product/110/964/897_original.jpg",
            "name": "Сетка кладочная 50*50 1*2 ф.4 (Сварная)",
            "description": "Производится путем точечной сварки мест пересечения проволоки."
        },
        {
            "@id": "64964135",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964135-setka_svarnaya_100_100_5_0_vr1_1kh2_s",
            "price": "222.0",
            "currencyId": "RUR",
            "categoryId": "10840",
            "picture": "http://st2.stpulscen.ru/images/product/110/961/578_original.jpg",
            "name": "Сетка сварная 100*100-5,0 Вр1 (1х2) С",
            "description": "Образуется из проволок, расположенных во взаимно перпендикулярных направлениях и сваренных в местах пересечения методом точечной сварки."
        },
        {
            "@id": "64964136",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964136-setka_svarnaya_100_100_5_0_vr1_1kh2_e",
            "price": "211.0",
            "currencyId": "RUR",
            "categoryId": "10840",
            "picture": "http://st2.stpulscen.ru/images/product/110/961/580_original.jpg",
            "name": "Сетка сварная 100*100-5,0 Вр1 (1х2) Э",
            "description": "Образуется из проволок, расположенных во взаимно перпендикулярных направлениях и сваренных в местах пересечения методом точечной сварки."
        },
        {
            "@id": "64964147",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964147-setka_svarnaya_50_50_4_0_vr1_1kh2_e",
            "price": "185.0",
            "currencyId": "RUR",
            "categoryId": "10840",
            "picture": "http://st2.stpulscen.ru/images/product/110/964/900_original.jpg",
            "name": "Сетка сварная 50*50-4 0 Вр1 (1х2) Э",
            "description": "Производится путем точесной сварки мест пересечения проволоки."
        },
        {
            "@id": "64964158",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964158-setka_fasadnaya_5mm_5mm_1m_50m_10_10_145_g_m_kv_zheltaya",
            "price": "1510.0",
            "currencyId": "RUR",
            "categoryId": "140129",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/741_original.jpg",
            "name": "Сетка фасадная 5мм*5мм(1м*50м+10-10%) 145 г/м.кв. желтая",
            "description": "Простой и удобный армирующий материал для оштукатуривания больших поверхностей."
        },
        {
            "@id": "64964159",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964159-setka_fasadnaya_5mm_5mm_1m_50m_10_10_145_g_m_kv_zheltaya_m2",
            "price": "31.0",
            "currencyId": "RUR",
            "categoryId": "140129",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/752_original.jpg",
            "name": "Сетка фасадная 5мм*5мм(1м*50м+10-10%) 145 г/м.кв. желтая м2",
            "description": "Простой и удобный армирующий материал для оштукатуривания больших поверхностей."
        },
        {
            "@id": "64964160",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964160-setka_fasadnaya_5mm_5mm_1m_50m_10_10_160_g_m_kv_belaya",
            "price": "1430.0",
            "currencyId": "RUR",
            "categoryId": "140129",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/654_original.jpg",
            "name": "Сетка фасадная 5мм*5мм(1м*50м+10-10%) 160 г/м.кв. белая",
            "description": "Простой и удобный армирующий материал для оштукатуривания больших поверхностей."
        },
        {
            "@id": "64964164",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964164-setka_fasadnaya_5mm_5mm_1m_50m_10_10_160_g_m_kv_sinyaya",
            "price": "1651.0",
            "currencyId": "RUR",
            "categoryId": "140129",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/675_original.jpg",
            "name": "Сетка фасадная 5мм*5мм(1м*50м+10-10%) 160 г/м.кв. синяя",
            "description": "Простой и удобный армирующий материал для оштукатуривания больших поверхностей."
        },
        {
            "@id": "64964166",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964166-setka_fasadnaya_5mm_5mm_1m_50m_10_10_160_g_m_kv_sinyaya_m2",
            "price": "37.0",
            "currencyId": "RUR",
            "categoryId": "140129",
            "picture": "http://st2.stpulscen.ru/images/product/111/085/677_original.jpg",
            "name": "Сетка фасадная 5мм*5мм(1м*50м+10-10%) 160 г/м.кв. синяя м2",
            "description": "Простой и удобный армирующий материал для оштукатуривания больших поверхностей."
        },
        {
            "@id": "64964270",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964270-smazka_aerozol_tytan_professional_tl_40",
            "price": "152.0",
            "currencyId": "RUR",
            "categoryId": "125172",
            "picture": "http://st2.stpulscen.ru/images/product/111/167/048_original.jpg",
            "name": "Смазка-аэрозоль TYTAN Professional TL-40",
            "description": "Для смазки поверхностей и одновременной их очистки. При нанесении на тефлоновую поверхность обеспечивает смазку и защиту. Подходит для чистки мебели, для моющихся элементов автомобилей."
        },
        {
            "@id": "64964276",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964276-smes_dlya_torkretirovaniya_sika_gunit_03_normal_25_kg",
            "price": "2000.0",
            "currencyId": "RUR",
            "categoryId": "92837",
            "picture": "http://st17.stpulscen.ru/images/product/110/705/247_original.png",
            "name": "Смесь для торкретирования Sika Gunit -03 Normal 25 кг",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964297",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964297-sredstvo_tytan_professional_fg_1_500ml_protiv_pleseni_i_gribka",
            "price": "251.0",
            "currencyId": "RUR",
            "categoryId": "116508",
            "picture": "http://st2.stpulscen.ru/images/product/111/163/064_original.jpg",
            "name": "Средство TYTAN Professional FG-1 500мл против плесени и грибка",
            "description": "Не содержит хлора."
        },
        {
            "@id": "64964299",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964299-sredstvo_tytan_professional_fg_2_500ml_protiv_pleseni_i_gribka_s_khlorom",
            "price": "221.0",
            "currencyId": "RUR",
            "categoryId": "116508",
            "picture": "http://st2.stpulscen.ru/images/product/111/165/034_original.jpeg",
            "name": "Средство TYTAN Professional FG-2 500мл против плесени и грибка(с хлором)",
            "description": "Содержит хлор."
        },
        {
            "@id": "64964370",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964370-styazhka_rovnitel_dlya_pola_universal_25_kg",
            "price": "321.0",
            "currencyId": "RUR",
            "categoryId": "62942",
            "picture": "http://st13.stpulscen.ru/images/product/112/775/645_original.jpg",
            "name": "Стяжка (ровнитель) для пола \"UNIVERSAL\", 25 кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТ:  Нужно обязательно очистить основание. Убедитесь, что оно прочное, плотное и сухое. Следы краски удалите. Трещины расширьте шпателем и очистите. Не позднее, чем за 4 часа до работ со стяжкой, прогрунтуйте основание, используя грунтовки SR-51 или SR-52. КАК ПРИГОТОВИТЬ СТЯЖКУ: Используйте механическую мешалку на малых оборотах. Залейте в неё пять литров воды, затем высыпайте сухой ровнитель, пока не получите однородную массу без комков. На 5 литров — 25 кг сухой смеси. Подождите около 10 минут и снова перемешайте. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте со стяжкой. Также не допускайте сквозняка. Готовый раствор вылейте на выравниваемый пол и распределите по всей поверхности резиновой планкой или другим специальным инструментом, в том числе механизированным. Через 24 часа можете ходить по стяжке. Спустя 7 дней можете укладывать напольное покрытие. Если нарушен климатический режим, сроки высыхания и схватывания могут быть больше."
        },
        {
            "@id": "64964462",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964462-tros_stal_v_pvkh_swr_m3_pvc_m4_din_3055_200m",
            "price": "2646.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/597/551_original.jpg",
            "name": "Трос сталь в ПВХ SWR M3 PVC M4 DIN 3055 (200м)",
            "description": "Стальной трос сделан из отдельных проволок, которые вместе создают прочный материал с небольшой изгибной жесткостью. Широко применяется в разных ситуациях. В нашем магазине возле Артека есть в наличии тросы всех размеров и метражей. Покупайте с выгодой для себя."
        },
        {
            "@id": "64964463",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964463-tros_stal_v_pvkh_swr_m4_pvc_m5_din_3055_200m",
            "price": "20.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/597/624_original.jpg",
            "name": "Трос сталь в ПВХ SWR M4 PVC M5 DIN 3055 (200м)",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964464",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964464-tros_stal_v_pvkh_swr_m6_pvc_m8_din_3055_100m",
            "price": "5152.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/597/629_original.jpg",
            "name": "Трос сталь в ПВХ SWR M6 PVC M8 DIN 3055 (100м)",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964466",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964466-tros_stal_kruglopryadny_swr_m_1_5_din_3055_200m",
            "price": "1149.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/598/145_original.png",
            "name": "Трос сталь круглопрядный SWR M 1.5 DIN 3055 (200м)",
            "description": "Круглопрядный трос применяется для подвесок и растяжек. Прочная оцинкованная проволоки пригодится во всех сферах, поскольку тросы имеют разные диаметры. Обращайтесь в магазины возле Артека или рядом с Ришелье Шато и мы поможем вам подобрать нужный трос."
        },
        {
            "@id": "64964467",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964467-tros_stal_kruglopryadny_swr_m_12_din_3055_100m",
            "price": "12722.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/598/165_original.png",
            "name": "Трос сталь круглопрядный SWR M 12 DIN 3055 (100м)",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964468",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964468-tros_stal_kruglopryadny_swr_m_3_din_3055_200m",
            "price": "1858.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/598/166_original.png",
            "name": "Трос сталь круглопрядный SWR M 3 DIN 3055 (200м)",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964470",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964470-tros_stal_kruglopryadny_swr_m_4_din_3055_200m",
            "price": "2926.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/598/167_original.png",
            "name": "Трос сталь круглопрядный SWR M 4 DIN 3055 (200м)",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964471",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964471-tros_stal_kruglopryadny_swr_m_6_din_3055_100m",
            "price": "4657.0",
            "currencyId": "RUR",
            "categoryId": "123686",
            "picture": "http://st2.stpulscen.ru/images/product/111/598/168_original.png",
            "name": "Трос сталь круглопрядный SWR M 6 DIN 3055 (100м)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964503",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964503-uayt_spirit_colorit_0_45_l_pl",
            "price": "51.0",
            "currencyId": "RUR",
            "categoryId": "271468",
            "picture": "http://st2.stpulscen.ru/images/product/111/275/628_original.png",
            "name": "Уайт-спирит \"Colorit\" 0,45 л пл.",
            "description": "Это фракция бензина с высококипящими свойствами. Используется для разбавки красок и обезжиривания поверхностей. Хранить следует в сухом и темном месте. Применять надо согласно инструкции. Покупайте и пользуйтесь нашей системой бонусов – скидки, акции, распродажи."
        },
        {
            "@id": "64964504",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964504-uayt_spirit_dzerzhinsk_1_l_15",
            "price": "68.0",
            "currencyId": "RUR",
            "categoryId": "271468",
            "picture": "http://st2.stpulscen.ru/images/product/111/273/501_original.png",
            "name": "Уайт-спирит Дзержинск 1 л (15)",
            "description": "Выступает основным растворителем для красок с масляной основой, алкидных, битумных и каучуковых мастик. Растворяет растительное масло, жир, серу, азот, кислород. Уайт спирит от производителя можно купить в магазине рядом с Ришелье Шато."
        },
        {
            "@id": "64964505",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964505-uayt_spirit_dzerzhinsk_5_l_pet_1_1",
            "price": "326.0",
            "currencyId": "RUR",
            "categoryId": "271468",
            "picture": "http://st2.stpulscen.ru/images/product/111/273/643_original.jpg",
            "name": "Уайт-спирит Дзержинск 5 л пэт. (1/1)",
            "description": "Соблюдайте технику безопасности при работе с растворителями."
        },
        {
            "@id": "64964581",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964581-ugolok_perforirovanny_arochny_22_22_3m_plastik",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "181572",
            "picture": "http://st13.stpulscen.ru/images/product/112/703/954_original.jpg",
            "name": "Уголок перфорированный арочный 22*22 3м пластик",
            "description": "Эти уголки имеют перфорацию, поэтому при установке в отверстия перфорации проникает шпаклёвка, которая была нанесена на угол стен, что и обеспечивает прочное сцепление профиля со стеной."
        },
        {
            "@id": "64964582",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964582-ugolok_perforirovanny_pvkh_3m_s_setkoy",
            "price": "75.0",
            "currencyId": "RUR",
            "categoryId": "181572",
            "picture": "http://st13.stpulscen.ru/images/product/112/703/959_original.jpg",
            "name": "Уголок перфорированный ПВХ 3м с сеткой",
            "description": "Эти уголки имеют перфорацию, поэтому при установке в отверстия перфорации проникает шпаклёвка, которая была нанесена на угол стен, что и обеспечивает прочное сцепление профиля со стеной."
        },
        {
            "@id": "64964583",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964583-ugolok_perforirovanny_plastikovy_s_setkoy_3m_bely",
            "price": "78.0",
            "currencyId": "RUR",
            "categoryId": "181572",
            "picture": "http://st13.stpulscen.ru/images/product/112/703/603_original.jpg",
            "name": "Уголок перфорированный пластиковый с сеткой 3 м",
            "description": "PRO — Зарегистрированный товарный знак. Основное направление — это разработка и внедрение в производство качественных профессиональных сухих строительных смесей, на цементной и гипсовой основе, изготовленных по передовым технологиям."
        },
        {
            "@id": "64964585",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964585-ugolok_perforirovanny_pryamoy_22_22_3m",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "181572",
            "picture": "http://st13.stpulscen.ru/images/product/112/704/618_original.jpeg",
            "name": "Уголок перфорированный прямой 22*22 3м пластик",
            "description": "."
        },
        {
            "@id": "64964587",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964587-ugolok_perforirovanny_shtukaturny_otsink_upsh",
            "price": "32.0",
            "currencyId": "RUR",
            "categoryId": "10492",
            "picture": "http://st13.stpulscen.ru/images/product/112/779/995_original.jpg",
            "name": "Уголок перфорированный штукатурный оцинк.(УПШ)",
            "description": "."
        },
        {
            "@id": "64964656",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964656-ushm_profi_sturm_230mm_2600vt_udlin_pov_rukoyat_antivibr",
            "price": "7502.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ \"профи\" STURM, 230мм, 2600Вт, удлин. пов. рукоять, антивибр.",
            "description": "Углошлифовальная машина, которая используется при разных строительных работах. Японские составные, в том числе мощный двигатель повышают эксплуатационный срок инструмента. Для того чтобы ее удобно было держать машина имеет дополнительную рукоятку. Можно купить по лучшей цене, приняв участие в распродаже магазина."
        },
        {
            "@id": "64964657",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964657-ushm_profi_energomash_125mm_1000vt",
            "price": "4075.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ \"профи\" Энергомаш, 125мм, 1000Вт",
            "description": "Углешлифовальная машина оснащена трехпозиционной ручкой и дополнительным комплектом щеток. Очень компактная и легкая, работает при мощности 1100 Вт, издавая в минуту 11 тысяч оборотов. Мы предлагаем по цене от производителя, а также со скидкой."
        },
        {
            "@id": "64964658",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964658-ushm_profi_energomash_125mm_1200vt",
            "price": "3438.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ \"профи\" Энергомаш, 125мм, 1200Вт",
            "description": []
        },
        {
            "@id": "64964659",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964659-ushm_elitech_mshu_1012_1000vt_2_6kg_125mm",
            "price": "3861.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ ELITECH МШУ 1012 1000Вт/2,6кг/125мм",
            "description": "Машину используют для шлифовки и зачистки металлических и каменных материалов. Используя нужного диаметра шлифовальный диск можно добиться результата. Углошлифовальные машины продаются в городах Гурзуфе и Ялте."
        },
        {
            "@id": "64964660",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964660-ushm_fit_ag_125_1150_1150vt_3000_11500ob_min",
            "price": "5075.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ FIT AG-125/1150 1150Вт, 3000-11500об/мин.",
            "description": "Этой моделью болгарки можно управлять одной рукой. Инструмент имеет небольшую длину, поэтому удобен для использования в узком помещенье и в неудобных условиях, например, под автомобилем. Мы предлагаем УШМ по невысокой цене, а также дарим скидки и участие в акциях магазина."
        },
        {
            "@id": "64964662",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964662-ushm_makita_ga5030_720_1_4_125mm",
            "price": "4799.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ Makita GA5030 720/1,4/125мм",
            "description": "Она отлично подходит в ситуациях, когда надо отшлифовать или очистить твердый материал. Благодаря покрытию специальным лаком якорь и полюса не засорятся мусором. Можно использовать в труднодоступных местах. Покупайте УШМ от производителя по лучшей цене."
        },
        {
            "@id": "64964663",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964663-ushm_makita_ga9020_2200_4_7_230",
            "price": "7739.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "УШМ Makita GA9020 2200/4,7/230",
            "description": []
        },
        {
            "@id": "64964747",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964747-tsep_svarnaya_dlinnozvennaya_otsink_llc_4_din_763",
            "price": "2062.0",
            "currencyId": "RUR",
            "categoryId": "124993",
            "picture": "http://st2.stpulscen.ru/images/product/111/590/785_original.jpg",
            "name": "Цепь сварная длиннозвенная оцинк LLC 4 DIN 763",
            "description": "Сварная цепь сделана из оцинкованной стали, поэтому она не ржавеет и не поддается механическому влиянию. Применяется в любых погодных условиях, помогая удобно и быстро перемещать грузы и транспортные средства. Купить можно в Крыму по лучшей цене."
        },
        {
            "@id": "64964749",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964749-tsep_svarnaya_dlinnozvennaya_otsink_llc_5_din_763",
            "price": "2750.0",
            "currencyId": "RUR",
            "categoryId": "124993",
            "picture": "http://st2.stpulscen.ru/images/product/111/590/812_original.jpg",
            "name": "Цепь сварная длиннозвенная оцинк LLC 5 DIN 763",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964750",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964750-tsep_svarnaya_korotkozvennaya_otsink_slc_4_din_766",
            "price": "2770.0",
            "currencyId": "RUR",
            "categoryId": "124993",
            "picture": "http://st2.stpulscen.ru/images/product/111/590/866_original.jpg",
            "name": "Цепь сварная короткозвенная оцинк SLC 4 DIN 766",
            "description": "Короткозвенная цепь – это крепежный элемент помогающий совершать монтаж разных конструкций. Но она используется не только на строительных площадках, но и в сельском хозяйстве. Из нее удобно делать оградки, крепления или подвески. Покупайте со скидкой в нашем магазине возле Артека."
        },
        {
            "@id": "64964752",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964752-tsep_svarnaya_korotkozvennaya_otsink_slc_5_din_766",
            "price": "3247.0",
            "currencyId": "RUR",
            "categoryId": "124993",
            "picture": "http://st2.stpulscen.ru/images/product/111/590/934_original.jpg",
            "name": "Цепь сварная короткозвенная оцинк SLC 5 DIN 766",
            "description": "Цена указана за бухту."
        },
        {
            "@id": "64964845",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964845-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_100mm_work_06510_1",
            "price": "51.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/408/528_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 100мм WORK (06510-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964846",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964846-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_150mm_work_06515_1",
            "price": "58.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/408/951_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 150мм WORK(06515-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964849",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964849-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_250mm_work_06525_1",
            "price": "95.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/106_original.jpeg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 250мм WORK(06525-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964850",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964850-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_200mm_work_06520_1",
            "price": "74.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/408/974_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 200мм WORK(06520-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964852",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964852-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_300mm_work_06530_1",
            "price": "123.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/124_original.jpeg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 300мм WORK(06530-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964853",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964853-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_40mm_work_06504_1",
            "price": "28.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/235_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 40мм WORK(06504-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964854",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964854-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_350mm_work_06535_1",
            "price": "132.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/127_original.jpeg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 350мм WORK(06535-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964856",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964856-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_450mm_work_06545_1",
            "price": "166.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/007_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 450мм WORK(06545-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964858",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964858-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_600mm_work_06560_1",
            "price": "243.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/269_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 600мм WORK(06560-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964860",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964860-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_60mm_work_06506_1",
            "price": "36.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/292_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 60мм WORK(06506-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964862",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964862-shpatel_iz_nerzh_stali_s_plastikovoy_ruchkoy_80mm_work_06508_1",
            "price": "45.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/293_original.jpg",
            "name": "Шпатель из нерж.стали с пластиковой ручкой 80мм WORK(06508-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964863",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964863-shpatel_iz_nerzhaveyushchey_stali_60_mm",
            "price": "34.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/294_original.jpg",
            "name": "Шпатель из нержавеющей стали 60 мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964865",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964865-shpatel_iz_nerzhaveyushchey_stali_80_mm",
            "price": "42.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/295_original.jpg",
            "name": "Шпатель из нержавеющей стали 80 мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964866",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964866-shpatel_metall_plast_ruchka_100mm_headman_683_045",
            "price": "61.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/332_original.jpg",
            "name": "Шпатель металл., пласт.ручка 100мм HEADMAN(683-045)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964868",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964868-shpatel_metall_plast_ruchka_200mm_headman_683_035",
            "price": "90.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/333_original.jpg",
            "name": "Шпатель металл., пласт.ручка 200мм HEADMAN(683-035)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964870",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964870-shpatel_nerzh_stal_prorezin_ruchka_1_0_25mm_usp_06681",
            "price": "124.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/367_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 1,0\"(25мм) USP(06681)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964872",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964872-shpatel_nerzh_stal_prorezin_ruchka_2_5_63mm_usp_06684",
            "price": "137.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/383_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 2,5\"(63мм) USP(06684)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964873",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964873-shpatel_nerzh_stal_prorezin_ruchka_2_0_50mm_usp_06683",
            "price": "131.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/384_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 2,0\"(50мм) USP(06683)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964876",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964876-shpatel_nerzh_stal_prorezin_ruchka_3_0_75mm_usp_06685",
            "price": "141.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/385_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 3,0\"(75мм) USP(06685)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964877",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964877-shpatel_nerzh_stal_prorezin_ruchka_4_0_100mm_usp_06686",
            "price": "187.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/386_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 4,0\"(100мм) USP(06686)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964879",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964879-shpatel_nerzh_stal_prorezin_ruchka_5_0_125mm_usp_06687",
            "price": "210.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/409/387_original.jpg",
            "name": "Шпатель нерж.сталь, прорезин.ручка 5,0\"(125мм) USP(06687)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964880",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964880-shpatel_nerzhaveyushchaya_stal_fasadny_150mm_dvukhkomponentnaya_ruchka_prof",
            "price": "311.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/569_original.jpg",
            "name": "Шпатель нержавеющая сталь фасадный 150мм, двухкомпонентная ручка \"ПРОФ",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964882",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964882-shpatel_nerzhaveyushchaya_stal_fasadny_250mm_dvukhkomponentnaya_ruchka_malyarka_3",
            "price": "352.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/599_original.jpg",
            "name": "Шпатель нержавеющая сталь фасадный 250мм, двухкомпонентная ручка МАЛЯРКА(3",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964883",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964883-shpatel_nerzhaveyushchaya_stal_fasadny_250mm_dvukhkomponentnaya_ruchka_prof",
            "price": "395.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/602_original.jpg",
            "name": "Шпатель нержавеющая сталь фасадный 250мм, двухкомпонентная ручка \"ПРОФ",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964886",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964886-shpatel_nerzhaveyushchaya_stal_fasadny_450mm_dvukhkomponentnaya_ruchka_317_0450",
            "price": "525.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/687_original.jpg",
            "name": "Шпатель нержавеющая сталь фасадный 450мм, двухкомпонентная ручка (317-0450",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964888",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964888-shpatel_nerzhaveyushchi_zubchaty_150_6mm_work_06616_1",
            "price": "61.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/824_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 150/6мм WORK(06616-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964889",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964889-shpatel_nerzhaveyushchi_zubchaty_150_8mm_work_06618_1",
            "price": "57.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/865_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 150/8мм WORK(06618-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964890",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964890-shpatel_nerzhaveyushchi_zubchaty_200_6mm_work_06626_1",
            "price": "78.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/868_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 200/6мм WORK(06626-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964891",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964891-shpatel_nerzhaveyushchi_zubchaty_200_6mm",
            "price": "73.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/870_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 200/6мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964892",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964892-shpatel_nerzhaveyushchi_zubchaty_200_8mm",
            "price": "137.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/871_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 200/8мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964893",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964893-shpatel_nerzhaveyushchi_zubchaty_200_8mm_work_06628_1",
            "price": "73.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/872_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 200/8мм WORK(06628-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964898",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964898-shpatel_nerzhaveyushchi_zubchaty_250_6mm",
            "price": "91.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/874_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 250/6мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964899",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964899-shpatel_nerzhaveyushchi_zubchaty_250_8mm_work_06638_1",
            "price": "91.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/875_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 250/8мм WORK(06638-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964901",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964901-shpatel_nerzhaveyushchi_zubchaty_250_6mm_work_06636_1",
            "price": "98.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/876_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 250/6мм WORK(06636-1)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964902",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964902-shpatel_nerzhaveyushchi_zubchaty_300mm8_8",
            "price": "106.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/422/877_original.jpg",
            "name": "Шпатель нержавеющий зубчатый 300мм8*8",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964904",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964904-shpatel_nerzhaveyushchi_malyarny_100mm",
            "price": "51.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 100мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964905",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964905-shpatel_nerzhaveyushchi_malyarny_100mm_torekh",
            "price": "47.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 100мм \"ТОРЕХ\"",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964908",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964908-shpatel_nerzhaveyushchi_malyarny_40mm_topex",
            "price": "26.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 40мм TOPEX",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964909",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964909-shpatel_nerzhaveyushchi_malyarny_125mm_topex",
            "price": "170.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 125мм TOPEX",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964911",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964911-shpatel_nerzhaveyushchi_malyarny_63mm",
            "price": "112.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 63мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964912",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964912-shpatel_nerzhaveyushchi_malyarny_50mm_topex",
            "price": "104.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 50мм TOPEX",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964913",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964913-shpatel_nerzhaveyushchi_malyarny_75mm",
            "price": "133.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий малярный 75мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964914",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964914-shpatel_nerzhaveyushchi_standart_150mm",
            "price": "54.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 150мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964915",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964915-shpatel_nerzhaveyushchi_standart_200mm",
            "price": "68.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 200мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964916",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964916-shpatel_nerzhaveyushchi_standart_250mm",
            "price": "89.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 250мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964917",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964917-shpatel_nerzhaveyushchi_standart_300mm",
            "price": "115.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 300мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964918",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964918-shpatel_nerzhaveyushchi_standart_350mm",
            "price": "123.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 350мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964921",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964921-shpatel_nerzhaveyushchi_standart_600mm",
            "price": "227.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 600мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964922",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964922-shpatel_nerzhaveyushchi_standart_450mm",
            "price": "154.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель нержавеющий стандарт 450мм",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964924",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964924-shpatel_nerzhaveyushchi_fasadny_350mm_profi_usp_06445",
            "price": "517.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/423/284_original.jpg",
            "name": "Шпатель нержавеющий фасадный 350мм Профи \"USP\"(06445)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964925",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964925-shpatel_nerzhaveyushchi_fasadny_400mm_profi_usp_06446",
            "price": "518.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/423/306_original.jpg",
            "name": "Шпатель нержавеющий фасадный 400мм Профи \"USP\"(06446)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964928",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964928-shpatel_nerzhaveyushchi_fasadny_450mm_profi_usp_06447",
            "price": "631.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/423/309_original.jpg",
            "name": "Шпатель нержавеющий фасадный 450мм Профи \"USP\"(06447)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964929",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964929-shpatel_nerzhaveyushchi_fasadny_600mm_profi_usp_06448",
            "price": "708.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "picture": "http://st2.stpulscen.ru/images/product/111/423/310_original.jpg",
            "name": "Шпатель нержавеющий фасадный 600мм Профи \"USP\"(06448)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964932",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964932-shpatel_pvkh_100mm_bely",
            "price": "23.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель ПВХ 100мм белый",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964933",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964933-shpatel_poverkhnostny_iz_plastmassy_nabor_5_8_10_12_sm_hobby_4sht",
            "price": "54.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель поверхностный из пластмассы (набор) 5/8/10/12 см,HOBBY 4шт",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964934",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964934-shpatel_prizhimnoy_oboyny_290mm_usp_06905",
            "price": "88.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель прижимной обойный 290мм USP(06905)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964936",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964936-shpatel_s_derevyannoy_ruchkoy_100mm_headman_683_016",
            "price": "30.0",
            "currencyId": "RUR",
            "categoryId": "113103",
            "name": "Шпатель с деревянной ручкой 100мм HEADMAN(683-016)",
            "description": "Все стройматериалы: сухие смеси, клеи, штукатурка, шпатлевка, краски, песок, кирпич и сотни других ждут Вас в нашем магазине \"Профсистемы-Крым\" по адресу: Гурзуф, Ялта, Крым. Ориентиры: возле Артека, рядом с Ришелье Шато. Для жителей Гурзуфа и Краснокаменки наше расположение уникально: рядом с домом, практически в шаговой доступности. Так как мы - производители сухих строительных смесей - у нас лучшие цены, от производителя. При покупках от 50000 руб - бесплатная доставка. Все стройматериалы и инструменты у нас всегда в наличии. Организациям предлагаем безнал с НДС. Уже при первой покупке Вы получите скидку 5%, а покупая постоянно, доведете ее до 15% - это уникальная скидка! Каждую неделю у нас или акция, или распродажа. Крупным застройщикам - специальное предложение! А кварцевый песок наиболее выгодно покупать только у нас: лучшего соотношения цена-качество Вы не найдете!"
        },
        {
            "@id": "64964989",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964989-shtukaturka_gipsovaya_start_mashinnogo_naneseniya_30kg",
            "price": "372.0",
            "currencyId": "RUR",
            "categoryId": "116760",
            "picture": "http://st13.stpulscen.ru/images/product/112/778/419_original.jpg",
            "name": "Штукатурка гипсовая \"PRO\" МН 30кг",
            "description": "Применяется при выравнивании как стен, так и потолков. В любых сухих помещениях. Финишное шпаклевание при этом не потребуется. Даже одного слоя гипсовой штукатурки достаточно для последующей отделки.   ПЕРЕД НАНЕСЕНИЕМ: Проверьте, достаточно ли прочное и плотное основание для штукатурки. Если есть бугры, счистите их, а отслоения удалите. Ямы и вмятины глубиной более пяти сантиметров заполните отдельно, перед выравниванием поверхности. При необходимости удалите пыль, грязь, жир, копоть, старую краску и прочие загрязнения. Если поверхность сильно впитывает, прогрунтуйте её грунтовкой SR-51, а бетон — SR-52. Через 1-4 часа на высохшую поверхность наносите штукатурную массу. КАК ПРИГОТОВИТЬ ШТУКАТУРКУ: Высыпайте сухую штукатурку в удобный для перемешивания сосуд, предварительно заполненный водой. На килограмм сухой штукатурки должно быть 600 миллилитров воды. Всыпайте порошок в воду, перемешивая и доводя до нужной консистенции. Комочки тут же разминайте. Если используете штукатурную машину, работайте по её инструкции. МЫ РЕКОМЕНДУЕМ: Если площадь покрытия большая, используйте специальные маяки — металлические планки. На углы, оконные и дверные откосы устанавливайте металлические или пластмассовые защитные перфорированные уголки или уголки с сеткой. Используйте штукатурную армирующую сетку там, где необходимо: в местах стыков, как однородных, так и разнородных материалов основания. Не работайте при температуре ниже плюс десяти градусов. Раствор набрызгивайте слоем одинаковой толщины — примерно сантиметр, но не меньше 5 миллиметров. Если собираетесь наносить несколько слоёв, то первый должен остаться шероховатым. Разравнивайте штукатурку правилом или гладилкой. Сразу после схватывания поверхность штукатурки слегка увлажните и затрите затиркой. Не забывайте сразу отмывать инструмент и оборудование!"
        },
        {
            "@id": "64964990",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64964990-shtukaturka_gipsovaya_start_ruchnogo_naneseniya_30kg",
            "price": "372.0",
            "currencyId": "RUR",
            "categoryId": "116760",
            "picture": "http://st13.stpulscen.ru/images/product/112/778/377_original.jpg",
            "name": "Штукатурка гипсовая \"Старт\"РН 30кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ Прежде, чем начинать штукатурить, нужно подготовить поверхность. Это важно, если Вас интересует качество результата. Требования к поверхности: сухая и прочная, чистая, без пыли, без отслоений. Если поверхность бетонная — тщательно очистите её от опалубочной смазки. Ели температура поверхности (и воздуха) ниже +5, работы не проводите. Части арматуры и другие металлические элементы покройте грунтом от коррозии. Если поверхность сильновпитывающая (кирпич, газобетон) — нанесите на неё предварительно грунтовку SR-51 или SR-52. Наоборот, очень плотные, гладкие и не впитывающие влагу поверхности обработайте грунтовкой «Бетон-контакт» ТМ PRO. Дождитесь высыхания грунтовки, следите, чтобы на поверхность грунта не попала пыль. Для предотвращения трещин в углах и местах стыка разнородных материалов используйте штукатурную сетку. На наружные углы, проёмы и откосы ставьте металлические или пластиковые уголки, лучше с сеткой.   ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ:   ЗАМЕС Сухую смесь высыпать в удобную для перемешивания ёмкость, предварительно наполненную холодной водой из расчёта 13,5 – 15 литров на 30 кг сухой смеси, одновременно перемешивая вручную или строительным миксером до получения однородной, не содержащей комков массы. После размешивания подождать примерно 3 минуты и снова перемешать. Никакие другие компоненты добавлять в смесь нельзя — это испортит раствор! МЫ РЕКОМЕНДУЕМ: Не работайте при высокой влажности воздуха (более 60%) и с сырыми поверхностями, при температурах ниже плюс пяти градусов и выше плюс тридцати. На стены наносите штукатурку слоем от 5 до 40 мм, (локально до 60мм), предварительно подготовив поверхность. На потолки — не более 20 мм. Разравнивайте смесь, используя h-образное правило. Как только раствор схватится, срежьте излишки смеси трапециевидным правилом и загладьте поверхность шпателем. Если вы наносите несколько слоёв, нижележащий слой «причешите» штукатурным гребнем и после его высыхания обработайте грунтовкой SR-51 или SR-52. Дождитесь высыхания грунтовки и нанесите второй слой. Обязательно вымойте инструменты и оборудование после работы, так как загрязнённые ёмкости и инструменты сокращают время использования растворной смеси. Защищайте высыхающий раствор от интенсивного высыхания: от солнца и сквозняков."
        },
        {
            "@id": "64965071",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/64965071-shcheben_5_25",
            "price": "1375.0",
            "currencyId": "RUR",
            "categoryId": "145463",
            "picture": "http://st2.stpulscen.ru/images/product/111/079/359_original.jpg",
            "name": "Щебень 5-25 в мeшках",
            "description": "Незаменим для цементных растворов."
        },
        {
            "@id": "66084512",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66084512-sr_19_shpaklevka_finishnaya_gipsovaya_25_kg",
            "price": "412.0",
            "currencyId": "RUR",
            "categoryId": "116755",
            "picture": "http://st13.stpulscen.ru/images/product/112/777/060_original.jpg",
            "name": "SR-19 Шпаклевка \"Финишная\" гипсовая, 25 кг",
            "description": "ПЕРЕД НАЧАЛОМ РАБОТЫ: Поверхность, на которую Вы будете наносить шпатлёвку, должна быть достаточно прочной, сухой и обязательно очищенной от всех загрязнений и пыли, старых красок и старой штукатурки. Мы рекомендуем предварительно выровнять поверхность, используя одну из штукатурок нашей торговой марки. Очень желательно прогрунтовывать поверхность основания грунтовками SR-51 или SR-52. КАК ЗАМЕСИТЬ РАСТВОР: Смешайте (затворите) сухую смесь с предварительно набранной в удобную для перемешивания ёмкость водой в соотношении примерно 0,56-0,6 литров воды на 1 килограмм сухой смеси, равномерно засыпая сухую смесь в воду, перемешивая вручную или механическим способом до консистенции сметаны. Затем раствор должен отстояться около 5 минут, после чего ещё раз тщательно перемешайте его. Используйте полученную смесь не дольше часа после замеса. МЫ РЕКОМЕНДУЕМ: Если слишком холодно (меньше плюс пяти) или слишком жарко (больше плюс тридцати) — не работайте со шпатлёвкой. Следите за толщиной слоя — он должен быть не тоньше 0,1 мм и не толще 5 мм. Наносите смесь шпателем или правилом. Новые слои наносите не ранее, чем через сутки. Высохший слой выравнивайте наждачной бумагой. Любая обработка (покраска, оклейка) шпатлёвки возможна не ранее суток после её нанесения. ОСТОРОЖНО! Если раствор попал в глаза, немедленно промойте глаза чистой водой. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "66084514",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66084514-sr_26_kley_20_kg",
            "price": "440.0",
            "currencyId": "RUR",
            "categoryId": "116755",
            "picture": "http://st16.stpulscen.ru/images/product/114/388/060_original.jpeg",
            "name": "SR-16 Шпатлевка для заделки швов гипсокартона, финиш , 30 кг",
            "description": "Эта шпатлёвка имеет гипсовую основу и обычно применяется в двух случаях: первый - для заделки швов и выравнивания обрабатываемых поверхностей, второй - при монтаже пазогребневых плит и для исправления различных дефектов (сколов, вмятин и т.п.) гипсокартонного листа или гипсоволокна. Наша компания открывает производство сухих смесей для строительства в Крыму, поэтому лучшая цена на сухие строительные смеси в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество смесей, которые всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "66084534",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66084534-apparat_svarochny_invertor_est_ig_200_220v_6kg_6_4mm_180a_keys",
            "price": "6612.0",
            "currencyId": "RUR",
            "categoryId": "164964",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/659_original.jpg",
            "name": "Аппарат сварочный инвертор EST IG-200 220В/6кг/,6-4мм 180А/кейс",
            "description": []
        },
        {
            "@id": "66085185",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66085185-drel_shurupovert_akk_gsr_1800_li_bosch_18_2_9_1_5a_keys",
            "price": "9478.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "name": "Дрель-шуруповёрт акк. GSR 1800-Li BOSCH 18/2.9/1.5а кейс",
            "description": "Дрель шуруповерт профи акк джи ес ер 1800 бош Дрель оснащена планетарным редуктором для вкручивания винтов и сверления на максимальных скоростях. Защита аккумулятора не позволяет ему перегреваться и разряжаться до предела. Весит меньше полутора килограмма, поэтому удобна в использованье. Есть в наличии с сезонной скидкой."
        },
        {
            "@id": "66086152",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086152-lampa_lyum_osram_t8_lumilux_l_36_840",
            "price": "153.0",
            "currencyId": "RUR",
            "categoryId": "115833",
            "picture": "http://st14.stpulscen.ru/images/product/113/404/072_original.jpg",
            "name": "Лампа люм. Osram T8 Lumilux L 36 / 840",
            "description": "Люминесцентная лампа отлично подходит для освещения растений и подсветки аквариумов. Она имеет специальный свет, который не вредит живым организмам. Большой выбор ламп в магазине возле Артека или рядом с Ришелье Шато. ."
        },
        {
            "@id": "66086183",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086183-lobzik_gst_8000_e_bosch_710_vt_500_3100",
            "price": "6442.0",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик GST 8000 E BOSCH 710 Вт/500-3100",
            "description": "Можно пилить любой материал, меняя пильное полотно без дополнительных инструментов. Направление реза имеет двойную фиксацию, поэтому можно профессионально делать как деликатные, так и грубые резы. Лучшая цена для наших покупателей от производителя.Можно пилить любой материал, меняя пильное полотно без дополнительных инструментов. Направление реза имеет двойную фиксацию, поэтому можно профессионально делать как деликатные, так и грубые резы. Лучшая цена для наших покупателей от производителя."
        },
        {
            "@id": "66086210",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086210-perforator_makita_hr2470_7820_2_6_2_7_sds_keys",
            "price": "9923.0",
            "currencyId": "RUR",
            "categoryId": "114477",
            "name": "Перфоратор Makita HR2470 7820/2.6/2.7 SDS+ кейс",
            "description": "Этим перфоратором вы можете сверлить, долбить и сверлить с ударом. Частота вращение регулируется электроникой. Не создает большой вибрации в включенном виде и легко используется. Предлагаем купить по лучшей цене перфоратор, а также со скидкой."
        },
        {
            "@id": "66086211",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086211-pesok_kvartsevy_0_63mm_meshok_25kg",
            "price": "9000.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st21.stpulscen.ru/images/product/118/452/928_original.jpg",
            "name": "Песок кварцевый сухой СТАВРОПОЛЬСКИЙ, фр. 1-2мм",
            "description": "Кварцевый песок - самый используемый материал из категории \"сыпучие строительные материалы\".  Название этой категории описывает, кроме песка, ещё гравий, цемент, керамзит, щебень и другие материалы, отпускаемые обычно насыпью или в мешках. Кварцевый песок - это тот самый материал, из которого изготавливается стекло. Всем известны качества стекла — высочайшая стойкость практически к любым воздействиям. Эти качества взяты стеклом от своего материала — кварцевого песка. Незаменим для цементных растворов. Наша компания открывает производство кварцевого песка для строительства в Крыму, поэтому лучшая цена на кварцевый песок в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество кварцевого песка, который всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "66086212",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086212-pila_diskovaya_hs7601_makita_1200_4_190_30",
            "price": "10314.0",
            "currencyId": "RUR",
            "categoryId": "108051",
            "name": "Пила дисковая HS7601 Makita 1200/4/190*30",
            "description": "Инструмент весит мало, поэтому владелец может маневрировать ею. Съемная насадка пылесоса очищает рабочую поверхность от стружки. Рукоятка имеет противоскользящее покрытие. Продается по лучшей цене, всегда в наличии."
        },
        {
            "@id": "66086213",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086213-pila_diskovoya_gks_190_bosch_1400_4_2_90mm",
            "price": "10314.0",
            "currencyId": "RUR",
            "categoryId": "108051",
            "name": "Пила дисковоя GKS 190 BOSCH 1400/4.2/90мм",
            "description": "Дисковая пила имеет одну скорость и функцию торможения двигателя. Вращает около 5500 оборотов в минуту. Вес пилы составляет 4,2 килограмма. Пилы в большом количестве есть в наших магазинах Ялты, а также Гурзуфа."
        },
        {
            "@id": "66086214",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086214-pila_tortsovochnaya_hammer_flex_stl800_800vt_5000ob_min_disk190_20mm_gl_prop",
            "price": "6075.0",
            "currencyId": "RUR",
            "categoryId": "173306",
            "name": "Пила торцовочная Hammer Flex STL800 (800Вт 5000об/мин диск190*20мм гл.проп",
            "description": "Торцовочной пилой можно распилить не только дерево, но и тонкий алюминий и сталь. Легкую пилу возможно без проблем переносить с одного места на другое. Чем прямее будет кут наклона, тем глубже можно сделать пропил. Наша цена – это лучшая цена с разными скидками и акциями."
        },
        {
            "@id": "66086220",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/66086220-provod_pvsbm_2_2_5_bely",
            "price": "64.0",
            "currencyId": "RUR",
            "categoryId": "142788",
            "picture": "http://st14.stpulscen.ru/images/product/113/464/909_original.jpeg",
            "name": "Провод ПВСбм 2*2,5 белый",
            "description": "Белый провод от производителя имеет диаметр 8,2 мм. Сделан с меди, изолирован ПВХ-пластикатом, из этого же материала сделана оболочка. Используется для проведения электричества на разных объектах. Для организаций предлагаем совершать покупки с помощью безналу с НДС.   ."
        },
        {
            "@id": "70298742",
            "@available": "false",
            "url": "http://www.orpro.ru/goods/70298742-pesok_kvartsevy_sukhoy_krymski_fr_0_01_0_63mm",
            "price": "3500.0",
            "currencyId": "RUR",
            "categoryId": "10781",
            "picture": "http://st21.stpulscen.ru/images/product/118/548/217_original.jpg",
            "name": "Песок кварцевый сухой КРЫМСКИЙ, фр. 0,01-0,63мм",
            "description": "Кварцевый песок - самый используемый материал из категории \"сыпучие строительные материалы\".  Название этой категории описывает, кроме песка, ещё гравий, цемент, керамзит, щебень и другие материалы, отпускаемые обычно насыпью или в мешках. Кварцевый песок - это тот самый материал, из которого изготавливается стекло. Всем известны качества стекла — высочайшая стойкость практически к любым воздействиям. Эти качества взяты стеклом от своего материала — кварцевого песка. Незаменим для цементных растворов. Наша компания открывает производство кварцевого песка для строительства в Крыму, поэтому лучшая цена на кварцевый песок в Крыму будет теперь только у нас, и, посетив наш магазин-склад в Гурзуфе, что возле Артека, рядом с Ришелье-Шато, вы сможете приобрести любое количество кварцевого песка, который всегда в наличии, а оплата может быть как наличными, так и по безналу с НДС. При существенных объемах мы делаем бесплатную доставку.  Если Вы живете в Гурзуфе или Краснокаменке, то наш магазин станет вашим любимым: рядом с домом (в шаговой доступности), товар от производителя, скидка 5% при первой покупке, накопительные скидки до 15%, распродажи и акции."
        },
        {
            "@id": "70299718",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70299718-drel_dvukhskorostnaya_udarnaya_msu9_16_2re_m",
            "price": "5882.0",
            "currencyId": "RUR",
            "categoryId": "104746",
            "picture": "http://st21.stpulscen.ru/images/product/118/549/785_original.jpg",
            "name": "Дрель двухскоростная ударная МСУ9-16-2РЭ М",
            "description": "Компактных размеров и современного дизайна с удобной ручкой дрель послужит для завинчивания, отвинчивания шурупов, винтов, бурения отверстий в камне и бетоне. Корпус изготовлен из сплава алюминия и это помогает отводить тепло и обеспечивает долговечность изделия. Покупайте по лучшей цене и с огромными скидками."
        },
        {
            "@id": "70313772",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70313772-drel_msu10_13_re_m",
            "price": "4622.0",
            "currencyId": "RUR",
            "categoryId": "114470",
            "picture": "http://st21.stpulscen.ru/images/product/118/583/491_original.jpg",
            "name": "Дрель МСУ10-13-РЭ М",
            "description": "Компактных размеров и современного дизайна с удобной ручкой дрель послужит для завинчивания, отвинчивания шурупов, винтов, бурения отверстий в камне и бетоне. Корпус изготовлен из сплава алюминия и это помогает отводить тепло и обеспечивает долговечность изделия. Покупайте по лучшей цене и с огромными скидками."
        },
        {
            "@id": "70377990",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70377990-keramzit_fr_10_20mm_1_m3_tsena_4500_rub_pri_zakaze_ot_40m3",
            "price": "4500.0",
            "currencyId": "RUR",
            "categoryId": "145466",
            "picture": "http://st21.stpulscen.ru/images/product/118/675/697_original.jpg",
            "name": "Керамзит фр. 10-20мм 1 м3 цена 4500 руб. при заказе от 40м3",
            "description": "Самый популярный насыпной утеплитель."
        },
        {
            "@id": "70555083",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555083-borozdodel_b2_30_v_korobke",
            "price": "9315.62",
            "currencyId": "RUR",
            "categoryId": "172490",
            "name": "Бороздодел Б2-30 (в коробке)",
            "description": "1600 Вт, скорость вращения 9000 об/мин, диск 125 мм, глубина паза 3-30 мм, макс.ширина паза 30 мм, возможность подключения пылесоса, плавный пуск, двойная изоляция, защита от токовой перегрузки, возможность использовать как углошлифовалую машину 125 мм"
        },
        {
            "@id": "70555084",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555084-borozdodel_b3_40_v_korobke",
            "price": "11319.5",
            "currencyId": "RUR",
            "categoryId": "172490",
            "name": "Бороздодел Б3-40 (в коробке)",
            "description": "1600 Вт, скорость вращения 9000 об/мин, диск 150 мм, глубина паза 40 мм, макс. возможность подключения пылесоса, плавный пуск, двойная изоляция, защита от токовой перегрузки, возможность использовать как углошлифовалую машину 150 мм"
        },
        {
            "@id": "70555085",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555085-akkumulyatornaya_drel_shurupovert_dsha1_10_re3_12_v_keyse",
            "price": "5805.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/358_original.jpg",
            "name": "Аккумуляторная дрель-шуруповерт ДША1-10-РЭ3-12 (в кейсе)",
            "description": "Номинальное напряжение 12В, Максимальный диаметр сверла по стали 7мм,по дереву 18мм. Максимальный диаметр шурупа 6мм. Масса не более 1,3кг.Масса машины с комплектом принадлежностей в кейсе не более 3,9кг.Емкость аккумулятора 1,3 А*ч. NiCd аккумуляторный блок, 2-х скоростной планетарный редуктор; реверс; выключатель с электронной регулировкой скорости; число ступеней регулировки момента:16+1; подсветка рабочей зоны; удобная обрезиненная рукоятка;магнитный держатель на рукоятке позволяет закрепить несколько винтов либо шурупов."
        },
        {
            "@id": "70555086",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555086-akkumulyatornaya_drel_shurupovert_dsha1_10_re3_14_4_v_keyse",
            "price": "6534.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/449_original.jpg",
            "name": "Аккумуляторная дрель-шуруповерт ДША1-10-РЭ3-14,4 (в кейсе)",
            "description": "Номинальное напряжение 14,4В, Максимальный диаметр сверла по стали 8мм,по дереву 20мм. Максимальный диаметр шурупа 6мм. Масса не более 1,5кг.Масса машины с комплектом принадлежностей в кейсе не более 4,1кг.Емкость аккумулятора 1,3 А*ч. NiCd аккумуляторный блок, 2-х скоростной планетарный редуктор; реверс; выключатель с электронной регулировкой скорости; число ступеней регулировки момента:16+1; подсветка рабочей зоны; удобная обрезиненная рукоятка;магнитный держатель на рукоятке позволяет закрепить несколько винтов либо шурупов."
        },
        {
            "@id": "70555087",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555087-akkumulyatornaya_drel_shurupovert_dsha1_10_re3_18_v_keyse",
            "price": "7581.0",
            "currencyId": "RUR",
            "categoryId": "273034",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/494_original.jpg",
            "name": "Аккумуляторная дрель-шуруповерт ДША1-10-РЭ3-18 (в кейсе)",
            "description": "Номинальное напряжение 18В, Максимальный диаметр сверла по стали 10мм,по дереву 24мм. Максимальный диаметр шурупа 6мм. Масса не более 1,7кг.Масса машины с комплектом принадлежностей в кейсе не более 4,3кг.Емкость аккумулятора 1,3 А*ч. NiCd аккумуляторный блок, 2-х скоростной планетарный редуктор; реверс; выключатель с электронной регулировкой скорости; число ступеней регулировки момента:16+1; подсветка рабочей зоны; удобная обрезиненная рукоятка;магнитный держатель на рукоятке позволяет закрепить несколько винтов либо шурупов."
        },
        {
            "@id": "70555088",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555088-akkumulyatornaya_drel_shurupover_dsha1_10_re4_12_v_keyse",
            "price": "7782.57",
            "currencyId": "RUR",
            "categoryId": "273034",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/495_original.jpg",
            "name": "Аккумуляторная дрель-шуруповер ДША1-10-РЭ4-12 (в кейсе)",
            "description": "Номинальное напряжение 12В, Максимальный диаметр сверла по стали 7мм,по дереву 18мм. Максимальный диаметр шурупа 6мм. Масса не более 1,3кг.Масса машины с комплектом принадлежностей в кейсе не более 3,9кг.Емкость аккумулятора 1,5 А*ч. Li-Ion аккумуляторный блок, 2-х скоростной планетарный редуктор; реверс; выключатель с электронной регулировкой скорости; число ступеней регулировки момента:18+1; подсветка рабочей зоны; удобная обрезиненная рукоятка."
        },
        {
            "@id": "70555089",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555089-akkumulyatornaya_drel_shurupover_dsha1_10_re4_18_v_keyse",
            "price": "10420.81",
            "currencyId": "RUR",
            "categoryId": "273034",
            "picture": "http://st30.stpulscen.ru/images/product/118/996/496_original.jpg",
            "name": "Аккумуляторная дрель-шуруповер ДША1-10-РЭ4-18 (в кейсе)",
            "description": "Номинальное напряжение 18В, Максимальный диаметр сверла по стали 10мм,по дереву 24мм. Максимальный диаметр шурупа 6мм. Масса не более 1,7кг.Масса машины с комплектом принадлежностей в кейсе не более 4,3кг.Емкость аккумулятора 1,5 А*ч. Li-Ion аккумуляторный блок, 2-х скоростной планетарный редуктор; реверс; выключатель с электронной регулировкой скорости; число ступеней регулировки момента:16+1; подсветка рабочей зоны; удобная обрезиненная рукоятка; магнитный держатель на рукоятке позволяет закрепить несколько винтов либо шурупов."
        },
        {
            "@id": "70555090",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555090-kraskoraspylitel_kr1_260_v_korobke",
            "price": "3469.2",
            "currencyId": "RUR",
            "categoryId": "81341",
            "name": "Краскораспылитель КР1-260 (в коробке)",
            "description": "60 Вт; Производительность - 260 г/мин; Диапазон вязкости - до 80 DIN-C; Давление - до 160 бар; Объем бачка - 0,7 л; 1,2 кг."
        },
        {
            "@id": "70555091",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555091-mixer_drel_md1_11e_v_korobke",
            "price": "5202.0",
            "currencyId": "RUR",
            "categoryId": "104801",
            "picture": "http://st30.stpulscen.ru/images/product/119/070/791_original.jpg",
            "name": "Миксер-дрель МД1-11Э (в коробке)",
            "description": "1100 Вт, патрон 16 мм (не входит в комплект), частота вращенияот 0 до 600 об/мин, внутрення резьба шпинделя М14, зажимная шейка - 57мм, максимальный момент 85 Нм, максимальный диаметр мешалок 160 мм (не входят в комплект)."
        },
        {
            "@id": "70555092",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555092-mixer_drel_md1_11e_m_master_v_korobke",
            "price": "7082.12",
            "currencyId": "RUR",
            "categoryId": "104801",
            "name": "Миксер-дрель МД1-11Э М \"Мастер\" (в коробке)",
            "description": "1100 Вт, патрон 16 мм (не входит в комплект), частота вращения от 0 до 600 об/мин, внутрення резьба шпинделя М14, зажимная шейка - 57мм, максимальный момент 85 Нм, максимальный диаметр мешалок 160 мм (не входят в комплект)."
        },
        {
            "@id": "70555094",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555094-ploskoshlifovalnaya_mashina_mpsh4_28e_v_korobke",
            "price": "6725.29",
            "currencyId": "RUR",
            "categoryId": "105037",
            "name": "Плоскошлифовальная машина МПШ4-28Э (в коробке)",
            "description": "600 Вт, частота колебаний шлифовальной платформы от 3000 до 6000 кол/мин, амплитуда колебаний 5 мм, размер шлифплатфомы 115 х 225 мм, размер шлифлиста 115 х 280 мм, электронника."
        },
        {
            "@id": "70555095",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555095-sverlilnaya_mashina_ms11_13re_v_korobke",
            "price": "3677.35",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина МС11-13РЭ (в коробке)",
            "description": "610 Вт, сверлильный патрон до 13 мм, частота вращения шпинделя 0-2800 об/мин, реверс, диаметр сверления в стали до 13 мм, мягком дереве 25 мм."
        },
        {
            "@id": "70555096",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555096-sverlilnaya_mashina_ms8_16re_m_master_v_keyse",
            "price": "8015.5",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина МС8-16РЭ М \"Мастер\" (в кейсе)",
            "description": "900 Вт, частота вращения шпинделя 0 до 600 об/мин, максимальный крутящий момент 86 Нм, реверс, диаметр сверления в стальи 16 мм, дереве 35 мм, коронками (60-80 мм). кейс."
        },
        {
            "@id": "70555097",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555097-sverlilnaya_mashina_msu10_13_re_m_master_v_keyse",
            "price": "6471.04",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина МСУ10-13-РЭ М \"Мастер\" (в кейсе)",
            "description": "750 Вт; Частота вращения - 0-2800 об/мин; Максимальный диаметр сверления: в стали - 13мм, в бетоне - 13мм, в древесине - 25 мм;Вес - 1,4 кг"
        },
        {
            "@id": "70555098",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555098-sverlilnaya_mashina_msu10_13_re_v_korobke",
            "price": "3981.31",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина МСУ10-13-РЭ (в коробке)",
            "description": "750 Вт, сверлильный патрон до 13 мм, частота вращения шпинделя 0-2800 об/мин, реверс, диаметр сверления в стали до 13 мм, бетоне 13 мм, мягком дереве 25 мм."
        },
        {
            "@id": "70555099",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555099-sverlilnaya_mashina_msu11_13re_v_korobke",
            "price": "3740.12",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина МСУ11-13РЭ (в коробке)",
            "description": "610 Вт, сверлильный патрон до 13 мм, частота вращения шпинделя 0-2800 об/мин, реверс, диаметр сверления в стали до 13 мм, в бетоне 13 мм, в мягком дереве 25 мм."
        },
        {
            "@id": "70555100",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555100-sverlilnaya_mashina_s_udarom_msu9_16_2re_v_keyse",
            "price": "7310.09",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина с ударом МСУ9-16-2РЭ (в кейсе)",
            "description": "1050 Вт, сверлильный патрон 13 мм, частота вращения шпинделя 0-800 / 800-2000 об/мин, реверс, диаметр сверления в стали до 16 мм, бетоне 20 мм, мягком дереве 45 мм, в кейсе."
        },
        {
            "@id": "70555101",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555101-sverlilnaya_mashina_s_udarom_msu9_16_2re_m_master_v_keyse",
            "price": "8235.21",
            "currencyId": "RUR",
            "categoryId": "105078",
            "name": "Сверлильная машина с ударом МСУ9-16-2РЭ М \"Мастер\" (в кейсе)",
            "description": "1050 Вт, сверлильный патрон 13 мм, частота вращения шпинделя 0-800 / 800-2000 об/мин, реверс, диаметр сверления в стали до 16 мм, бетоне 20 мм, мягком дереве 45 мм., кейс."
        },
        {
            "@id": "70555102",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555102-frezernaya_mashina_mf2_620e_v_korobke",
            "price": "4625.59",
            "currencyId": "RUR",
            "categoryId": "105095",
            "name": "Фрезерная машина МФ2-620Э (в коробке)",
            "description": "620 Вт,частота вращения фрезы на холостом ходу от 7800 до 32000 об/мин, зажимная цанга под диаметр 8 мм, максимальный ход фрезы 50 мм, установка глубины фрезерования револьверная, 3 ступенчатая, шкала глубины погружения фрезы."
        },
        {
            "@id": "70555103",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555103-frezernaya_mashina_mf3_1100e_v_korobke",
            "price": "5339.26",
            "currencyId": "RUR",
            "categoryId": "105095",
            "name": "Фрезерная машина МФ3-1100Э (в коробке)",
            "description": "1100 Вт,частота вращения фрезы на холостом ходу от 0 до 30000 об/мин, зажимная цанга под диаметр 8 мм, максимальный ход фрезы 50 мм, установка глубины фрезерования револьверная, 3 ступенчатая, шкала глубины погружения фрезы."
        },
        {
            "@id": "70555104",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555104-ugloshlifovalnaya_mashina_mshu1_20_230a_v_korobke",
            "price": "6978.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "picture": "http://st30.stpulscen.ru/images/product/119/070/940_original.jpg",
            "name": "Углошлифовальная машина МШУ1-20-230А (в коробке)",
            "description": "2000 Вт, скорость вращения 6500 об/мин, диаметр диска 230 мм, резьба ведущего шпинделя М14."
        },
        {
            "@id": "70555105",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555105-ugloshlifovalnaya_mashina_mshu1_23_230_m_master_v_korobke",
            "price": "9705.5",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ1-23-230 М \"Мастер\" (в коробке)",
            "description": "2300 Вт, скорость вращения 6500 об/мин, диаметр диска 230 мм, резьба ведущего шпинделя М14, плавный пуск"
        },
        {
            "@id": "70555106",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555106-ugloshlifovalnaya_mashina_mshu1_23_230b_v_korobke",
            "price": "8785.33",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ1-23-230Б (в коробке)",
            "description": "2300 Вт, скорость вращения 6500 об/мин, диаметр диска 230 мм, резьба ведущего шпинделя М14, плавный пуск, ограничение пускового тока, защиты от перегрузки"
        },
        {
            "@id": "70555107",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555107-ugloshlifovalnaya_mashina_mshu2_9_125_v_korobke",
            "price": "4113.0",
            "currencyId": "RUR",
            "categoryId": "116661",
            "picture": "http://st30.stpulscen.ru/images/product/119/070/886_original.jpg",
            "name": "Углошлифовальная машина МШУ2-9-125 (в коробке)",
            "description": "920 Вт, скорость вращения 11000 об/мин, диаметр диска 125 мм, резьба ведущего шпинделя М14."
        },
        {
            "@id": "70555108",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555108-ugloshlifovalnaya_mashina_mshu2_9_125e_v_korobke",
            "price": "5380.56",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ2-9-125Э (в коробке)",
            "description": "900 Вт, регулировка числа оборотов 2800-9000 об/мин, диаметр диска 125 мм, резьба ведущего шпинделя М14. Плавный пуск. Электроника."
        },
        {
            "@id": "70555109",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555109-ugloshlifovalnaya_mashina_mshu2_9_125e_m_master_v_keyse",
            "price": "6548.52",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ2-9-125Э М \"Мастер\" (в кейсе)",
            "description": "900 Вт, регулировка числа оборотов2800-9000 об/мин, , диаметр диска 125 мм, резьба ведущего шпинделя М14. кейс"
        },
        {
            "@id": "70555110",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555110-ugloshlifovalnaya_mashina_mshu3_11_150_v_korobke",
            "price": "5297.96",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ3-11-150 (в коробке)",
            "description": "1100 Вт, скорость вращения 8500 об/мин, диаметр диска 150 мм, резьба ведущего шпинделя М14."
        },
        {
            "@id": "70555111",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555111-ugloshlifovalnaya_mashina_mshu5_11_150_v_korobke",
            "price": "5380.56",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ5-11-150 (в коробке)",
            "description": "1100 Вт, скорость вращения 6200 об/мин, диаметр диска 150 мм, резьба ведущего шпинделя М14. Поворотная основная ручка."
        },
        {
            "@id": "70555112",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555112-polirovatel_po_betonu_mshu8_14_125_m_master_v_korobke",
            "price": "9388.31",
            "currencyId": "RUR",
            "categoryId": "173372",
            "name": "Полирователь по бетону МШУ8-14-125 М \"Мастер\" (в коробке)",
            "description": "1400 Вт.; Диаметр круга - 125 мм.; Частота вращения - 9600 об/мин.; Резьба шпинделя - М14; Длина сетевого шнура - 2,2 м.; 2,8 кг., электроника. Бетоношлифователь, 2 в 1 возможность использовать как МШУ с кругом 125 мм."
        },
        {
            "@id": "70555113",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555113-ugloshlifovalnaya_mashina_mshu9_16_180_v_korobke",
            "price": "7029.25",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ9-16-180 (в коробке)",
            "description": "1600 Вт.; Диаметр круга - 180 мм.; Частота вращения - 8400 об/мин.; Резьба шпинделя - М14; Длина сетевого шнура - 2,2 м.; 2,8 кг."
        },
        {
            "@id": "70555114",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555114-ugloshlifovalnaya_mashina_mshu9_16_180e_v_korobke",
            "price": "7604.15",
            "currencyId": "RUR",
            "categoryId": "116661",
            "name": "Углошлифовальная машина МШУ9-16-180Э (в коробке)",
            "description": "1600 Вт.; Диаметр круга - 180 мм.; Частота вращения - 8400 об/мин.; Резьба шпинделя - М14; Длина сетевого шнура - 2,2 м.; 2,8 кг., электронная защита от перегрузки."
        },
        {
            "@id": "70555115",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555115-perforator_p6_1200_e_v_keyse",
            "price": "9730.27",
            "currencyId": "RUR",
            "categoryId": "114477",
            "name": "Перфоратор П6-1200-Э (в кейсе)",
            "description": "1200 Вт, SDS-Plus, три режима работы, энергия удара 6,5 Дж, частота вращения шпинделя на х/х - 0-950 об/мин, макс. диаметр сверления в бетоне - 32 мм, в дереве - 40 мм, стали - 13 мм, в бетоне полой коронкой 65 мм, пластиковый кейс."
        },
        {
            "@id": "70555116",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555116-perforator_p7_1500_e_v_keyse",
            "price": "8849.0",
            "currencyId": "RUR",
            "categoryId": "114477",
            "picture": "http://st30.stpulscen.ru/images/product/119/070/831_original.jpg",
            "name": "Перфоратор П7-1500-Э (в кейсе)",
            "description": "1500 Вт, SDS-Plus, три режима работы, энергия удара 8 Дж, частота вращения шпинделя на х/х - 0-900 об/мин, макс. диаметр сверления в бетоне - 32 мм, в дереве - 40 мм, стали - 13 мм, в бетоне полой коронкой 65 мм, пластиковый кейс."
        },
        {
            "@id": "70555117",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555117-pila_diskovaya_pd3_70_v_korobke",
            "price": "10087.11",
            "currencyId": "RUR",
            "categoryId": "108051",
            "name": "Пила дисковая ПД3-70 (в коробке)",
            "description": "2000 Вт, Глубина пропила (макс) 90 градусов - 0-70 мм, Диаметр диска - 210 мм, Частота вращения - 4500 об/мин, Угол реза- 0-45 градусов, - 5,9 кг"
        },
        {
            "@id": "70555118",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555118-pila_diskovaya_pd4_54_v_korobke",
            "price": "7159.76",
            "currencyId": "RUR",
            "categoryId": "108051",
            "name": "Пила дисковая ПД4-54 (в коробке)",
            "description": "1100 Вт, Глубина пропила - 90 градусов -0-54 мм, 45 градусов - 0-34 мм, Внешний диаметр пильного диска - 160 мм, Посадочный диаметр - 20 мм, Частота вращения - 5000 об/мин, Угол реза- 0-45 градусов, 3,5 кг"
        },
        {
            "@id": "70555119",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555119-pila_diskovaya_pd7_75_v_korobke",
            "price": "10581.06",
            "currencyId": "RUR",
            "categoryId": "108051",
            "name": "Пила дисковая ПД7-75 (в коробке)",
            "description": "2300 Вт; Диаметр пильного диска/отверстия - 210/30 мм; Частота вращения на холостом ходу - 4800 мин-1; Максимальная глубина пропила 90°/45° - 75/48 мм; Угол наклона - 45°; 6,5 кг."
        },
        {
            "@id": "70555120",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555120-lobzik_elektricheski_pm3_600e_v_korobke",
            "price": "3464.0",
            "currencyId": "RUR",
            "categoryId": "114473",
            "picture": "http://st30.stpulscen.ru/images/product/119/071/000_original.jpg",
            "name": "Лобзик электрический ПМ3-600Э (в коробке)",
            "description": "600 Вт, маятниковый ход, число двойных ходов пилы 0 - 2600 ход/мин, глубина пропила в дереве 85 мм, цветном металле 20 мм, стали 10 мм, угол наклона пилки (в обе стороны) 45°, регулировка маятникового хода-3 ступени, индивидуальная упаковка."
        },
        {
            "@id": "70555121",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555121-lobzik_elektricheski_pm3_650e_v_korobke",
            "price": "4126.69",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический ПМ3-650Э (в коробке)",
            "description": "650 Вт, маятниковый ход, число двойных ходов пилы 0 - 2600 ход/мин, глубина пропила в дереве 100 мм, цветном металле 20 мм, стали 10 мм, угол наклона пилки (в обе стороны) 45°, регулировка маятникового хода-3 ступени."
        },
        {
            "@id": "70555122",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555122-lobzik_elektricheski_pm4_700e_v_korobke",
            "price": "4577.69",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический ПМ4-700Э (в коробке)",
            "description": "700 Вт, маятниковый ход, число двойных ходов пилы 0 - 3000 ход/мин, глубина пропила в дереве 110 мм, цветном металле 20 мм, стали 10 мм, угол наклона пилки (в обе стороны) 45°, индивидуальная упаковка."
        },
        {
            "@id": "70555123",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555123-lobzik_elektricheski_pm5_720e_v_keyse",
            "price": "5317.78",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический ПМ5-720Э (в кейсе)",
            "description": "720 Вт, маятниковый ход, число двойных ходов пилы 0 - 3000 ход/мин, глубина пропила в дереве 115 мм, цветном металле 20 мм, стали 10 мм, угол наклона пилки (в обе стороны) 45°, в кейсе."
        },
        {
            "@id": "70555124",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555124-lobzik_elektricheski_pm5_720e_v_korobke",
            "price": "4792.45",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический ПМ5-720Э (в коробке)",
            "description": "720 Вт, маятниковый ход, число двойных ходов пилы 0 - 3000 ход/мин, глубина пропила в дереве 115 мм, цветном металле 20 мм, стали 10 мм, угол наклона пилки (в обе стороны) 45°, индивидуальная упаковка."
        },
        {
            "@id": "70555125",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555125-lobzik_elektricheski_pm5_750e_m_master_v_keyse",
            "price": "6115.7",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Лобзик электрический ПМ5-750Э М \"Мастер\" (в кейсе)",
            "description": "750 Вт, литая подошва, улучшенный обдув зоны реза, маятниковый ход, число двойных ходов пилы 0-2800 ход/мин, глубина пропила в дереве 135 мм, цветном металле 20мм, стали 10мм, угол наклона пилки 45°, в кейсе."
        },
        {
            "@id": "70555126",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555126-rubanok_r3_82_v_korobke",
            "price": "8210.43",
            "currencyId": "RUR",
            "categoryId": "114483",
            "name": "Рубанок Р3-82 (в коробке)",
            "description": "1050 Вт, частота вращения ножа 15000 об/мин, ширина строгания 82 мм, глубина строгания 3 мм, глубина выборки четверти до 13 мм."
        },
        {
            "@id": "70555127",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555127-shurupovert_setevoy_shv3_6_re_v_korobke",
            "price": "4275.37",
            "currencyId": "RUR",
            "categoryId": "106393",
            "name": "Шуруповерт сетевой ШВ3-6-РЭ (в коробке)",
            "description": "610 Вт, Частота вращения шпинделя на холостом ходу - 0-2800 об/мин, Держатель насадок - 6,35 внутренний шестигранник, Максимальный диаметр шурупа 6 мм, Область применения: • Завинчивание, отвинчивание шурупов и винтов в строительстве и сборочных работах."
        },
        {
            "@id": "70555128",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555128-shurupovert_setevoy_shv3_6_re_m_master_v_korobke",
            "price": "4810.62",
            "currencyId": "RUR",
            "categoryId": "106393",
            "name": "Шуруповерт сетевой ШВ3-6-РЭ М \"Мастер\" (в коробке)",
            "description": "610 Вт; Частота вращения - 0-2800 об/мин; Держатель насадок - 6,35 внутренний шестигранник; Максимальный диаметр шурупа - 6 мм;Вес - 1,2 кг; работа по профнастилу (в комплекте удлененнтая втулка)"
        },
        {
            "@id": "70555129",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555129-nasadka_na_md1_11e_002i_pravostoronnyaya",
            "price": "797.91",
            "currencyId": "RUR",
            "categoryId": "116502",
            "name": "Насадка на МД1-11Э (002И) (правосторонняя)",
            "description": "Рекомендуется для извести, бетона, цементной или известковой штукатурки, заливочных компаундов, бесшовных полов, эпоксидных смол, битумных покрытийВетви спирали, направленные по часовой стрелке, при вращении вкручивают насадку в раствор. Перемешивающий эффект снизу вверх. Быстрое интенсивное и однородное смешивание тяжелых смесей с высокой вязкостью."
        },
        {
            "@id": "70555130",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555130-nasadka_na_md1_11e_001i_universalnaya",
            "price": "778.09",
            "currencyId": "RUR",
            "categoryId": "116502",
            "name": "Насадка на МД1-11Э (001И) (универсальная)",
            "description": "Рекомендуется для:плиточных клеев; заливочной массы; клеевого строительного раствора; готовой штукатурки; бесшовных полов; эпоксидных смол; заливочных компаундов."
        },
        {
            "@id": "70555131",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555131-nasadka_idfr304159003i",
            "price": "797.91",
            "currencyId": "RUR",
            "categoryId": "116502",
            "name": "Насадка ИДФР304159003И",
            "description": "Рекомендуется для Дисперсныйх красок, Настенных красок, Заливочной массыНе разбрызгивается!Ветви спирали направлены по часовой стрелке, при вращении вкручивают насадку в раствор; выполняет перемешивания сверху вниз. Смесь направляется ко дну. Смешивание без разбрызгивания текучих жидких смесей, приготовление красок из компонентов различных цветов."
        },
        {
            "@id": "70555132",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555132-nasadka_n1_k_mshu",
            "price": "1167.96",
            "currencyId": "RUR",
            "categoryId": "116502",
            "name": "Насадка Н1 к МШУ",
            "description": "Специальная насадка Н-1 к угловой шлифовальной машине МШУ 2-9-125 Э. Применяется для зачистных и отрезных работ в труднодоступных местах, связанных с автослесарными, слесарными и сантехническими работами."
        },
        {
            "@id": "70555133",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555133-lineyka_k_lobziku",
            "price": "289.1",
            "currencyId": "RUR",
            "categoryId": "114473",
            "name": "Линейка к лобзику",
            "description": "Пользуясь электролобзиком, Вы можете значительно расширить сферу его применения, приобретя линейку-циркуль, производства ДП \"Фиолентмехпласт\". С ее помощью возможно: - выпилить идеально-круглое отверстие. - периодически изменяя центр базирования, выпилить лекальную кривую. - обеспечить прямолинейное направление распила параллельно выбранной кромке. - строгание под углом от 0° до 45° - пиление на выставляемую ширину от 0 до 80мм."
        },
        {
            "@id": "70555134",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555134-lineyka_uglovaya_k_rubanku",
            "price": "1762.68",
            "currencyId": "RUR",
            "categoryId": "173008",
            "name": "Линейка угловая к рубанку",
            "description": "С ее помощью Вы сможете:- производить строгание материала под углом 0°-45°- устанавливать ширину строгания 0-82 мм- обеспечить выборку фальца( четверти) глубиной 0-12 мм."
        },
        {
            "@id": "70555136",
            "@available": "true",
            "url": "http://www.orpro.ru/goods/70555136-stol_dlya_lobzika_idfr301313003",
            "price": "1731.29",
            "currencyId": "RUR",
            "categoryId": "174708",
            "name": "Стол для лобзика ИДФР301313003",
            "description": "Позволяет стационарно установить лобзик для точного прямолинейного и фигурного реза."
        }
    ]

    for i in rr:
        kk = Offers (offer_url=i['url'][26:], offer_valuta=i['currencyId'], offer_price=i['price'],
                     offer_title=i['name'],
                     offer_text=i['description'], offer_pre_text=i['description'][:100])
        try:
            kk.offer_photo_url = i['picture']
        except KeyError:
            print ("lol")
        tag1 = Tags.objects.get(tag_id=i['categoryId'])
        kk.offer_main_tag = tag1

        kk.save ()

