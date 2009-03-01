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
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                u = self.lookup(username)
                user = User(username=username,
                            first_name= u['first_name'],
                            last_name = u['last_name'],
                            email     = u['email'])
                user.set_unusable_password()
                user.save()
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
