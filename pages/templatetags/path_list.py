import random
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
