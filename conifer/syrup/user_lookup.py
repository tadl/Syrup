from django.contrib.auth.models import User
from django.contrib.auth import get_backends

#----------------------------------------------------------------------
# Initializing an external user account

# TODO: does it make sense to put maybe_initialize_user on the
# authentication backends, or does it belong somewhere else?

# For usernames that come from external authentication sources (LDAP,
# Evergreen, etc.) we need a general way to look up a user who may not
# yet have a Django account.  For example, you might want to add user
# 'xsmith' as the instructor for a course. If 'xsmith' is in LDAP but
# not yet in Django, it would be nice if a Django record were lazily
# created for him upon lookup. 

# That's what 'maybe_initialize_user' is for: participating backends
# provide a 'maybe_initialize_user' method which creates a new User
# record if one doesn't exist. Otherwise, 'maybe_initialize_user' is
# equivalent to 'User.objects.get(username=username)'.

_backends_that_can_initialize_users = [
    be for be in get_backends() if hasattr(be, 'maybe_initialize_user')]

def maybe_initialize_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        for be in _backends_that_can_initialize_users:
            user = be.maybe_initialize_user(username, look_local=False)
            if user:
                return user
