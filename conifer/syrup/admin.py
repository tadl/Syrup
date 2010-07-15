# to run standalone: From conifer directory:
# DJANGO_SETTINGS_MODULE=conifer.settings PYTHONPATH=.. python syrup/admin.py

from django.contrib import admin
import django.db.models
from conifer.syrup.models import *

for m in [ServiceDesk, Group, Membership, Course,
          Department, ReadingList, Term, 
          UserProfile, Config, Z3950Target]:
    admin.site.register(m)


class MetadataInline(admin.StackedInline):
    model = Metadata
    extra = 3

class ItemAdmin(admin.ModelAdmin):
    model = Item
    inlines = [MetadataInline]

admin.site.register(Item, ItemAdmin)
