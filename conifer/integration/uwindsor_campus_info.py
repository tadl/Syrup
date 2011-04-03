from urllib2 import *
from django.utils import simplejson
from django.conf import settings

def call(name, *args):
    url = '%s%s?%s' % (settings.CAMPUS_INFO_SERVICE, name, simplejson.dumps(args))
    raw = urlopen(url).read()
    return simplejson.loads(raw)

if __name__ == '__main__':
    print call('methods_supported')
    print call('person_lookup', 'fawcett')
