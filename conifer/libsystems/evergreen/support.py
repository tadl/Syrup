import warnings
import urllib2
from urllib import quote
from django.utils import simplejson as json
from xml.etree import ElementTree
import re
import sys, os

LOCALE = 'en-US'

#------------------------------------------------------------
# parse fm_IDL, to build a field-name-lookup service.

fields_for_class = {}
BASE = None

def initialize(base):
    global BASE
    if not BASE:
        assert base.endswith('/')
        BASE = base
        fields_for_class.update(dict(_fields()))

def _fields():
    fm_idl_file = os.path.join(os.path.dirname(__file__), 'fm_IDL.xml')
    with open(fm_idl_file) as f:
        tree = ElementTree.parse(f)
    # fm_IDL_location = BASE + 'reports/fm_IDL.xml'
    # tree = ElementTree.parse(urllib2.urlopen(fm_IDL_location))
    NS = '{http://opensrf.org/spec/IDL/base/v1}'
    for c in tree.findall('%sclass' % NS):
        cid = c.attrib['id']
        fields = [f.attrib['name'] \
                  for f in c.findall('%sfields/%sfield' % (NS,NS))]
        yield (cid, fields)


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
    params += ['param=%s' % quote(json.dumps(a)) for a in args]
    url = '%sosrf-gateway-v1?%s' % (BASE, '&'.join(params))
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
