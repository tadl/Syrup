from django.contrib import admin
import django.db.models
from django import forms
from conifer.syrup.models import *

for m in [ServiceDesk, Group, Course,
          Department, Site, Term, 
Config, Z3950Target]:
    admin.site.register(m)

class ItemAdmin(admin.ModelAdmin):
    search_fields = ['title', 'barcode', 'bib_id']
    model = Item

admin.site.register(Item, ItemAdmin)

class MembershipAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.order_by('username'))

    class Meta:
        model = Membership

class MembershipAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'group__external_id', 
                     'group__site__course__code']
    form = MembershipAdminForm

admin.site.register(Membership, MembershipAdmin)

class UserProfileAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.order_by('username'))

    class Meta:
        model = UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm

admin.site.register(UserProfile, UserProfileAdmin)
