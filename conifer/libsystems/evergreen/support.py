import warnings
import urllib2
from urllib import quote
from django.utils import simplejson as json
from xml.etree import ElementTree
import re
import sys, os

#------------------------------------------------------------
# parse fm_IDL, to build a field-name-lookup service.

fields_for_class = {}
GATE = None
LOCALE = 'en-US'                # fixme, this shouldn't be here.


def initialize(integration_object):
    global GATE
    if not GATE:
        GATE = integration_object.GATEWAY_URL
        fm_idl_url = integration_object.IDL_URL
        fields_for_class.update(dict(_fields(fm_idl_url)))

def _fields(fm_idl_url):
    print 'Loading fm_IDL from %s' % fm_idl_url
    f = urllib2.urlopen(fm_idl_url)
    tree = ElementTree.parse(f)
    f.close()
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
    url = '%s?%s' % (GATE, '&'.join(params)) # fixme, OSRF_HTTP, IDL_URL
    # print '--->', url
    req = urllib2.urlopen(url)
    resp = json.load(req)
    if resp['status'] != 200:
        raise Exception('error during evergren request', resp)
    payload = resp['payload']
    # print '<---', payload
    return evergreen_object(payload)

def evergreen_request_single_result(method, *args, **kwargs):
    resp = evergreen_request(method, *args, **kwargs)
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
