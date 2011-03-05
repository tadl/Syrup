#!/usr/bin/env python

"A rewrite of SpeedLookup in Python."

import ldap
import csv, sys

MIN_QUERY_LENGTH = 3

BASE  = "ou=people,dc=uwindsor,dc=ca"
SCOPE = ldap.SCOPE_ONELEVEL
ATTRS = ["uid", "sn", "eduPersonNickname", "employeeType",
         "uwinDepartment", "mail", "givenName"]

# fetch server connection details from /etc/ldap-agent

tmp = [line.strip() for line in file('/etc/ldap-agent')]
SERVER, USER, PWD = tmp[:3]

# ---------------------------------------------------------------------------
# filter construction

def _or(*parts):
    return '|%s' % ''.join(['(%s)' % p for p in parts])

def _and(*parts):
    return '&%s' % ''.join(['(%s)' % p for p in parts])

def build_filter(query, include_students=False):
    if len(query) < MIN_QUERY_LENGTH:
        return None
    else:
        query = query.lower()
        pattern = _and(_or('uid=%(query)s*',
                           'sn=%(query)s*',
                           'givenName=%(query)s*'),
                       _or(*['employeeType=%s' % x for x in
                             ('Faculty', 'Administration',
                              'Staff', 'Librarian', 
                              'Academic*')]))
        if include_students:
            # we only match students by uid.
            pattern = _or('uid=%(query)s', pattern)
        return '(%s)' % (pattern % locals())

# ---------------------------------------------------------------------------
# LDAP interaction

def search(filt):
    if not filt:
        return []

    conn = ldap.open(SERVER)
    conn.simple_bind_s(USER, PWD)
    results = conn.search_s(BASE, SCOPE, filt, ATTRS)

    for (cn, dct) in results:
        dct['cn'] = cn
        if dct.get('eduPersonNickname'):
            dct['givenName'] = dct['eduPersonNickname']
        for attr in dct:
            dct[attr] = dct[attr][0]
    
    dicts = [dct for cn,dct in results]
    dicts.sort(key=lambda dct: (dct['sn'], dct['givenName']))
    conn.unbind_s()
    return dicts

# ---------------------------------------------------------------------------
# main

if __name__ == '__main__':
    # the headings to print, and their corresponding ldap attributes.
    HEADINGS = ["uid", "surname", "given", "type", "department", "email"]
    MAPPING  = ["uid", "sn", "givenName", "employeeType", "uwinDepartment", "mail"]

    out      = csv.writer(sys.stdout)
    query    = sys.argv[1]
    students = 'students' in sys.argv
    filt     = build_filter(query, include_students=students)
    results  = search(filt)

    # print them
    out.writerow(HEADINGS)
    for dct in results:
        row = [dct.get(key,'') for key in MAPPING]
        out.writerow(row)
