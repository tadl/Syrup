from conifer.plumbing.hooksystem import *
from django.conf                 import settings
from django.contrib.auth.models  import User
from urllib                      import quote
from urllib2                     import urlopen


def testsign(query_string):
    url = '%s?data=%s' % (settings.LINKTOOL_AUTH_URL, quote(query_string))
    result = urlopen(url).read()
    return (result == 'true')


class LinktoolAuthBackend(object):

    def __init__(self):
        assert settings.LINKTOOL_AUTH_URL, \
            'LinktoolAuthBackend requires settings.LINKTOOL_AUTH_URL'

    def authenticate(self, request=None):
        valid = testsign(request.META['QUERY_STRING'])
        if valid:
            username = request.GET['user']
            return self.maybe_initialize_user(username)
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def maybe_initialize_user(self, username, look_local=True):
        """Look up user in Django db; if not found, fetch user detail
        from backend and set up a local user object. Return None if no
        such user exists in either Django or the backend.

        Setting look_local=False skips the Django search and heads
        straight to the backend; this shaves a database call when
        walking a set of backends to initialize a user. Skipping
        look_local on a username that already exists in Django will
        certainly lead to an integrity error.

        This method is NOT part of the Django backend interface.
        """
        user = None
        if look_local:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        if user is None:
            u = self.lookup(username)
            if u:           # user found in LDAP or whatever.
                user = User(username=username,
                            first_name = u['given_name'],
                            last_name  = u['surname'],
                            email      = u.get('email', None))
                user.set_unusable_password()
                user.save()
        return user

    def lookup(self, username):
        return callhook('external_person_lookup', username)

