"""
WSGI config for stract project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os, sys
from decouple import config

from django.core.wsgi import get_wsgi_application

#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stract.settings')

#application = get_wsgi_application()

sys.path.append(config('WSGI_PATH'))
#sys.path.append('/home/cademio/virtualenv/public__html_stract__py/3.6/bin/stract/stract/')

#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stract.settings')

os.environ["DJANGO_SETTINGS_MODULE"] = "stract.settings"

application = get_wsgi_application()
