# Small portions are borrowed from David Fiander's acstest.py, in the
# openncip project. David's license is below:

# Copyright (C) 2006-2008  Georgia Public Library Service
# 
# Author: David J. Fiander
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 2 of the GNU General Public
# License as published by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307 USA


from sipconstants import *
import socket
import sys
from datetime import datetime
import re

DEBUG = True

# ------------------------------------------------------------
# helper functions

def split_n(n):
    """Return a function that splits a string into two parts at index N."""
    return lambda s: (s[:n], s[n:])

split2 = split_n(2)




# ------------------------------------------------------------
# Messages

# First we build up a little language for defining SIP messages, so
# that we can define the protocol in a declarative style.


class basefield(object): 

    def encode(self, dct):
        """Take a dict, and return the wire representation of this field."""
        raise NotImplementedError, repr(self)

    def decode(self, bytes):
        """
        Take a wire representation and return a pair (V,R) where V is
        the translated value of the current field, and R is the
        remaining bytes after the field has been read. If this is an
        optional field, then decode should return None for V, and
        return the input bytes for R.
        """
        raise NotImplementedError, repr(self)


class field(basefield):

    def __init__(self, name, code, width=None):
        self.name = name 
        self.code = code
        self.width = None       # don't use this yet.

    def encode(self, dct):
        return '%s%s|' % (self.code, dct.get(self.name, ''))

    def decode(self, bytes):
        bcode, rest = split2(bytes)
        if bcode != self.code:
            raise 'BadDecode', \
                'Wrong field! Expected %r (%s) got %r (%s), in %r.' % (
                    self.code, lookup_constant(self.code),
                    bcode, lookup_constant(bcode),
                    bytes)
        data, rest = rest.split('|', 1)
        return data, rest


class optfield(field):          # an optional field

    def decode(self, bytes):
        tmp = bytes + '  '
        bcode, rest = split2(tmp)
        if bcode == self.code:
            return field.decode(self, bytes)
        else:
            return None, bytes

        
class charfield(basefield):

    def __init__(self, name, width=None, default=None):
        self.name = name
        self.dflt = str(default)
        self.width = width or len(self.dflt) # give at least one
        self.pad = ' ' * self.width

        self.decode = split_n(self.width)

    def encode(self, dct):
        v = dct.get(self.name, self.dflt)
        assert v is not None
        return ('%s%s' % (self.pad, v))[-self.width:]


class yn(basefield):
    def __init__(self, name):
        self.name = name

    def encode(self, dct):
        return 'NY'[bool(dct.get(self.name))]

    def decode(self, bytes):
        return (bytes[0] == 'Y'), bytes[1:]


class localtime(charfield):
    def __init__(self, name):
        self.name = name
        self.width = 18

    def encode(self, dct):
        return datetime.now().strftime('%Y%m%d    %H%M%S')

    def decode(self, bytes):
        return split_n(self.width)(bytes)

RAW = -55
class raw(basefield):
    name = 'raw'
    # for debugging.
    def decode(self, bytes):
        return bytes, '\r'

# We define a protocol Message as a list of fields. For now,
# message(A, B, C) is equivalent to the tuple (A,B,C).

message = lambda *args: args

# Encoding a message on to the wire. Args is a dict of field-values.

def encode_msg(msg, args):
    out = []
    add = out.append
    for thing in msg:
        if isinstance(thing, basefield):
            add(thing.encode(args))
        else:
            add(str(thing))
    return ''.join(out)

# Decoding from the wire:

def decode_msg(msg, bytes):
    out = {}
    add = out.__setitem__
    rest = bytes
    
    # Proper 'fields' have variable position in the tail of the
    # message. So we treat them differently.
    varposn = set([p for p in msg if isinstance(p, field)])
    varlookup = dict((x.code, x) for x in varposn)
    fixedposn = [p for p in msg if not p in varposn]
    
    for part in fixedposn:
        if isinstance(part, basefield):
            good, rest = part.decode(rest)
            if good is not None:
                add(part.name, good)
        else:
            v = str(part)
            good, rest = rest[:len(v)], rest[len(v):]
            assert v == good
        if DEBUG: print '%s == %r\n==== %r' % (getattr(part, 'name',''), good, rest)

    # Now we take what's left, chunk it, and try to resolve each one
    # against a variable-position field.
    segments = re.findall(r'(.*?\|)', rest)
    
    if DEBUG: print segments

    for segment in segments:
        fld = varlookup.get(segment[:2])
        if fld:
            good, rest = fld.decode(segment)
            add(fld.name, good)
            varposn.remove(fld)
        else:
            raise 'FieldNotProcessed: %s, %s' % (segment, lookup_constant(segment[:2]))

    # Let's make sure that any "required" fields were not missing.
    notpresent = set(f for f in varposn if not isinstance(f, optfield))
    if notpresent:
        for f in notpresent:
            print 'MISSING: %-12s %s %s' % (f.name, f.code, lookup_constant(f.code))
        raise 'MandatoryFieldsNotPresent'

    return out

# The SIP checksum. Borrowed from djfiander.        

def checksum(msg):
    return '%04X' % ((0 - sum(map(ord, msg))) & 0xFFFF)


#------------------------------------------------------------
# SIP Message Definitions

# some common fields


fld_localtime     = localtime('localtime')
fld_INST_ID       = field('inst', FID_INST_ID)
fld_ITEM_ID       = field('item', FID_ITEM_ID)
fld_PATRON_ID     = field('patron', FID_PATRON_ID)
ofld_TERMINAL_PWD = optfield('termpwd', FID_TERMINAL_PWD)
fld_proto_version = charfield('version', default='2.00')
ofld_print_line    = optfield('print_line', FID_PRINT_LINE)
ofld_screen_msg    = optfield('screenmsg', FID_SCREEN_MSG)

MESSAGES = {
    LOGIN : message(
            LOGIN, 
            '00',
            field('uid', FID_LOGIN_UID),
            field('pwd', FID_LOGIN_PWD),
            field('locn', FID_LOCATION_CODE)),

    LOGIN_RESP : message(
            LOGIN_RESP, 
            charfield('ok', width=1)),

    SC_STATUS : message(
            SC_STATUS, 
            charfield('online', default='1'),
            charfield('width', default='040'),
            fld_proto_version),

    ACS_STATUS : message(
            ACS_STATUS,
            yn('online'),
            yn('checkin_OK'),
            yn('checkout_OK'),
            yn('renewal_OK'),
            yn('status_update_OK'),
            yn('offline_OK'),
            charfield('timeout', default='01'),
            charfield('retries', default='9999'),
            fld_localtime,
            charfield('protocol', default='2.00'),
            fld_INST_ID,
            optfield('patron_id', FID_PATRON_ID),
            optfield('item_id', FID_ITEM_ID),
            optfield('terminal_pwd', FID_TERMINAL_PWD),
            
            optfield('instname', FID_LIBRARY_NAME),
            field('supported', FID_SUPPORTED_MSGS),
            optfield('ttylocn', FID_TERMINAL_LOCN),
            ofld_screen_msg,
            ofld_print_line),
    PATRON_INFO : message(
            PATRON_INFO,
            charfield('lang', width=3, default=1),
            fld_localtime,
            charfield('holditemsreq', default='Y         '),
            fld_INST_ID,
            fld_PATRON_ID,
            ofld_TERMINAL_PWD,
            optfield('patronpwd', FID_PATRON_PWD),
            optfield('startitem', FID_START_ITEM, width=5),
            optfield('enditem', FID_END_ITEM, width=5)),
            
    PATRON_INFO_RESP : message(
            PATRON_INFO_RESP,
            charfield('hmmm', width=14),
            charfield('lang', width=3, default=1),
            fld_localtime,
            charfield('onhold', width=4),
            charfield('overdue', width=4),
            charfield('charged', width=4),
            charfield('fine', width=4),
            charfield('recall', width=4),
            charfield('unavail_holds', width=4),
            fld_INST_ID,
            ofld_screen_msg,
            ofld_print_line,
            optfield('instname', FID_LIBRARY_NAME),
            fld_PATRON_ID,
            field('personal', FID_PERSONAL_NAME),

            optfield('hold_limit', FID_HOLD_ITEMS_LMT, width=4),
            optfield('overdue_limit', FID_OVERDUE_ITEMS_LMT, width=4),
            optfield('charged_limit', FID_OVERDUE_ITEMS_LMT, width=4),

            optfield('hold_items', FID_HOLD_ITEMS),
            optfield('valid_patron_pwd', FID_VALID_PATRON_PWD),
            
            optfield('valid_patron', FID_VALID_PATRON),
            optfield('currency', FID_CURRENCY),
            optfield('fee_amt', FID_FEE_AMT),
            optfield('fee_limit', FID_FEE_LMT),
            optfield('home_addr', FID_HOME_ADDR),
            optfield('email', FID_EMAIL),
            optfield('home_phone', FID_HOME_PHONE),
            optfield('patron_birthdate', FID_PATRON_BIRTHDATE),
            optfield('patron_class', FID_PATRON_CLASS),
            optfield('inet_profile', FID_INET_PROFILE),
            optfield('home_library', FID_HOME_LIBRARY)),

    END_PATRON_SESSION : message(
            END_PATRON_SESSION,
            fld_localtime,
            field('inst', FID_INST_ID),
            field('patron', FID_PATRON_ID)),

    END_SESSION_RESP : message(
            END_SESSION_RESP,
            yn('session_ended'),
            fld_localtime,
            fld_INST_ID,
            fld_PATRON_ID,
            ofld_print_line,
            ofld_screen_msg),

    CHECKOUT: message(
        CHECKOUT,
        yn('renewals_OK'),
        yn('no_block'),
        fld_localtime,
        fld_localtime,
        field('inst', FID_INST_ID),
        field('patron', FID_PATRON_ID),
        field('item', FID_ITEM_ID),
        ),

    CHECKOUT_RESP: message(
        CHECKOUT_RESP,
        charfield('ok', width=1),
        yn('is_renewal'),
        yn('is_magnetic'),
        yn('desensitize'),
        fld_localtime,
        field('inst', FID_INST_ID),
        field('patron', FID_PATRON_ID),
        field('item', FID_ITEM_ID),
        field('due', FID_DUE_DATE),
        field('title', FID_TITLE_ID),
        optfield('media_type_code', FID_MEDIA_TYPE),
        optfield('is_valid_patron', FID_VALID_PATRON),
        ofld_print_line,
        ofld_screen_msg),

    CHECKIN: message(
        CHECKIN,
        yn('is_retry'),
        fld_localtime,
        fld_localtime,
        field('item', FID_ITEM_ID),
        field('location', FID_CURRENT_LOCN),
        field('inst', FID_INST_ID),
        ofld_TERMINAL_PWD,
        ),

    CHECKIN_RESP: message(
        CHECKIN_RESP,
        charfield('ok', width=1),
        yn('resensitize'),
        yn('is_magnetic'),
        yn('alert'),
        fld_localtime,
        fld_INST_ID,
        optfield('patron', FID_PATRON_ID),
        field('item', FID_ITEM_ID),
        field('title', FID_TITLE_ID),
        optfield('media_type_code', FID_MEDIA_TYPE),
        optfield('perm_locn', FID_PERM_LOCN),
        optfield('due', FID_DUE_DATE),
        ofld_print_line,
        ofld_screen_msg,
        ),
#         yn('is_retry'),
#         fld_localtime,
#         fld_localtime,
#         field('item', FID_ITEM_ID),
#         field('location', FID_CURRENT_LOCN),
#         ofld_TERMINAL_PWD,
#        ),

    ITEM_INFORMATION : message(
            ITEM_INFORMATION,
            fld_localtime,
            fld_INST_ID,
            fld_ITEM_ID,
            ofld_TERMINAL_PWD),

    ITEM_INFO_RESP : message(
            ITEM_INFO_RESP,
            charfield('circstat', width=2),
            charfield('security', width=2),
            charfield('feetype', width=2),
            fld_localtime,
            fld_ITEM_ID,
            field('title', FID_TITLE_ID),
            optfield('mediatype', FID_MEDIA_TYPE),
            optfield('perm_locn', FID_PERM_LOCN),
            optfield('current_locn', FID_CURRENT_LOCN),
            optfield('item_props', FID_ITEM_PROPS),
            optfield('currency', FID_CURRENCY),
            optfield('fee', FID_FEE_AMT),
            optfield('owner', FID_OWNER),
            optfield('hold_queue_len', FID_HOLD_QUEUE_LEN),
            optfield('due_date', FID_DUE_DATE),

            optfield('recall_date', FID_RECALL_DATE),
            optfield('hold_pickup_date', FID_HOLD_PICKUP_DATE),
            ofld_screen_msg,
            ofld_print_line),
            
    RAW : message(raw()),
}


class SipClient(object):
    def __init__(self, host, port, error_detect=False):
        self.hostport = (host, port)
        self.error_detect = error_detect
        self.connect()

    def connect(self):
        so = socket.socket()
        so.connect(self.hostport)
        self.socket = so
        self.seqno = self.error_detect and 1 or 0

    def close(self):
        # fixme, do SIP close first.
        self.socket.close()

    def send(self, outmsg, inmsg, args=None):
        msg_template = MESSAGES[outmsg]
        resp_template = MESSAGES[inmsg]
        msg = encode_msg(msg_template, args or {})
        if self.error_detect:
            # add the checksum
            msg += 'AY%dAZ' % (self.seqno % 10)
            self.seqno += 1
            msg += checksum(msg)
        msg += '\r'
        if DEBUG: print '>>> %r' % msg
        self.socket.send(msg)
        resp = self.socket.recv(1000)
        if DEBUG: print '<<< %r' % resp
        return decode_msg(resp_template, resp)
        

    # --------------------------------------------------
    # Common protocol methods

    def login(self, uid, pwd, locn):
        msg = self.send(LOGIN, LOGIN_RESP, 
                        dict(uid=uid, pwd=pwd, locn=locn))
        return msg.get('ok') == '1'

    def status(self):
        return self.send(SC_STATUS, ACS_STATUS)

    def patron_info(self, barcode):
        msg = self.send(PATRON_INFO,PATRON_INFO_RESP,
                        {'patron':barcode,
                         'startitem':1, 'enditem':2})
        return msg

    def checkout(self, patron, item, inst=''):
        msg = self.send(CHECKOUT, CHECKOUT_RESP,
                        {'patron':patron,
                         'inst': inst,
                         'item':item})
        msg['media_type'] = MEDIA_TYPE_TABLE.get(msg.get('media_type_code'))
        msg['success'] = msg.get('ok') == '1'
        return msg

    def checkin(self, item, institution='', location=''):
        msg = self.send(CHECKIN, CHECKIN_RESP,
                        {'inst': institution,
                         'location':location,
                         'is_retry':False,
                         'item':item})
        msg['success'] = msg.get('ok') == '1'
        return msg

    def item_info(self, barcode):
        msg = self.send(ITEM_INFORMATION, ITEM_INFO_RESP,
                        {'item':barcode})
        msg['available'] = msg['circstat'] == '03'
        msg['status'] = ITEM_STATUS_TABLE[msg['circstat']]
        return msg


# ------------------------------------------------------------
# Django stuff. Optional.

try:
    from django.conf import settings
    def sip_connection():
        sip = SipClient(*settings.SIP_HOST)
        if not sip.login(*settings.SIP_CREDENTIALS):
            raise 'SipLoginError'
        return sip

    # decorator
    def SIP(fn):
        def f(*args, **kwargs):
            conn = sip_connection()
            resp = fn(conn, *args, **kwargs)
            conn.close()
            return resp
        return f

except ImportError:
    pass


# ------------------------------------------------------------
# Test code.

if __name__ == '__main__':
    from pprint import pprint

    sip = SipClient('home', 6001)
    resp = sip.login(uid='scclient',
                     pwd='clientpwd', locn='The basement')
    pprint(resp)
    pprint(sip.status())

    pprint(sip.send(PATRON_INFO, PATRON_INFO_RESP,
                   {'patron':'scclient',
                    'startitem':1, 'enditem':2}))

    # these are items from openncip's test database.
    item_ids = ['1565921879', '0440242746', '660']
    bad_ids = ['xx' + i for i in item_ids]
    for item in (item_ids + bad_ids):
        result = sip.send(ITEM_INFORMATION, ITEM_INFO_RESP,
                          {'item':item})
        print '%-12s: %s' % (item, result['title'] or '????')
        print sip.send(CHECKOUT, RAW,
                       {'patron':'scclient-2',
                        'inst': 'UWOLS',
                        'item':item})
        print '\n' * 5
    pprint(sip.send(END_PATRON_SESSION, END_SESSION_RESP,
                   {'patron':'scclient',
                    'inst':'UWOLS'}))


