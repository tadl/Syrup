from conifer.libsystems import ezproxy
from datetime           import date
from evergreen_site     import EvergreenIntegration
import csv
import subprocess
import uwindsor_fuzzy_lookup
from django.conf                          import settings
from urllib2 import urlopen
from django.utils import simplejson


class UWindsorIntegration(EvergreenIntegration):

    OSRF_CAT_SEARCH_ORG_UNIT = 106
    
    OPAC_LANG = 'en-CA'
    OPAC_SKIN = 'uwin'

    RESERVES_DESK_NAME = 'Leddy: Course Reserves - Main Bldng - 1st Flr - Reserve Counter at Circulation Desk'
    SITE_DEFAULT_ACCESS_LEVEL = 'RESTR'

    # Options for circ modifiers
    MODIFIER_CHOICES = [
        ('CIRC', 'Normal'),
        ('RSV2', '2 Hour'),
        ('RSV1', '1 Day'),
        ('RSV3', '3 Day'),
        ('RSV7', '7 Day'),
        ]

    # TODO: these are harcoded for now, should make the opensrf calls to resolve them
    # Options for circ desk
    DESK_CHOICES = [
        ('631', 'Reserves Counter'),
        ('598', 'Circulating Collection'),
        ]

    #---------------------------------------------------------------------------
    # proxy server integration

    ezproxy_service = ezproxy.EZProxyService(
        settings.EZPROXY_HOST,
        settings.EZPROXY_PASSWORD)

    def proxify_url(self, url):
        """
        Given a URL, determine whether the URL needs to be passed through
        a reverse-proxy, and if so, return a modified URL that includes
        the proxy. If not, return None.
        """
        return self.ezproxy_service.proxify(url)


    #---------------------------------------------------------------------------
    # campus information

    def department_course_catalogue(self):
        """
        Return a list of rows representing all known, active courses and
        the departments to which they belong. Each row should be a tuple
        in the form: ('Department name', 'course-code', 'Course name').
        """
        url = 'http://cleo.uwindsor.ca/graham/courses.txt.gz'
        p = subprocess.Popen('curl -s %s | gunzip -c' % url,
                             shell=True, stdout=subprocess.PIPE)
        reader = csv.reader(p.stdout)
        catalogue = list(reader)
        p.stdout.close()
        return catalogue

    def term_catalogue(self):
        """
        Return a list of rows representing all known terms. Each row
        should be a tuple in the form: ('term-code', 'term-name',
        'start-date', 'end-date'), where the dates are instances of the
        datetime.date class.
        """
        # TODO: make this algorithmic.
        return [
            ('2011S', '2011 Summer', date(2011,5,1), date(2011,9,1)),
            ('2011F', '2011 Fall', date(2011,9,1), date(2011,12,31)),
            ]

    def _campus_info(self, name, *args):
        url = '%s%s?%s' % (settings.CAMPUS_INFO_SERVICE, name, simplejson.dumps(args))
        try:
            raw = urlopen(url).read()
            return simplejson.loads(raw)
        except:
            return None


    def external_person_lookup(self, userid):
        """
        Given a userid, return either None (if the user cannot be found),
        or a dictionary representing the user. The dictionary must contain
        the keys ('given_name', 'surname') and should contain 'email' if
        an email address is known, and 'patron_id' if a library-system ID
        is known.
        """
        return self._campus_info('person_lookup', userid)


    def external_memberships(self, userid):
        """
        Given a userid, return a list of dicts, representing the user's
        memberships in known external groups. Each dict must include the
        following key/value pairs:
        'group': a group-code, externally defined;
        'role':          the user's role in that group, one of (INSTR, ASSIST, STUDT).
        """
        if '@' in userid:
            # If there's an at-sign in the userid, then it's not a UWin ID.
            # Maybe you've got Evergreen authentication turned on?
           return []
 
        memberships = self._campus_info('membership_ids', userid)
        if memberships:
            for m in memberships:
                m['role'] = self._decode_role(m['role'])
        return memberships

    def _decode_role(self, role):
        if role == 'Instructor':
            return 'INSTR'
        else:
            return 'STUDT'

    def fuzzy_person_lookup(self, query, include_students=False):
        """
        Given a query, return a list of users who probably match the
        query. The result is a list of (userid, display), where userid
        is the campus userid of the person, and display is a string
        suitable for display in a results-list. Include_students
        indicates that students, and not just faculty/staff, should be
        included in the results.
        """
        # Note, our 'include_students' option only matches students on exact
        # userids. That is, fuzzy matching only works for staff, faculty, and
        # other non-student roles.

        filter	= uwindsor_fuzzy_lookup.build_filter(query, include_students)
        results = uwindsor_fuzzy_lookup.search(filter)

        out = []
        for res in results:
            if not 'employeeType' in res:
                res['employeeType'] = 'Student' # a 99% truth!
            if not 'uwinDepartment' in res:
                res['uwinDepartment'] = ''
            display = ('%(givenName)s %(sn)s. %(employeeType)s, '
                       '%(uwinDepartment)s. <%(mail)s>. [%(uid)s]') % res
            out.append((res['uid'], display))
        return out


    def derive_group_code_from_section(self, site, section):
        """
        This function is used to simplify common-case permission setting
        on course sites. It takes a site and a section number/code, and
        returns the most likely external group code. (This function will
        probably check the site's term and course codes, and merge those
        with the section code, to derive the group code.) Return None if a
        valid, unambiguous group code cannot be generated.
        """
        try:
            section = int(section)
        except:
            return None

        return '%s-%s-%s' % (site.course.code.replace('-', ''),
                             section,
                             site.start_term.code)

    #---------------------------------------------------------------------------
    # copyright/permissions

    def download_declaration(self):
        """
        Returns a string. The declaration to which students must agree when
        downloading electronic documents. If not customized, a generic message
        will be used.
        """
        # as per Joan Dalton, 2010-12-21.
        return ("I warrant that I am a student of the University of Windsor "
                "enrolled in a course of instruction. By pressing the "
                "'Request' button below, I am requesting a digital copy of a "
                "reserve reading for research, private study, review or criticism "
                "and that I will not use the copy for any other purpose, nor "
                "will I transmit the copy to any third party.")

