import conifer.genshi_support as g
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.forms import ModelForm, ValidationError


def generic_handler(form, decorator=lambda x: x):
    def handler(request, obj_id=None, action=None):
        if obj_id is None and action is None:
            return generic_index(form)
        elif action is None:
            return generic_edit(form, request, obj_id)
        elif action == 'delete':
            return generic_delete(form, request, obj_id)
    return decorator(handler)


def generic_index(form):
    assert hasattr(form, 'Index')
    return g.render('generic/index.xhtml', form=form)

def generic_edit(form, request, obj_id):
    if obj_id == '0':
        instance = None
    else:
        instance = get_object_or_404(form.Meta.model, pk=obj_id)
    if request.method != 'POST':
        form = form(instance=instance)
        return g.render('generic/edit.xhtml', **locals())
    else:
        form = form(request.POST, instance=instance)
        if not form.is_valid():
            return g.render('generic/edit.xhtml', **locals())
        else:
            form.save()
            return HttpResponseRedirect('../')

def generic_delete(form, request, obj_id):
    instance = get_object_or_404(form.Meta.model, pk=obj_id)
    if request.method != 'POST':
        form = form(instance=instance)
        return g.render('generic/delete.xhtml', **locals())
    else:
        instance.delete()
        return HttpResponseRedirect('../')


def strip_and_nonblank(fieldname):
    def clean(self):
        v = self.cleaned_data.get(fieldname) or ''
        if not v.strip():
            raise ValidationError('Cannot be blank.')
        return v.strip()
    return clean
