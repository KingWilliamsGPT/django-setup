from src.config.common import *  # noqa
from src.config.logging import *


# Testing
INSTALLED_APPS += ('django_nose',)  # noqa
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['-s', '--nologcapture', '--with-progressive', '--with-fixture-bundling']

# INSTALLED_APPS += ['']
