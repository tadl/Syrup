# -*- encoding: utf-8 -*-

from conifer.syrup.models import *
from conifer.plumbing.hooksystem import callhook

VALID_ROLES = [code for code, desc in Membership.ROLE_CHOICES]

#-----------------------------------------------------------------------------

def reconcile_user_memberships(user):
    """
    Polling an externally-defined system to find out what externally-defined
    groups this user belongs to, perform a series of "adds" and "drops" in any
    internal groups that mirror those external groups.
    """

    # This function may be called frequently, so it's important that it runs
    # efficiently. In the case where no group-memberships change, this
    # function should execute no more than two SQL queries: one to fetch the
    # list of 'interesting' groups, and another to fetch the list of the
    # user's current memberships. (Of course it's also important that the
    # external hook-function runs as efficiently as possible, but that's
    # outside of our scope.)

    # The 'external_memberships' hook function must return a list of
    # (groupcode, role) tuples (assuming the hook function has been defined;
    # otherwise, the hook system will return None). All of our membership
    # comparisons are based on groupcodes, which internally are stored in the
    # Group.external_id attribute. We only consider roles if we are adding a
    # user to a group.

    # This design assumes (but does not assert) that each groupcode is
    # associated with exactly zero or one internal Groups. Specifically, you
    # will get unexpected results if (a) there are multiple Groups with the
    # same code, and (b) the user is currently a member of some of those
    # Groups, but not others.

    _externals  = callhook('external_memberships', user.username) or []
    externals   = [(e['group'], e['role']) for e in _externals]
    extgroups   = set(g for g, role in externals)
    role_lookup = dict(externals) # a map of groupcodes to roles.
    assert all((role in VALID_ROLES) for g, role in externals)

    # What group-codes are currently 'of interest' (i.e., in use in the
    # system) and in which groups is the user already known to be a member?

    _base       = Group.objects.filter(external_id__isnull=False)
    of_interest = set(r[0] for r in _base.values_list('external_id'))
    current     = set(r[0] for r in _base.filter(membership__user=user) \
                          .values_list('external_id'))

    # to_add:  external ∩ of_interest ∩ ¬current
    # to_drop: current  ∩ of_interest ∩ ¬external

    to_add  = extgroups.intersection(of_interest).difference(current)
    to_drop = current.intersection(of_interest).difference(extgroups)

    # Since we assert that external groupcodes can be associated with no more
    # than one internal Group, an external groupcode can be used as a map to
    # exactly zero or one internal Groups. We take care that 'to_add_groups'
    # does not include any groups in which the user is already a member, which
    # is imposible under this assertion. This is just a bit of defensive
    # programming, in case the larger algorithm is changed.

    to_add_groups = Group.objects.filter(
        ~Q(membership__user=user), # "user is not already a member"
         external_id__in=to_add)

    # process the adds and drops.

    for group in to_add_groups:
        Membership.objects.create(group=group, user=user, 
                                  role=role_lookup[group.external_id])

    to_drop_memberships = Membership.objects.filter(
        group__external_id__in=to_drop, 
        user=user)
    to_drop_memberships.delete()

    return (to_add, to_drop)



if __name__ == '__main__':    
    from django.db import connection
    from pprint    import pprint

    user      = User.objects.get(username='fawcett')
    add, drop = reconcile_user_memberships(user)
    print (add, drop)

    for q in connection.queries:
        pprint(q)
