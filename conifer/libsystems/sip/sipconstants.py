# This is the work of David Fiander, from the openncip project. We
# have transformed it into a Python library. David's license appears
# below.

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

constants = [
    # Messages from SC to ACS
    ('PATRON_STATUS_REQ', '23'),
    ('CHECKOUT', '11'),
    ('CHECKIN', '09'),
    ('BLOCK_PATRON', '01'),
    ('SC_STATUS', '99'),
    ('REQUEST_ACS_RESEND', '97'),
    ('LOGIN', '93'),
    ('PATRON_INFO', '63'),
    ('END_PATRON_SESSION', '35'),
    ('FEE_PAID', '37'),
    ('ITEM_INFORMATION', '17'),
    ('ITEM_STATUS_UPDATE', '19'),
    ('PATRON_ENABLE', '25'),
    ('HOLD', '15'),
    ('RENEW', '29'),
    ('RENEW_ALL', '65'),
    
    # Message responses from ACS to SC
    ('PATRON_STATUS_RESP', '24'),
    ('CHECKOUT_RESP', '12'),
    ('CHECKIN_RESP', '10'),
    ('ACS_STATUS', '98'),
    ('REQUEST_SC_RESEND', '96'),
    ('LOGIN_RESP', '94'),
    ('PATRON_INFO_RESP', '64'),
    ('END_SESSION_RESP', '36'),
    ('FEE_PAID_RESP', '38'),
    ('ITEM_INFO_RESP', '18'),
    ('ITEM_STATUS_UPDATE_RESP', '20'),
    ('PATRON_ENABLE_RESP', '26'),
    ('HOLD_RESP', '16'),
    ('RENEW_RESP', '30'),
    ('RENEW_ALL_RESP', '66'),
    
    #
    # Some messages are short and invariant, so they're constant's too
    #
    ('REQUEST_ACS_RESEND_CKSUM', '97AZFEF5'),
    ('REQUEST_SC_RESEND_CKSUM', '96AZFEF6'),
    
    #
    # Field Identifiers
    #
    ('FID_PATRON_ID', 'AA'),
    ('FID_ITEM_ID', 'AB'),
    ('FID_TERMINAL_PWD', 'AC'),
    ('FID_PATRON_PWD', 'AD'),
    ('FID_PERSONAL_NAME', 'AE'),
    ('FID_SCREEN_MSG', 'AF'),
    ('FID_PRINT_LINE', 'AG'),
    ('FID_DUE_DATE', 'AH'),
    # UNUSED AI
    ('FID_TITLE_ID', 'AJ'),
    # UNUSED AK
    ('FID_BLOCKED_CARD_MSG', 'AL'),
    ('FID_LIBRARY_NAME', 'AM'),
    ('FID_TERMINAL_LOCN', 'AN'),
    ('FID_INST_ID', 'AO'),
    ('FID_CURRENT_LOCN', 'AP'),
    ('FID_PERM_LOCN', 'AQ'),
    ('FID_HOME_LIBRARY', 'AQ'), # Extension: AQ in patron info
    # UNUSED AR
    ('FID_HOLD_ITEMS', 'AS'), # SIP 2.0
    ('FID_OVERDUE_ITEMS', 'AT'), # SIP 2.0
    ('FID_CHARGED_ITEMS', 'AU'), # SIP 2.0
    ('FID_FINE_ITEMS', 'AV'), # SIP 2.0
    # UNUSED AW
    # UNUSED AX
    ('FID_SEQNO', 'AY'),
    ('FID_CKSUM', 'AZ'),
    
    # SIP 2.0 Fields
    # UNUSED BA
    # UNUSED BB
    # UNUSED BC
    ('FID_HOME_ADDR', 'BD'),
    ('FID_EMAIL', 'BE'),
    ('FID_HOME_PHONE', 'BF'),
    ('FID_OWNER', 'BG'),
    ('FID_CURRENCY', 'BH'),
    ('FID_CANCEL', 'BI'),
    # UNUSED BJ
    ('FID_TRANSACTION_ID', 'BK'),
    ('FID_VALID_PATRON', 'BL'),
    ('FID_RENEWED_ITEMS', 'BM'),
    ('FID_UNRENEWED_ITEMS', 'BN'),
    ('FID_FEE_ACK', 'BO'),
    ('FID_START_ITEM', 'BP'),
    ('FID_END_ITEM', 'BQ'),
    ('FID_QUEUE_POS', 'BR'),
    ('FID_PICKUP_LOCN', 'BS'),
    ('FID_FEE_TYPE', 'BT'),
    ('FID_RECALL_ITEMS', 'BU'),
    ('FID_FEE_AMT', 'BV'),
    ('FID_EXPIRATION', 'BW'),
    ('FID_SUPPORTED_MSGS', 'BX'),
    ('FID_HOLD_TYPE', 'BY'),
    ('FID_HOLD_ITEMS_LMT', 'BZ'),
    ('FID_OVERDUE_ITEMS_LMT', 'CA'),
    ('FID_CHARGED_ITEMS_LMT', 'CB'),
    ('FID_FEE_LMT', 'CC'),
    ('FID_UNAVAILABLE_HOLD_ITEMS', 'CD'),
    # UNUSED CE
    ('FID_HOLD_QUEUE_LEN', 'CF'),
    ('FID_FEE_ID', 'CG'),
    ('FID_ITEM_PROPS', 'CH'),
    ('FID_SECURITY_INHIBIT', 'CI'),
    ('FID_RECALL_DATE', 'CJ'),
    ('FID_MEDIA_TYPE', 'CK'),
    ('FID_SORT_BIN', 'CL'),
    ('FID_HOLD_PICKUP_DATE', 'CM'),
    ('FID_LOGIN_UID', 'CN'),
    ('FID_LOGIN_PWD', 'CO'),
    ('FID_LOCATION_CODE', 'CP'),
    ('FID_VALID_PATRON_PWD', 'CQ'),
    
    # SIP Extensions used by Envisionware Terminals
    ('FID_PATRON_BIRTHDATE', 'PB'),
    ('FID_PATRON_CLASS', 'PC'),
    
    # SIP Extension for reporting patron internet privileges
    ('FID_INET_PROFILE', 'PI'),
    
    #
    # SC Status Codes
    #
    ('SC_STATUS_OK', '0'),
    ('SC_STATUS_PAPER', '1'),
    ('SC_STATUS_SHUTDOWN', '2'),
    
    #
    # Various format strings
    #
    ('SIP_DATETIME', "%Y%m%d    %H%M%S"),
]

# make them toplevel variables.
for k,v in constants:
    locals()[k] = v

def lookup_constant(x):
    for k, v in constants:
        if v == x:
            return k
