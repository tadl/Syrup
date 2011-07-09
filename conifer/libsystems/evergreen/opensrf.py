# session-based opensrf calls go here
# thanks to dan scott for sorting out the python integration

from datetime import date
from django.conf import settings
import os
import re
import traceback

import oils.event
import oils.utils.idl
import oils.utils.utils
import osrf.gateway
import osrf.json
import sys
import tempfile
import urllib2

class AuthException(Exception):
    """
    Exceptions for authentication events
    """

    def __init__(self, msg=''):
        """
        Initialize the authentication exception
        """
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        """
        Stringify the authentication exception
        """
        return 'AuthException: %s' % self.msg

def auth_token(username, password, workstation):
    authtoken = None
    seed = request('open-ils.auth', 
	    'open-ils.auth.authenticate.init', username).send()

    # generate the hashed password
    password = oils.utils.utils.md5sum(seed + oils.utils.utils.md5sum(password))
	
    result = request('open-ils.auth',
	    'open-ils.auth.authenticate.complete', {
	    'workstation' : workstation,
	    'username' : username,
	    'password' : password,
	    'type' : 'staff' 
	    }).send()
	
    evt = oils.event.Event.parse_event(result)
    if evt and not evt.success:
        print "authentication problem: ", AuthException(evt.text_code)
        return None

    authtoken = result['payload']['authtoken']
    return authtoken

def session_cleanup(authtoken):
    try:
    	result = request('open-ils.auth', 
		    'open-ils.auth.session.delete', authtoken).send()
    except:
	    print "session problem: ", authtoken
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production 
            return None
        
    return True

def request(service, method, *args):
    """
    Make a JSON request to the OpenSRF gateway

    This is as simple as it gets. Atomic requests will require a bit
    more effort.
    """

    req = osrf.gateway.JSONGatewayRequest(service, method, *args)

    # The gateway URL ensures we're using JSON v1, not v0
    req.setPath(settings.GATEWAY_URL)
    return req

def ils_item_info(barcode):
    """
    We store some item information with syrup record 
    """
    try:
    	req = request('open-ils.search',
		'open-ils.search.asset.copy.fleshed2.find_by_barcode',
		barcode)
    	barcode_copy = req.send()
        # print "debug", osrf.json.debug_net_object(barcode_copy)

    	if barcode_copy:
        	req = request('open-ils.search', 
			'open-ils.search.asset.call_number.retrieve',
                	barcode_copy.call_number())
   
        	call_num = req.send()
		if call_num:
			print "req", call_num
			print "label", call_num.label()
			print "prefix", call_num.prefix()
			print "suffix", call_num.suffix()
			return barcode_copy.circ_modifier(), barcode_copy.location().id(), call_num.prefix(), call_num.label(), call_num.suffix()
    except:
            print "problem retrieving item info"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production

    return None, None, None

def ils_patron_details(usrname):
    dir_entry = {}

    try:
        authtoken = auth_token(settings.OPENSRF_STAFF_USERID, 
            settings.OPENSRF_STAFF_PW,
            settings.OPENSRF_STAFF_WORKSTATION)

        if auth_token:
            patrons = []
            req = request('open-ils.actor',
                'open-ils.actor.patron.search.advanced',
                authtoken, {'usrname':{'value':usrname.strip(),'group':0}})
            patron_info = req.send()
            if patron_info:
                patrons = patron_info
            for patron in patrons[0:1]:
                req = request('open-ils.actor',
                    'open-ils.actor.user.fleshed.retrieve',
                    authtoken, patron,
                    ["first_given_name","family_name","email","cards"])
                patron_info = req.send()
                if patron_info:
                    given_name = ""
                    if patron_info.first_given_name():
                        given_name = patron_info.first_given_name()
                    dir_entry['given_name'] = given_name
                    surname = ""
                    if patron_info.family_name():
                        surname = patron_info.family_name()
                    dir_entry['surname'] = surname
                    email = ""
                    if patron_info.email():
                        dir_entry['email'] = email

                    cards = patron_info.cards()
                    if cards:
                        barcode = None
                        for card in cards:
                            barcode = card.barcode()
                            dir_entry['barcode'] = barcode
                        
            #clean up session
            session_cleanup(authtoken)
    except:
            print "item update problem"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production

    return dir_entry

def ils_patron_lookup(name, is_staff=True, is_usrname=False, is_everyone=False):
    """
    This is an implementation of a fuzzy lookup using opensrf
    """
    RESULT_LIMIT  = 5

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def group_search(q,token,patrons):
        my_q = q
        my_patrons = []
        for group in settings.OPENSRF_PERMIT_GRPS:
            my_q['profile'] = {'value':group,'group':0}
            req = request('open-ils.actor',
                'open-ils.actor.patron.search.advanced',
                    token, my_q)
            patron_info = req.send()
            if patron_info: 
                my_patrons.extend(patron_info)
                if len(my_patrons) + len(patrons) > RESULT_LIMIT:
                    break
        my_patrons.extend(patrons)
        return my_patrons

    out = []
    if len(name) < settings.MIN_QUERY_LENGTH:
        return out
    is_barcode = re.search('\d{14}', name)
    if not is_barcode and is_number(name):
        return out
    is_email = False
    if not is_usrname and name.find('@') > 0:
        is_email = True

    try:
        query = None
        default_query = None
        query1 = None
        query2 = None
        incoming = None

        if not is_barcode: 
            incoming = name.split()
            query1 = incoming[0]

            if len(incoming) > 1:   
                query2 = incoming[1].strip()
                query = {'first_given_name':{'value':query1,'group':0},
                    'family_name':{'value':query2,'group':0}}
            else:
                query = {'first_given_name':{'value':query1,'group':0}}
                default_query = {'family_name':{'value':query1,'group':0}}
            
        authtoken = auth_token(settings.OPENSRF_STAFF_USERID, 
            settings.OPENSRF_STAFF_PW,
            settings.OPENSRF_STAFF_WORKSTATION)

        if auth_token:

            patrons = []
            if is_barcode:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'card':{'value':name.strip(),'group':3}})
                    patrons = req.send()
            elif is_usrname:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'usrname':{'value':name.strip(),'group':0}})
                    patron_info = req.send()
                    if patron_info:
                        patrons = patron_info
            elif is_staff:
                patrons.extend(group_search(query,authtoken,patrons))
                if (len(patrons) < RESULT_LIMIT and default_query):
                    more_patrons = group_search(default_query,
                        authtoken,patrons)
                    patrons.extend(more_patrons)
            elif is_email:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'email':{'value':name.strip(),'group':0}})
                    patron_info = req.send()
                    if patron_info:
                        patrons = patron_info
            else:
                req = request('open-ils.actor',
                    'open-ils.actor.patron.search.advanced',
                        authtoken, query)
                patron_info = req.send()
                if patron_info:
                    patrons = patron_info
                if (len(patrons) < RESULT_LIMIT and default_query):
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, default_query)
                    patron_info = req.send()
                    if patron_info:
                        patrons.extend(patron_info)
                
            for patron in patrons[0:RESULT_LIMIT]:
                req = request('open-ils.actor',
                    'open-ils.actor.user.fleshed.retrieve',
                        authtoken, patron,
                        ["first_given_name","family_name","email","usrname"])
                patron_info = req.send()
                if patron_info.usrname():
                    display = ('%s %s, '
                        '<%s>. [%s]') % (patron_info.first_given_name(),
                        patron_info.family_name(),
                        patron_info.email(), 
                        patron_info.usrname())
                    out.append((patron_info.usrname(), display))
                        
            #clean up session
            session_cleanup(authtoken)
    except:
            print "item update problem"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production
            return out

    return out


def ils_item_update(barcode, prefix, callno, suffix, modifier, location):
    item_changed = False
    callno_changed = False

    try:
    	# We get our copy object
        req = request('open-ils.search', 
            'open-ils.search.asset.copy.fleshed2.find_by_barcode', 
            barcode)
    	barcode_copy = req.send()

        # are there changes?
        if barcode_copy.location().id != location or barcode_copy.circ_modifier() != modifier:
            item_changed = True 

    	# And our call number object
        req = request('open-ils.search', 
		    'open-ils.search.asset.call_number.retrieve', 
            barcode_copy.call_number())
        call_num = req.send()

	    # are there changes?
        if call_num.label() != callno:
            callno_changed = True

	    # there might be nothing to do
	    if not item_changed and not callno_changed:
		    return True
		
	    # ok, we are going to update, first we authenticate
        authtoken = auth_token(settings.OPENSRF_STAFF_USERID, 
		    settings.OPENSRF_STAFF_PW,
            settings.OPENSRF_STAFF_WORKSTATION)

	    # item changes first, location and circ modifier
        if authtoken and item_changed:
            barcode_copy.location().id(location)
            barcode_copy.circ_modifier(modifier)
            barcode_copy.ischanged(True)

            acp = [barcode_copy]
            req = request('open-ils.cat', 
                'open-ils.cat.asset.copy.fleshed.batch.update',
                authtoken, acp, False, None)
            result = req.send()
		
            # print "item result", result

	        
        # on to call number
        if authtoken and callno_changed:
            call_num.prefix(prefix)
            call_num.label(callno)
            call_num.suffix(suffix)
            call_num.ischanged(True)

            # volume.fleshed.batch.update expects an array of call number objects 
            acn = [call_num]
            req = request('open-ils.cat', 
                'open-ils.cat.asset.volume.fleshed.batch.update', 
                authtoken, acn, False, None)
		
            result = req.send()
            # print "callno result", result
        
            #clean up session
            session_cleanup(authtoken)
    except:
            print "item update problem"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production
            return False

    return True
