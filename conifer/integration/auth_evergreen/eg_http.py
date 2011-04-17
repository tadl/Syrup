# auth_evergreen_support -- Authentication and user lookup against an
# Evergreen XML-RPC server.

# This is the Evergreen-specific stuff, with no Django dependencies.

from hashlib import md5
import warnings
import time
from conifer.libsystems.evergreen.support import ER, E1, initialize
import re

#----------------------------------------------------------------------
# support

def _hsh(s):
    return md5(s).hexdigest()

#----------------------------------------------------------------------
# main interface

class EvergreenAuthServer(object):

    def __init__(self):
        pass

    def login(self, username, password, workstation='OWA-proxyloc'): # fixme!
        """Return True if the username/password are good, False otherwise."""

        seed = E1('open-ils.auth.authenticate.init', username)

        result = E1('open-ils.auth.authenticate.complete', {
                'workstation' : workstation,
                'username' : username,
                'password' : _hsh(seed + _hsh(password)),
                'type' : 'staff' 
                })
        try:
            authkey = result['payload']['authtoken']
            return authkey
        except:
            return None

    def djangoize_username(self, username):
        """
        Transform username so it is valid as a Django username. For Django
        1.2, only [a-zA-Z0-9_] are allowed in userids.
        """
        pat = re.compile('[^a-zA-Z0-9_]+')
        return pat.sub('_', username)

    def lookup(self, username, login_token=None):
        """Given a username, return a dict, or None. The dict must have
        four keys (first_name, last_name, email, external_username), where
        external_username value is the username parameter."""

        # for now, this backend only returns a user if a login_token is
        # provided; in other words, the only time your personal info is
        # fetched is when you log in.
        if login_token:
            resp = E1('open-ils.auth.session.retrieve', login_token)
            person = dict((j, resp.get(k)) 
                          for j,k in [('first_name', 'first_given_name'),
                                      ('last_name', 'family_name'),
                                      ('email', 'email'),
                                      ('external_username', 'usrname')])
            return person

