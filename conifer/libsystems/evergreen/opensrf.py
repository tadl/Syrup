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
			return barcode_copy.circ_modifier(), barcode_copy.location().id(), call_num.label()
    except:
            print "problem retrieving item info"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production

    return None, None, None

def ils_patron_lookup(patron):
    """
    This is the barebones of a fuzzy lookup using opensrf
    """
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    out = []
    if len(patron) < settings.MIN_QUERY_LENGTH:
        return out
    is_barcode = re.search('\d{14}', patron)
    if not is_barcode and is_number(patron):
        return out
    is_email = False
    if patron.find('@') > 0:
        is_email = True

    try:
        query = None
        query1 = None
        query2 = None
        incoming = None

        if not is_barcode: 
            incoming = patron.split()
            query1 = incoming[0]

            if len(incoming) > 1:   
                #in case wild card searching can be used
                query2 = '%s' % incoming[1].strip()
                query = {'first_given_name':{'value':query1,'group':0},
                    'family_name':{'value':query2,'group':0}}
            else:
                query1 = '%s' % query1
                query = {'first_given_name':{'value':query1,'group':0}}
            
        authtoken = auth_token(settings.OPENSRF_STAFF_USERID, 
            settings.OPENSRF_STAFF_PW,
            settings.OPENSRF_STAFF_WORKSTATION)

        if auth_token:
            patron_info = []
            if not is_barcode and not is_email:
                req = request('open-ils.actor',
                    'open-ils.actor.patron.search.advanced',
                    authtoken, query)
                patron_info = req.send()
                if not patron_info and len(incoming) == 1:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'family_name':{'value':query1,'group':0},'profile':{'value':'11','group':0}})
                    patron_info = req.send()
            if is_email:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'email':{'value':query1,'group':0}})
                    patron_info = req.send()
            if is_barcode:
                    req = request('open-ils.actor',
                        'open-ils.actor.patron.search.advanced',
                        authtoken, {'card':{'value':patron.strip(),'group':3}})
                    patron_info = req.send()

            if patron_info:
                cnt = 0
                for patron in patron_info:
                    req = request('open-ils.actor',
                    'open-ils.actor.user.fleshed.retrieve',
                    authtoken, patron,
                    ["profile"])
                    ind_info = req.send()
                    profile = ind_info.profile()
                    profile_id = profile.id()

                    if int(profile_id) in settings.OPENSRF_PERMIT_GRPS:
                        cnt+=1
                        display = ('%s %s. %s, '
                        '%s. <%s>. [%s]') % (ind_info.first_given_name(),
                            ind_info.family_name(), 'Test', 'FACULTY/STAFF',
                            ind_info.email(), ind_info.usrname())
                        out.append((ind_info.usrname(), display))
                        if cnt == 5:
                            return out

            #clean up session
            session_cleanup(authtoken)
    except:
            print "item update problem"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production
            return out

    return out


def ils_item_update(barcode, callno, modifier, location):
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
            call_num.label(callno)
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
