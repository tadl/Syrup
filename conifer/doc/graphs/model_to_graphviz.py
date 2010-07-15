# Generate a graph visualization from the model. Requires Graphviz.
# To run, from conifer directory:
# DJANGO_SETTINGS_MODULE=conifer.settings PYTHONPATH=.. python doc/graphs/model_to_graphviz.py  | dot -Tpng > /tmp/syrup-model.png
# You might try 'fdp' instead of 'dot'; 'neato' and 'circo' give poorer results.

import sys
import django.db.models
import conifer.syrup.models as models
#import conifer.syrup.direct_models as models

from django.db.models.fields.related import (ForeignRelatedObjectsDescriptor, 
                                             ManyRelatedObjectsDescriptor)

print 'digraph a {'
print '{ splines=true; }'
print 'graph [ label="dotted-end is the \'many\' end", splines=true ]'

all = set(); linked = set(); primary = set()

for name, value in models.__dict__.items():
    if isinstance(value, type) and issubclass(value, django.db.models.Model):
        try:
            if value._meta.abstract:
                continue
        except:
            pass
        local = value.__name__
        all.add(local)
        for k, v in value.__dict__.items():
            if isinstance(v, ForeignRelatedObjectsDescriptor):
                foreign = v.related.model.__name__
                print '%s -> %s [ arrowhead=dot, arrowtail=none ];' % (local, foreign)
                primary.add(local); linked.add(local); linked.add(foreign)
            if isinstance(v, ManyRelatedObjectsDescriptor):
                foreign = v.related.model.__name__
                print '%s -> %s [ arrowhead=dot, arrowtail=dot ];' % (local, foreign)
                primary.add(local); linked.add(local); linked.add(foreign)
for n in (all - linked):
    print '%s [ style=dashed ]' % n

for n in primary:
    print '%s [ color=blue ]' % n
print '}'
