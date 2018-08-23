import random
from django import template
from .get_html_comments import get_html_comments, comment_search_expr

register = template.Library()


@register.filter(name='path_list')
def return_path_list(value, index='None'):
    split_list = value.split('/')[1:]
    return split_list if type(index) != int else split_list[index]


@register.filter(name='random_sort')
def random_sort(tags_list):
    ''' Blends the tag list for the cloud '''
    return sorted(tags_list, key=lambda x: random.random())


@register.filter(name='offer_pre_text')
def offer_pre_text(value):
    comments = get_html_comments(value, comment_search_expr)
    return comments if comments else value[:max(200, len(value) - 1)]
