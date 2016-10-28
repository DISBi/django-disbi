# Django
from django.template.defaulttags import register


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_list(qdict, key):
    return qdict.getlist(key=key)

@register.filter
def get_item_by_idx(iters, idx):
    return iters[idx]
