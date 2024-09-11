# import os


# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#             'formatter': 'standard'
#         },
#         'file': {
#             'level': os.getenv('LOGGING_LEVEL', 'ERROR'),
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': 'info.log',
#             'maxBytes': 1024 * 1024 * 1,  # 1 MB
#             # 'backupCount': 1,
#             'formatter': 'standard',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console', 'file'],
#             'level': os.getenv('LOGGING_LEVEL', 'ERROR'),
#             'propagate': True,
#         },
#         'django.utils.autoreload': {
#             'level': 'WARNING',
#         }
#     },
#     'formatters': {
#         'standard': {
#             'format': '{levelname} {asctime} - {message}',
#             'style': '{',
#         },
#     }
# }