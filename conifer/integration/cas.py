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


from django_cas import backends

# First, we monkey-patch the django_cas verifier.
#
# Okay, monkey-patching is lame. But I have a problem with the way django_cas
# fails to clean usernames. At Windsor, if you log in as '_FAWCETT_', where
# '_' is a space, django_cas will create a new User object for
# username='_FAWCETT_', even if a user 'fawcett' exists. Bad!
#
# Now, I'm not certain that all CAS-using campus would like to have their
# usernames lower-cased, though I'm guessing it won't hurt. But I'm absolutely
# sure that spaces should be stripped, always. I'll propose a patch to
# django_cas; but in the meantime, let's reach into django_cas and fix it.

if hasattr(backends, '_verify'):
    _orig_verify = backends._verify
    def _newverify(*args, **kwargs):
        username = _orig_verify(*args, **kwargs)
        if username:
            username = username.lower().strip()
        return username
    backends._verify = _newverify


class CASBackend(backends.CASBackend):

    def authenticate(self, ticket, service):
        """Authenticates CAS ticket and retrieves user data"""

        user = super(CASBackend, self).authenticate(ticket, service)
        if user:
            user.maybe_decorate()
        return user
