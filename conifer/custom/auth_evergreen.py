from auth_evergreen_support import EvergreenAuthServer
from django.contrib.auth.models import User
from django.conf import settings

class EvergreenAuthBackend(EvergreenAuthServer):

    def __init__(self):
        EvergreenAuthServer.__init__(
            self, settings.EVERGREEN_XMLRPC_SERVER)

    def authenticate(self, username=None, password=None):
        pwd_valid = self.login(username, password)
        if pwd_valid:
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
            if u:           # user found in Evergreen.
                user = User(username=username,
                            first_name = u['first_name'],
                            last_name  = u['last_name'],
                            email      = u['email'])
                user.set_unusable_password()
                user.save()
        return user
