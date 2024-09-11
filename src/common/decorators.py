from .helpers import build_absolute_uri

def add_url(method, field_name='detail_url'):
    '''Adds url to representation'''

    def wrapper(self, instance):
        model_method = getattr(instance, 'get_absolute_url', lambda *a: '')
        url = model_method()
        if url:
            url = build_absolute_uri(url)
        representation =  method(self, instance)
        representation[field_name] = url
        return representation

    return wrapper