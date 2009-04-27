import warnings
import urllib2
from urllib import quote
from django.utils import simplejson as json
from xml.etree import ElementTree
import re
import sys, os

#------------------------------------------------------------
# Configuration

# where is our evergreen server's opensrf http gateway?

BASE = 'http://concat.ca/osrf-gateway-v1'
LOCALE = 'en-US'

# where can I find a copy of fm_IDL.xml from Evergreen?

# # This will work always, though maybe you want to up the rev number...
# FM_IDL_LOCATION = ('http://svn.open-ils.org/trac/ILS/export/12640'
#                    '/trunk/Open-ILS/examples/fm_IDL.xml')

# # or, if you have a local copy...
# FM_IDL_LOCATION = 'file:fm_IDL.xml'

FM_IDL_LOCATION = 'http://concat.ca/reports/fm_IDL.xml'
here = lambda s: os.path.join(os.path.dirname(__file__), s)
FM_IDL_LOCATION = 'file:' + here('fm_IDL.xml')

#------------------------------------------------------------
# parse fm_IDL, to build a field-name-lookup service.

def _fields():
    tree = ElementTree.parse(urllib2.urlopen(FM_IDL_LOCATION))
    NS = '{http://opensrf.org/spec/IDL/base/v1}'
    for c in tree.findall('%sclass' % NS):
        cid = c.attrib['id']
        fields = [f.attrib['name'] \
                  for f in c.findall('%sfields/%sfield' % (NS,NS))]
        yield (cid, fields)

fields_for_class = dict(_fields())

#------------------------------------------------------------

def evergreen_object(rec):
    """Where possible, add field-names to an Evergreen return-value."""
    if isinstance(rec, list):
        return map(evergreen_object, rec)
    if not (isinstance(rec, dict) and '__c' in rec):
        return rec
    else:
        kls    = rec['__c']
        data   = rec['__p']
        fields = fields_for_class[kls]
        #print '----', (kls, fields)
        return dict(zip(fields, map(evergreen_object, data)))

def evergreen_request(method, *args, **kwargs):
    service = '.'.join(method.split('.')[:2])
    kwargs.setdefault('locale', LOCALE)
    kwargs.update({'service':service, 'method':method})
    params =  ['%s=%s' % (k,quote(v)) for k,v in kwargs.items()] 
    params += ['param=%s' % quote(str(a)) for a in args]
    url = '%s?%s' % (BASE, '&'.join(params))
    req = urllib2.urlopen(url)
    resp = json.load(req)
    assert resp['status'] == 200, 'error during evergreen request'
    payload = resp['payload']
    #print '----', payload
    return evergreen_object(payload)

def evergreen_request_single_result(method, *args):
    resp = evergreen_request(method, *args)
    if not resp:
        return None
    elif len(resp) > 1:
        warnings.warn('taking single value from multivalue evergreen response')
        print >> sys.stderr, repr(resp)
    return resp[0]


#------------------------------------------------------------
# Abbreviations

ER = evergreen_request
E1 = evergreen_request_single_result
