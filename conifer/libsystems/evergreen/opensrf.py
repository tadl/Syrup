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
            return None

    return authtoken

def session_cleanup(authtoken):
    try:
	payload = E1(settings.OPENSRF_CLEANUP, authtoken)
    except:
	    print "session problem: ", authtoken
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production 
            return None
        
    return True

def evergreen_item_update(barcode, callno, modifier, desk):
    try:
        token = auth_token(settings.OPENSRF_STAFF_USERID, settings.OPENSRF_STAFF_PW,
                settings.OPENSRF_STAFF_ORG, settings.OPENSRF_STAFF_WORKSTATION)

        null = None
        true = True
        false = False
        barcode_copy = E1(settings.OPENSRF_CN_BARCODE, token, barcode);

        copy = None
        volumeinfo = None

        if barcode_copy:
                volumeinfo = barcode_copy.get("volume")
                if volumeinfo:
                        volume = volumeinfo['__p']
                        if volume and volume[7] != callno:
                                volume[0] = []
                                volume[7] = str(callno)
				vol_len = len(volume) - 1
				volume[vol_len] = str(volume[vol_len])
				# ok, this is bad, need to find what these values are
				for i in range(0, 4):
                                	volume.append(None)
                                volume.append('1')
                                # print "volume", volume
                                updaterec = E1(settings.OPENSRF_VOLUME_UPDATE,
                                        token, [{"__c":"acn","__p":volume}], false,
                                        {"auto_merge_vols":false})
				# print "update", updaterec
                copy = barcode_copy.get("copy")
                if copy:
                        # print "copy", copy
                        detailid = copy['__p'][21]
                        details = E1(settings.OPENSRF_FLESHEDCOPY_CALL, [detailid])
                        if details and (details[0]['__p'][7] != modifier or details[0]['__p'][23] != desk):
                                details[0]['__p'][7] = str(modifier)
                                details[0]['__p'][23] = str(desk)
				# ditto here too, need to find what these values are
				for i in range(0, 6):
                                	details[0]['__p'].append(None)
                                details[0]['__p'].append('1')

                                print "details", details
                                updaterec = E1(settings.OPENSRF_BATCH_UPDATE, token, details,true)
                                # print "updaterec", updaterec

        session_cleanup(token)
    except:
            print "item update problem"
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production
            return False

    return True
