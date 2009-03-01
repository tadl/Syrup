# auth_evergreen_support -- Authentication and user lookup against an
# Evergreen XML-RPC server.

# This is the Evergreen-specific stuff, with no Django dependencies.

import xmlrpclib
import md5
import warnings
import time

#----------------------------------------------------------------------
# support

def do_request(proxy, method, *args):
    # Against my test server, I would get intermittent
    # ProtcolErrors. If we get one, try again, backing off gradually.
    for attempt in range(5):
        try:
            return getattr(proxy, method)(*args)
        except xmlrpclib.ProtocolError, pe:
            warnings.warn('open-ils xml-rpc protocol error: trying again: ' + method)
            time.sleep(0.1 * attempt)       # back off a bit and try again

def _hsh(s):
    return md5.new(s).hexdigest()

#----------------------------------------------------------------------
# main interface

class EvergreenAuthServer(object):

    def __init__(self, address, verbose=False):
        self.address = address
        self.verbose = verbose

    def proxy(self, service):
        server = xmlrpclib.Server(
            'http://%s/xml-rpc/%s' % (self.address, service),
            verbose=self.verbose)
        def req(method, *args):
            return do_request(server, method, *args)
        return req

    def login(self, username, password):
        """Return True if the username/password are good, False otherwise."""
        prx = self.proxy('open-ils.auth')
        seed = prx('open-ils.auth.authenticate.init', username)
        resp = prx('open-ils.auth.authenticate.complete',
                   dict(username=username,
                        password=_hsh(seed + _hsh(password)), 
                        type='reserves'))
        try:
            # do we need the authkey for anything?
            authkey = resp['payload']['authtoken']
            return True
        except KeyError:
            return False

    def lookup(self, username):
        """Given a username, return a dict, or None. The dict must have
        four keys (first_name, last_name, email, external_username), where
        external_username value is the username parameter."""

        prx = self.proxy('open-ils.actor')
        r = prx('open-ils.actor.user.search.username', 'admin')
        if not r:
            return None
        else:
            r = r[0]['__data__']
            f = lambda k: r.get(k)
            person = dict((j, f(k)) for j,k in [('first_name', 'first_given_name'),
                                                ('last_name', 'family_name'),
                                                ('email', 'email'),
                                                ('external_username', 'usrname')])
            return person

#----------------------------------------------------------------------
# testing

if __name__ == '__main__':
    from pprint import pprint
    address = '192.168.1.10'
    egreen = EvergreenAuthServer(address)
    username, password = 'admin', 'open-ils'
    print egreen.login(username, password)
    pprint(egreen.lookup('admin'))
