# CAS authentication. See http://code.google.com/p/django-cas/
#
# To use CAS authentication, you must "easy_install django-cas", then add these
# to your local_settings.py:
#
# CAS_AUTHENTICATION = True
# CAS_SERVER_URL     = 'https://my.cas.server.example.net/cas/'
#
# You will probably also want to define two customization hooks:
# external_person_lookup and user_needs_decoration. See:
# conifer/syrup/integration.py.

from conifer.plumbing.hooksystem import gethook, callhook
import django_cas.backends


class CASBackend(django_cas.backends.CASBackend):

    def authenticate(self, ticket, service):
        """Authenticates CAS ticket and retrieves user data"""

        user = super(CASBackend, self).authenticate(ticket, service)
        if user and gethook('external_person_lookup'):
            decorate_user(user)
        return user


# TODO is this really CAS specific? Wouldn't linktool (for example)
# also need such a decorator?

def decorate_user(user):
    dectest = gethook('user_needs_decoration', default=_user_needs_decoration)
    if not dectest(user):
        return

    dir_entry = callhook('external_person_lookup', user.username)
    if dir_entry is None:
        return

    user.first_name = dir_entry['given_name']
    user.last_name  = dir_entry['surname']
    user.email      = dir_entry.get('email', user.email)
    user.save()

    if 'patron_id' in dir_entry:
        # note, we overrode user.get_profile() to automatically create
        # missing profiles. See models.py.
        user.get_profile().ils_userid = dir_entry['patron_id']
        profile.save()


def _user_needs_decoration(user):
    return user.last_name is not None
