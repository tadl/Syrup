# startup ils tasks go here

import os

import oils.event
import oils.utils.idl
import oils.utils.utils
import osrf.gateway
import osrf.json
import sys
import tempfile
import urllib2

def load_idl(osrf_http, gateway_server, idl_url):
    """
    Loads the fieldmapper IDL, registering class hints for the defined objects

    We use a temporary file to store the IDL each time load_idl()
    is invoked to ensure that the IDL is in sync with the target
    server. One could a HEAD request to do some smarter caching,
    perhaps.
    """
    
    parser = oils.utils.idl.IDLParser()
    idlfile = tempfile.TemporaryFile()

    # Get the fm_IDL.xml file from the server
    try:
	print '%s://%s/%s' % (osrf_http, gateway_server, idl_url)
        idl = urllib2.urlopen('%s://%s/%s' % 
            (osrf_http, gateway_server, idl_url)
        )
        idlfile.write(idl.read())
        # rewind to the beginning of the file
        idlfile.seek(0)

    #no pass on these, updates are too critical to ever be out of sync
    except urllib2.URLError, exc:
        print("Could not open URL to read IDL: %s", exc.code)

    except IOError, exc:
        print("Could not write IDL to file: %s", exc.code)

    # parse the IDL
    parser.set_IDL(idlfile)
    parser.parse_IDL()

def ils_startup(EVERGREEN_GATEWAY_SERVER, OSRF_HTTP, IDL_URL):
    """
    Put any housekeeping for ILS interactions here, the definitions come from
    local_settings in the call itself rather than an import
    """
    	
    # Set the host for our requests
    osrf.gateway.GatewayRequest.setDefaultHost(EVERGREEN_GATEWAY_SERVER)

    # Pull all of our object definitions together
    load_idl(OSRF_HTTP, EVERGREEN_GATEWAY_SERVER, IDL_URL)
