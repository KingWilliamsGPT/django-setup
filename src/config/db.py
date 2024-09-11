import os, os.path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# construct database settings based on chosen backend only postgres and mysql has been setup for now
alt_backend = {
    'postgres': 'django.db.backends.postgresql',
    'mysql': 'django.db.backends.mysql',
}

USE_DEFAULT_BACKEND = os.getenv('USE_DEFAULT_BACKEND') == 'True'
ALT_BACKEND = str(os.getenv('ALT_BACKEND')).lower()


class ImproperlyConfigured(Exception):
    pass


try:
    db_backend = alt_backend[ALT_BACKEND]
except KeyError:
    raise ImproperlyConfigured(f'ALT_BACKEND={ALT_BACKEND} in .env change it to either postgres or mysql.')

if USE_DEFAULT_BACKEND:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': db_backend,
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST', 'db'),
            'PORT': os.getenv('DB_PORT'),
            # 'CONN_MAX_AGE': 300, # this was a bad idea
        }
    }
