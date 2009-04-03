from pprint import pprint
from sipclient import *

sip = SipClient('dwarf.cs.uoguelph.ca', 8080)
resp = sip.login(uid='sipclient',
                     pwd='c0n1fi3', locn='fawcett laptop')
pprint(resp)
pprint(sip.status())

pprint(sip.send(PATRON_INFO, PATRON_INFO_RESP,
                   {'patron':'21862000380830',
                    'startitem':1, 'enditem':2}))

pprint(sip.send(ITEM_INFORMATION, ITEM_INFO_RESP,
                          {'item': '31862017122801'}))
