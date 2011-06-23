from datetime           import date
from evergreen_site     import EvergreenIntegration
import csv
import subprocess
from django.conf                          import settings
from urllib2 import urlopen
from django.utils import simplejson
from conifer.libsystems.evergreen import opensrf


class EvergreenExampleIntegration(EvergreenIntegration):

    OSRF_CAT_SEARCH_ORG_UNIT = 28
    
    OPAC_LANG = 'en-US'
    OPAC_SKIN = 'default'

    RESERVES_DESK_NAME = 'Reserves'
    SITE_DEFAULT_ACCESS_LEVEL = 'RESTR'

    def external_person_lookup(self, userid):
        """
        Given a userid, return either None (if the user cannot be found),
        or a dictionary representing the user. The dictionary must contain
        the keys ('given_name', 'surname') and should contain 'email' if
        an email address is known, and 'patron_id' if a library-system ID
        is known.
        """
        return opensrf.ils_patron_details(userid)


    def fuzzy_person_lookup(self, query, include_students=False, level='STAFF'):
        patrons = []

        if level == 'USERNAME':
            patrons = opensrf.ils_patron_lookup(query,False,True,True)
        elif level == 'EVERYONE':
            patrons = opensrf.ils_patron_lookup(query,False,False,True)
        else:
            patrons = opensrf.ils_patron_lookup(query)
        
        return patrons

    #---------------------------------------------------------------------------
    # copyright/permissions

    def download_declaration(self):
        """
        Returns a string. The declaration to which students must agree when
        downloading electronic documents. If not customized, a generic message
        will be used.
        """
        # based on U. of Windsor
        return ("I warrant that I am a student of this university "
                "enrolled in a course of instruction. By pressing the "
                "'Request' button below, I am requesting a digital copy of a "
                "reserve reading for research, private study, review or criticism "
                "and that I will not use the copy for any other purpose, nor "
                "will I transmit the copy to any third party.")

