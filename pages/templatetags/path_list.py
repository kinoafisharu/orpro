import random
import re
from django import template

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
    result = re.findall(r'(p|li)>([0-9a-zA-Zа-яА-Я\t&;\.,:\- ]+)<\/(p|li)', value)
    search_result = ""
    for result_element in result:
        #search_result = result[random.randint(0, len(result) - 1)][1]
        if len(search_result) + len(result_element[1]) <= 200:
            search_result += result_element[1]
        else:
            continue
    return search_result
