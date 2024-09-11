import logging
from datetime import timedelta
from collections import namedtuple

from django.conf import settings


from django.contrib.auth.models import User


def build_absolute_uri(path):
    return f'{settings.SITE_URL}{path}'


def get_urls():
    # list all url endpoints
    import sys 
    for route in router.get_urls():
        print(f'path={route.name}', end='\t')
        print(f'lookup_str={route.lookup_str}')


class Log:
    @staticmethod
    def log(msg, error_level=logging.DEBUG, **kw):
        return logging.log(error_level, msg, **kw)


FRONTEND_LINKS = {
    'login': '/login',
    'general_settings': '/settings/general-settings',
    'add_codes': '/codebase/show/{codebase_id}/manage',
    'add_auction': '/ebay/new-auction',
    'accounts': '/ebay/accounts',
    'edit_auction': '/ebay/{account_id}/edit?auctionId={auction_id}',
    'edit_layout': '/settings/layout/edit/{layout_id}',
}


def GetFrontendLink(key, default='#'):
    return settings.FRONTEND_DOMAIN + FRONTEND_LINKS.get(key, default)


def dict_to_object(dict_obj, class_name='Object', struct=()):
    """
    Convert a dictionary to an object with named attributes.
    
    Args:
        dict_obj (dict): The dictionary to be converted.
        class_name (str, optional): The name of the class. Default is 'Object'.
    
    Returns:
        namedtuple: An object with named attributes.
    """
    for i in struct:
        dict_obj.setdefault(i, None)
    return namedtuple(class_name, dict_obj.keys())(*dict_obj.values())


def complete_media_url(url):
    return settings.SITE_URL + settings.MEDIA_URL.rstrip('/') + '/' + url.lstrip('/')\


def format_money(money, default=0):
    if money:
        return f"{money.currency}{money.amount}"
    else:
        return default




def generate_date_dict(start_date, end_date, date_format='%Y-%m-%d', value='0'):
    start = min(start_date, end_date)
    end = max(start_date, end_date)

    num_days = (end - start).days

    dict_ = {}

    for days in range(num_days+1):
        current = start + timedelta(days=days)
        dict_[current.strftime(date_format)] = value

    return dict_

