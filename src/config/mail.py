import os, os.path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Email
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = os.getenv('EMAIL_PORT', 1025)
# EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@somehost.local')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Elastic Email
ELASTIC_EMAIL_NAME=os.getenv('ELASTIC_EMAIL_NAME', 'AutoVerify')
ELASTIC_EMAIL=os.getenv('ELASTIC_EMAIL', 'noreply@bloombyte.dev')
ELASTIC_EMAIL_KEY=os.getenv('ELASTIC_EMAIL_KEY')

# Zepto Mail
ZEPTO_EMAIL_NAME=os.getenv('ZEPTO_EMAIL_NAME', 'AutoVerify')
ZEPTO_EMAIL=os.getenv('ZEPTO_EMAIL', 'noreply@bloombyte.dev')
ZEPTO_API_KEY=os.getenv('ZEPTO_API_KEY')