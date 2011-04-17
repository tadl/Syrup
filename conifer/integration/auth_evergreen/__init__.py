from .eg_http import EvergreenAuthServer
from django.contrib.auth.models import User


class EvergreenAuthBackend(EvergreenAuthServer):

    def __init__(self):
        super(EvergreenAuthBackend, self).__init__()

    def authenticate(self, username=None, password=None):
        login_token = self.login(username, password)
        if login_token:
            return self.maybe_initialize_user(
                username, login_token=login_token)
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def maybe_initialize_user(self, username, login_token=None, look_local=True):
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
        username = self.djangoize_username(username)
        if look_local:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        if user is None:
            u = self.lookup(username, login_token)
            if u:           # user found in Evergreen.
                user = User(username   = username,
                            first_name = u['first_name'],
                            last_name  = u['last_name'],
                            email      = u['email'])
                user.set_unusable_password()
                user.save()
        return user
