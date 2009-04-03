# Our integration-point with back-end library systems.

# TODO: write some documentation about the lib_integration interface.

# Our example configuration: 
# Z39.50 for catalogue search, 
# SIP for patron and item_info, and for item checkout and checkin,
# OpenSRF for extended item info.

from conifer.libsystems.sip import sipclient


def patron_info(barcode):
    conn = sipclient.sip_connection()
    resp = sipclient.sip_connection().patron_info(barcode)
    conn.close()
    return resp

def item_info(barcode):
    conn = sipclient.sip_connection()
    resp = conn.item_info(barcode)
    conn.close()
    return resp

    


