from datetime           import date
from evergreen_site     import EvergreenIntegration
import csv
import subprocess
from django.conf                          import settings
from urllib2 import urlopen
from django.utils import simplejson
try:
    from conifer.libsystems.evergreen import opensrf
except ImportError:
    print "evergreen access without opensrf library"


class EvergreenExampleIntegration(EvergreenIntegration):

    OSRF_CAT_SEARCH_ORG_UNIT = 106
    
    OPAC_LANG = 'en-US'
    OPAC_SKIN = 'default'

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
        ('821', 'Reserves Counter'),
        ('598', 'Circulating Collection'),
        ]

    # Options for call number prefixes
    PREFIX_CHOICES = [
        ('-1', ''),
        ('1', 'FIC'),
        ('2', 'NF'),
        ]

    # Options for call number suffixes
    SUFFIX_CHOICES = [
        ('-1', ''),
        ('1', 'OV'),
        ('2', 'BIO'),
        ]



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

