# session-based opensrf calls go here

from conifer.libsystems import marcxml as M
from conifer.libsystems.evergreen import item_status as I
from conifer.libsystems.evergreen.support import initialize, E1
from datetime import date
from django.conf import settings
import hashlib
import os
import re
import traceback

def auth_token(username, password, org, workstation):
    try:
	authtoken = None
	payload = E1(settings.OPENSRF_AUTHENTICATE_INIT, username)
	pw = hashlib.md5(password).hexdigest()
	pw = hashlib.md5(payload + pw).hexdigest()
	authinfo = E1(settings.OPENSRF_AUTHENTICATE,{"password":pw, "type":"staff", 
		"org": org, "username":username,
		"workstation":workstation})
    	if authinfo:
    		payload = authinfo.get("payload")
    		authtoken = payload.get("authtoken")
    except:
	    print "authentication problem: ", username
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production 
    return authtoken

def session_cleanup(authtoken):
    try:
	payload = E1(settings.OPENSRF_CLEANUP, authtoken)
    except:
	    print "session problem: ", authtoken
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production 
        
    return True
