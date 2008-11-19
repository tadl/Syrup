# to run standalone: From conifer directory:
# DJANGO_SETTINGS_MODULE=conifer.settings PYTHONPATH=.. python syrup/admin.py

from django.contrib import admin
import django.db.models
#import conifer.syrup.models as models
from conifer.syrup.models import *
# from django.db.models.fields import CharField

# def unicode_fn(fld):
#     def un(self):
#         return getattr(self, fld)
#     return un

# for name, value in models.__dict__.items():
#     if isinstance(value, type) and issubclass(value, django.db.models.Model):
#         localfields = value._meta.local_fields
#         tmp = [x for x in localfields if isinstance(x, CharField)]
#         if tmp:
#             firstcharfield = tmp[0].name
#             print (value.__name__, firstcharfield)
#             value.__unicode__ = unicode_fn(firstcharfield)
#         admin.site.register(value)

for m in [LibraryUnit, ServiceDesk, Member, Department, Course, Term, UserProfile, NewsItem]:
    admin.site.register(m)
