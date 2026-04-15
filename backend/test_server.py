#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promptx_project.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:5000', '--noreload'])
