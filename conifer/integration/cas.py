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
# conifer/syrup/integration.py and 'maybe_decorate' in
# conifer/syrup/models.py.


import django_cas.backends


class CASBackend(django_cas.backends.CASBackend):

    def authenticate(self, ticket, service):
        """Authenticates CAS ticket and retrieves user data"""

        user = super(CASBackend, self).authenticate(ticket, service)
        if user:
            user.maybe_decorate()
        return user
