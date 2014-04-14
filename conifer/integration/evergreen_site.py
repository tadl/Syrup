# See conifer/syrup/integration.py for documentation.

from conifer.libsystems                   import marcxml as M
from conifer.libsystems.evergreen         import item_status as I
from conifer.libsystems.evergreen.support import initialize, E1
from conifer.libsystems.z3950             import pyz3950_search as PZ
from conifer.plumbing.memoization         import memoize
from django.conf                          import settings
from xml.etree                            import ElementTree as ET
import re
import time
import traceback

# If the Python OpenSRF library is installed, we want to know about it. It
# isn't needed for our read-only ILS operations, only for updates.

try:
    import osrf
    OSRF_LIB_INSTALLED = True
except ImportError:
    OSRF_LIB_INSTALLED = False
    
if OSRF_LIB_INSTALLED:
    from conifer.libsystems.evergreen.startup import ils_startup


OPENSRF_AUTHENTICATE      = "open-ils.auth.authenticate.complete"
OPENSRF_AUTHENTICATE_INIT = "open-ils.auth.authenticate.init"
OPENSRF_BATCH_UPDATE      = "open-ils.cat.asset.copy.fleshed.batch.update"
OPENSRF_CIRC_UPDATE       = "open-ils.cstore open-ils.cstore.direct.action.circulation.update"
OPENSRF_CLEANUP           = "open-ils.auth.session.delete"
OPENSRF_CN_BARCODE        = "open-ils.circ.copy_details.retrieve.barcode.authoritative"
OPENSRF_CN_CALL           = "open-ils.search.asset.copy.retrieve_by_cn_label"
OPENSRF_COPY_COUNTS       = "open-ils.search.biblio.copy_counts.location.summary.retrieve"
OPENSRF_FLESHED2_CALL     = "open-ils.search.asset.copy.fleshed2.retrieve"
OPENSRF_FLESHEDCOPY_CALL  = "open-ils.search.asset.copy.fleshed.batch.retrieve.authoritative"


# @disable is used to point out integration methods you might want to define
# in your subclass, but which are not defined in the basic Evergreen
# integration.

def disable(func):
    return None

class EvergreenIntegration(object):

    # Either specify EVERGREEN_SERVERin your local_settings, or override
    # EVERGREEN_SERVER and OPAC_URL, etc. in your subclass of this class.

    EVERGREEN_SERVER = getattr(settings, 'EVERGREEN_SERVER', '')


    # ----------------------------------------------------------------------
    # These variables depend on EVERGREEN_SERVER, or else you need to override
    # them in your subclass.

    # OPAC_URL: the base URL for the OPAC's Web interface.
    # default: http://your-eg-server/
    # local_settings variable: EVERGREEN_OPAC_URL

    if hasattr(settings, 'EVERGREEN_OPAC_URL'):
        OPAC_URL = settings.EVERGREEN_OPAC_URL
    else:
        assert EVERGREEN_SERVER
        OPAC_URL = 'http://%s/' % EVERGREEN_SERVER

    # IDL_URL: where is your fm_IDL.xml file located? For faster process
    # startup, it's recommended you use a file:// URL, pointing to a local
    # copy of the file. default: http://your-eg-server/reports/fm_IDL.xml
    # local_settings variable: EVERGREEN_IDL_URL

    IDL_URL = getattr(settings, 'EVERGREEN_IDL_URL',
                      'http://%s/reports/fm_IDL.xml' % EVERGREEN_SERVER)

    # GATEWAY_URL: where is your HTTP gateway?
    # default: http://your-eg-server/osrf-gateway-v1'
    # variable: EVERGREEN_GATEWAY_URL

    GATEWAY_URL = getattr(settings, 'EVERGREEN_GATEWAY_URL',
                      'http://%s/osrf-gateway-v1' % EVERGREEN_SERVER)

    # end of variables dependent on EVERGREEN_SERVER
    # ----------------------------------------------------------------------

    # BIB_PART_MERGE: display multiple parts for one bib title
    # that have been scanned in separately in one section
    BIB_PART_MERGE = bool(getattr(settings, 'BIB_PART_MERGE', True))

    # OPAC_LANG and OPAC_SKIN: localization skinning for your OPAC

    OPAC_LANG = getattr(settings, 'EVERGREEN_OPAC_LANG', 'en-CA')
    OPAC_SKIN = getattr(settings, 'EVERGREEN_OPAC_SKIN', 'default')

    # RESERVES_DESK_NAME: this will be going away, but for now, it's the full
    # ILS-side name of the reserves desk. This needs to be replaced with a
    # database-driven lookup for the correct reserves desk in the context of
    # the given item.

    RESERVES_DESK_NAME = getattr(settings, 'RESERVES_DESK_NAME', None)
    
    # USE_Z3950: if True, use Z39.50 for catalogue search; if False, use OpenSRF.
    # Don't set this value directly here: rather, if there is a valid Z3950_CONFIG
    # settings in local_settings.py, then Z39.50 will be used.

    USE_Z3950 = bool(getattr(settings, 'Z3950_CONFIG', None))

    TIME_FORMAT = getattr(settings, 'SYRUP_TIME_FORMAT', '%Y-%m-%dT%H:%M:%S')
    DUE_FORMAT  = getattr(settings, 'SYRUP_DUE_FORMAT', '%b %d %Y, %r')

    # regular expression to detect DVD, CD, CD-ROM, Guide, Booklet on the end of a
    # call number
    ATTACHMENT_EXPRESSION = getattr(settings, 'ATTACHMENT_REGEXP', '\w*DVD\s?|\w*CD\s?|\w[Gg]uide\s?|\w[Bb]ooklet\s?|\w*CD\-ROM\s?')
    IS_ATTACHMENT = re.compile(ATTACHMENT_EXPRESSION)

    # regular expression to volume designations within a 
    # call number
    EMBEDDEDVOL_EXPRESSION = getattr(settings, 'EMBEDDEDVOL_REGEXP','\w*[Vv]\.\s?(\d+)')
    IS_EMBEDDEDVOL = re.compile(EMBEDDEDVOL_EXPRESSION)

    # Used if you're doing updates to Evergreen from Syrup.
    UPDATE_CHOICES = [ 
        ('Cat', 'Catalogue'), 
        ('One', 'Syrup only'), 
        ('Zap', 'Remove from Syrup'), 
        ] 

    # ----------------------------------------------------------------------
    def __init__(self):
        # establish our OpenSRF connection.
        initialize(self)

        if OSRF_LIB_INSTALLED:
            ils_startup(self.EVERGREEN_SERVER, 
                        self.IDL_URL)

        # set up the available/reshelving codes, for the item_status routine.
        status_decode = [(str(x['id']), x['name'])
                         for x in E1('open-ils.search.config.copy_status.retrieve.all')]

        #for x in E1('open-ils.search.config.copy_status.retrieve.all'):
        #    print "x", x
        self.AVAILABLE  = [id for id, name in status_decode if name == 'Available'][0]
        self.RESHELVING = [id for id, name in status_decode if name == 'Reshelving'][0]
        self.CHECKEDOUT = [id for id, name in status_decode if name == 'Checked out'][0]


    def item_status(self, item, bcs=[], ids=[]):
        """
        Given an Item object, return three numbers: (library, desk,
        avail). Library is the total number of copies in the library
        system; Desk is the number of copies at the designated reserves
        desk; and Avail is the number of copies available for checkout at
        the given moment. Note that 'library' includes 'desk' which
        includes 'avail'. You may also return None if the item is
        nonsensical (e.g. it is not a physical object, or it has no bib
        ID).

        Note, 'item.bib_id' is the item's bib_id, or None;
        'item.item_type' will equal 'PHYS' for physical items;
        'item.site.service_desk' is the ServiceDesk object associated with
        the item. The ServiceDesk object has an 'external_id' attribute
        which should represent the desk in the ILS.
        """
        if not item.bib_id:
            return None

        #really silly function to turn list into string for passing
        def make_obj_string(objs):
            objlist = ""
            for obj in objs:
                if len(objlist) > 0:
                    objlist = objlist + ';'

                for o in obj:
                    if obj.index(o) > 0:
                        objlist = objlist + '/'
                    objlist = objlist + str(o)

            return objlist

        bclist = make_obj_string(bcs)
        idlist = make_obj_string(ids)
        return self._item_status(item.bib_id, item.barcode, bclist, idlist)

    #in general, you want to cache this for a few minutes
    #but bump this value to 0 or something low for debugging
    CACHE_TIME = 300

    @memoize(timeout=CACHE_TIME)
    def _item_status(self, bib_id, barcode, bclist, idlist):

        #sanity variables for multipart titles
        DUE = 0
        READY = 1
        LOCKED = 2 #lock in an available copy

        class copy_obj:
           def __init__(self, circ_modifier, circs, part_label, part_sort, syrup_id):
              self.circ_modifier = circ_modifier
              self.circs = circs
              self.part_label = part_label
              self.part_sort = part_sort
              self.syrup_id = syrup_id

        def make_obj_list(objlist):
           objset = []
           objcoll = objlist.split(";")
           for o in objcoll:
               objset.append(o.split("/"))

           return objset

        def collect_set(barcode,bcs,ids):
           bc_dups = []
           id_dups = []
           i=0
           for bc in bcs:
               if barcode in bc:
                   return bc,ids[i]
               i = i+1

           return bc_dups, id_dups
                            
        def get_copydetails(barcode,copyids,reserves_loc,bcs,ids):
           copy_list = []

           bcs_set, ids_set = collect_set(barcode,bcs,ids)

           for copyid in copyids:
              circinfo = E1(OPENSRF_FLESHED2_CALL, copyid)
              circbarcode = None

              if barcode is not None:
                  circbarcode = circinfo.get("barcode")
             
              thisloc = circinfo.get("location")

              if thisloc:
                  thisloc = thisloc.get("name")

              #create copy object for supplied barcode - will be all barcodes if none supplied
              if thisloc in reserves_loc and (barcode==circbarcode or circbarcode in bcs_set):
                  circ_modifier = circinfo.get("circ_modifier")
                  circs = circinfo.get("circulations")
                  parts = circinfo.get("parts")
                  part_label = ''
                  part_sort = None
                  part = None
                  if parts:
                      part = parts[0]
                  if part:
                      part_label = part.get("label")
                      part_sort = part.get("label_sortkey")

                  id_ind = -1
                  if circbarcode in bcs_set:
                      id_ind = ids_set[bcs_set.index(circbarcode)]
                  copy_list.append(copy_obj(circ_modifier,circs,part_label,part_sort,id_ind))

           return sorted(copy_list, key=lambda copy: copy.part_sort)

        #deal with call numbers that have embedded parts - ugh!
        def get_dueinfo(callprefix,callsuffix,callno,earliestdue,attachtest,voltest,sort_callno,
                            bringfw,dueinfo):

            tmpinfo = ''

            _callprefix = callprefix
            _callsuffix = callsuffix
            _callno = callno
            _dueinfo = dueinfo

            if voltest:
                if (int(voltest.group(1)) > vol):
                    if len(_dueinfo) > 0:
                        _dueinfo = _dueinfo + "/"
                    _dueinfo = _dueinfo + voltest.group(0) + ': ' + time.strftime(self.DUE_FORMAT,earliestdue)
                else:
                    tmpinfo = _dueinfo
                    _dueinfo = voltest.group(0) + ': ' + time.strftime(self.DUE_FORMAT,earliestdue)
                    if len(tmpinfo) > 0:
                        _dueinfo = _dueinfo + "/" + tmpinfo
                _callprefix = _callsuffix = ''
            elif attachtest:
                tmpinfo = _dueinfo
                _dueinfo = attachtest.group(0) + ': ' + time.strftime(self.DUE_FORMAT,earliestdue)
                if len(_callno) > 0:
                    _callno = _callno + '/' + sort_callno
                    _callprefix = _callsuffix = ''
                else:
                    _callno = sort_callno
                if len(tmpinfo) > 0:
                    _dueinfo = _dueinfo + "/" + tmpinfo

            if not bringfw:
                _dueinfo = time.strftime(self.DUE_FORMAT,earliestdue)
                _callno = sort_callno

            return _dueinfo,_callno,_callprefix,_callsuffix

        #get due information - lots of pieces passed on for embedded parts
        def deal_with_dues(duetime,avail,bringfw,copy,callprefix,callsuffix,callno,earliestdue,
                attachtest,voltest,sort_callno,dueinfo):

            earlydue = earliestdue
            due = dueinfo
            due_callprefix = callprefix
            due_callno = callno
            due_callsuffix = callsuffix
             
            if copy.circs and len(copy.circs) > 0:
                if len(dueinfo) == 0 or bringfw:
                    earlydue = duetime
                    due,due_callno,due_callprefix,due_callsuffix = get_dueinfo(callprefix,callsuffix,callno,
                        earlydue,attachtest,voltest,sort_callno,bringfw,dueinfo)

                if (earlydue is None or duetime < earlydue) and not bringfw:
                   earlydue = duetime
                   due = time.strftime(self.DUE_FORMAT,earliestdue)

            return due, due_callprefix, due_callno,due_callsuffix

        #create initial call no and counts
        def initialVals(prefix,suffix,callno,lib):
            initial_callno = callno
            if prefix:
                initial_callno = prefix + callno
            if suffix:
                initial_callno = callno + suffix
            initial_avail = stats.get(self.AVAILABLE, 0)
            initial_avail += stats.get(self.RESHELVING, 0)
            anystatus_here = sum(stats.values())
                    
            return initial_callno, lib + anystatus_here

        #sometimes part information is in the callno directly, try to combine for display by
        #shifting to suffix - otherwise treat normally
        def add_in_embedded_parts(prefix,suffix,callprefix,callsuffix,callno,voltest,attachtest,vol):
            embed_prefix = callprefix
            embed_callno = callno
            embed_suffix = callsuffix

            if (voltest and vol > 0 ):
                if (int(voltest.group(1)) > vol):
                    embed_suffix = "/" + callno
                else:
                    embed_prefix = callno + "/"
            elif attachtest and callno.find(attachtest.group(0)) == -1:
                if len(callno) > 0:
                    embed_suffix = "/" + callno
                else:
                    embed_prefix = callno
            else:
                embed_callno = prefix + callno + suffix

            return embed_prefix, embed_callno, embed_suffix

        #probably not needed but final sanity check for embedded parts
        def last_check_embed(callprefix,callno,callsuffix,voltest,vol):
            last_call = callno
            last_vol = vol 
            if callno.find(callprefix) == -1:
                last_call = callprefix + callno
            if callno.find(callsuffix) == -1:
                last_call = last_call + callsuffix
            if voltest:
                last_vol = int(voltest.group(1))

            return last_call, last_vol

        #use counts from system if not parts
        def get_desk_counts(counts):
            desk_count = 0
            for i, j, k, l, m, n in counts:
                if m in self.RESERVES_DESK_NAME:
                      desk_count += n.get(self.AVAILABLE, 0)
                      desk_count += n.get(self.RESHELVING, 0)
                      desk_count += n.get(self.CHECKEDOUT, 0)
            return desk_count
                    
        #pull together status information
        def sort_out_status(barcode, sort_vol, counts, version, sort_lib, sort_desk, sort_avail, 
            sort_callno, sort_dueid, sort_dueinfo, sort_circmod, sort_allcalls, sort_alldues, prefix, suffix, 
            bcs,ids):

            vol = sort_vol
            lib = sort_lib
            desk = sort_desk
            avail = sort_avail 
            callno = sort_callno 
            dueinfo = sort_dueinfo
            circmod = sort_circmod
            allcalls = sort_allcalls
            alldues = sort_alldues
            dueid = sort_dueid

            try:
                if loc in self.RESERVES_DESK_NAME:
                    callprefix = ''
                    callsuffix = ''

                    # get initial call number and total library count
                    callno, lib = initialVals(prefix,suffix,callno,lib)

                    # volume check - based on v.1, etc. in call number
                    voltest = re.search(self.IS_EMBEDDEDVOL, callno)

                    # attachment test
                    attachtest = re.search(self.IS_ATTACHMENT, callno)

                    dueinfo = ''

                    # combine volume designations for embedded values
                    callprefix,callno,callsuffix = add_in_embedded_parts(prefix,suffix,
                        callprefix,callsuffix,callno,voltest,attachtest,vol)

                    if version >= 2.1:
                        copyids = E1(OPENSRF_CN_CALL, bib_id, [prefix,sort_callno,suffix], org)
                    else:
                        copyids = E1(OPENSRF_CN_CALL, bib_id, sort_callno, org)

                    #get copy information
                    copies = get_copydetails(barcode,copyids,self.RESERVES_DESK_NAME,bcs,ids)

                    desk = get_desk_counts(counts)
                    avail = desk
                       
                    copy_parts = []
                    duetime = None
                    earliestdue = None

                    # we want to identify the copy that will be returned first if
                    # all are checked out
                    for copy in copies:
                        #this condition should only ever be true when a multipart is in full display
                        #in that case, the most available copy should be selected
                        if len(ids) == 1:
                            if ids[0][0] == '':
                                avail = 1 
                        if copy.part_label:
                            #print "callno", callno
                            #print "sort_callno", sort_callno

                            callno = sort_callno + " " + copy.part_label
                            if copy.part_sort in copy_parts and len(copy_parts) > 0:
                                #leave alone if locked - otherwise mark as ready
                                if allcalls[len(allcalls) - 1][1] != LOCKED:
                                    allcalls[len(allcalls) - 1] = [callno,READY,copy.syrup_id,copy.part_label]
                                    
                            else:
                                allcalls.append([callno,READY,copy.syrup_id,copy.part_label])
                            copy_parts.append(copy.part_sort)

                        bringfw = attachtest

                        # multiple volumes in identified in call number
                        if voltest and callno.find(voltest.group(0)) == -1:
                            bringfw = True

                        if copy.circs and isinstance(copy.circs, list):
                            circ = copy.circs[0]
                            rawdate = circ.get("due_date")
                            #remove offset info, %z is flakey for some reason
                            rawdate = rawdate[:-5]
                            duetime = time.strptime(rawdate, self.TIME_FORMAT)
                        elif len(allcalls) == 0:
                            dueid = [copy.syrup_id,LOCKED]

                        #get due information - lots of extra pieces needed for embedded parts
                        dueinfo,callprefix,callno,callsuffix = deal_with_dues(duetime,avail,bringfw,copy,
                            callprefix,callsuffix,callno,earliestdue,attachtest,voltest,sort_callno,dueinfo)

                        alldisplay = callno + ' (Available)'

                        if copy.circs and isinstance(copy.circs, list):
                            if (earliestdue is None or duetime < earliestdue):
                                #print "SETTING earliest to", duetime
                                earliestdue = duetime
                                dueinfo = time.strftime(self.DUE_FORMAT,earliestdue)
                                #will want the link to be to the earliest item if not multipart
                                if len(allcalls) == 0 and dueid[1] != LOCKED:
                                    dueid = [copy.syrup_id,DUE]

                            alldisplay = '%s (DUE: %s)' % (callno,time.strftime(self.DUE_FORMAT,earliestdue))

                            if len(allcalls) > 0:
                                if allcalls[len(allcalls) - 1][1] != LOCKED:
                                    allcalls[len(allcalls) - 1] = [alldisplay,DUE,copy.syrup_id,copy.part_label]
                                    if avail >= 1:
                                        avail -= 1
                            elif avail >= 1:
                                avail -= 1
                               
                        elif len(allcalls) > 0:
                            allcalls[len(allcalls) - 1] = [callno,LOCKED,copy.syrup_id,copy.part_label]

                        alldues.append(alldisplay)

                        if voltest or attachtest:
                            callno,vol = last_check_embed(callprefix,callno,callsuffix,voltest,vol)
            except:
                print "due date/call problem: ", bib_id
                print "*** print_exc:"
                traceback.print_exc()
        
            return (vol, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues)

        #get lists of barcodes and ids
        bcs = make_obj_list(bclist)
        ids = make_obj_list(idlist)

        # At this point, status information does not require the opensrf
        # bindings, I am not sure there is a use case where an evergreen
        # site would not have access to these but will leave for now
        # since there are no hardcoded references
        assert self.RESERVES_DESK_NAME, 'No RESERVES_DESK_NAME specified!'

        lib = desk = avail = vol = anystatus_here = 0
        dueid = ['',READY]
        dueinfo = ''
        callno  = ''
        circmod = ''
        allcalls = []
        alldues = []
        cpname = 'copies'
            
        EVERGREEN_STATUS_ORG = getattr(settings, 'EVERGREEN_STATUS_ORG', 1)
        EVERGREEN_STATUS_DEPTH = getattr(settings, 'EVERGREEN_STATUS_DEPTH', 0)

        counts = E1(OPENSRF_COPY_COUNTS, bib_id, EVERGREEN_STATUS_ORG, EVERGREEN_STATUS_DEPTH)

        version = getattr(settings, 'EVERGREEN_VERSION',
                      2.4)

        if version >= 2.1:
            #this loop is needed in case there are multiple reserves locations
            for org, prefix, callno, suffix, loc, stats in counts:
                if len(prefix) > 0:
                    prefix += ' '
                if len(suffix) > 0:
                    suffix = ' ' + suffix
                vol, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues = sort_out_status(barcode, vol, counts, 
                    version, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues, prefix, suffix, bcs,ids)
        else:
            for org, callno, loc, stats in counts:
                vol, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues = sort_out_status(barcode, vol, counts, 
                    version, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues, bcs,ids)
            
        if len(allcalls) > 0:
            cpname = 'volumes'

        return (cpname, lib, desk, avail, callno, dueid[0], dueinfo, circmod, allcalls, alldues)



    # You'll need to define OSRF_CAT_SEARCH_ORG_UNIT, either by overriding its
    # definition in your subclass, or by defining it in your
    # local_settings.py.

    OSRF_CAT_SEARCH_ORG_UNIT = getattr(settings, 'OSRF_CAT_SEARCH_ORG_UNIT', None)

    def cat_search(self, query, start=1, limit=10):
        barcode = ''
        bibid	= ''
        is_barcode = re.search('\d{14}', query)

        if query.startswith(self.OPAC_URL):
            results = []
            # query is an Evergreen URL
            # snag the bibid at this point
            if "=" in query and "&" in query:
                params = dict([x.split("=") for x in query.split("&")])
                for key in params.keys():
                    if key.find('?r') != -1:
                       bibid = params[key]
                results = M.marcxml_to_records(I.url_to_marcxml(query))
            else:
                # likely template opac
                # first seq of digits after a / should be the bibid
                match = re.search(r'/(\d+)', query)
                if match:
                    bibid = match.group(1)
                    results = M.marcxml_to_records(self.bib_id_to_marcxml(bibid))
            numhits = len(results)
        elif is_barcode:
            results = []
            numhits = 0
            barcode = query.strip()
            bib = E1('open-ils.search.bib_id.by_barcode', barcode)
            if bib:
                bibid = bib
                copy = E1('open-ils.supercat.record.object.retrieve', bib)
                marc = copy[0]['marc']
                # In some institutions' installations, 'marc' is a string; in
                # others it's unicode. Convert to unicode if necessary.
                if not isinstance(marc, unicode):
                    marc = unicode(marc, 'utf-8')
                tree = M.marcxml_to_records(marc)[0]
                results.append(tree)
                numhits = 1
        else:
            # query is an actual query
            if self.USE_Z3950:
                cat_host, cat_port, cat_db = settings.Z3950_CONFIG
                results, numhits = PZ.search(cat_host, cat_port, cat_db, query, start, limit)
            else:					# use opensrf
                if not self.OSRF_CAT_SEARCH_ORG_UNIT:
                    raise NotImplementedError, \
                        'Your integration must provide a value for OSRF_CAT_SEARCH_ORG_UNIT.'

                EVERGREEN_SEARCH_DEPTH = getattr(settings, 'EVERGREEN_SEARCH_DEPTH', 1)
                superpage = E1('open-ils.search.biblio.multiclass.query',
                               {'org_unit': self.OSRF_CAT_SEARCH_ORG_UNIT,
                                'depth': EVERGREEN_SEARCH_DEPTH, 
                                'limit': limit, 'offset': start-1,
                                'visibility_limit': 3000,
                                'default_class': 'keyword'},
                               query, 1)
                ids = [id for (id,) in superpage['ids']]
                results = []
                for rec in E1('open-ils.supercat.record.object.retrieve', ids):
                    marc = rec['marc']
                    # In some institutions' installations, 'marc' is a string; in
                    # others it's unicode. Convert to unicode if necessary.
                    if not isinstance(marc, unicode):
                        marc = unicode(marc, 'utf-8')
                    tree = M.marcxml_to_records(marc)[0]
                    results.append(tree)
                numhits = int(superpage['count'])
        return results, numhits, bibid, barcode

    def bib_id_to_marcxml(self, bib_id):
        """
        Given a bib_id, return a MARC record in MARCXML format. Return
        None if the bib_id does not exist.
        """
        try:
            xml = I.bib_id_to_marcxml(bib_id)
            return ET.fromstring(xml)
        except:
            return None

    def marc_to_bib_id(self, marc_string):
        """
        Given a MARC record, return either a bib ID or None, if no bib ID can be
        found.
        """
        dct = M.marcxml_to_dictionary(marc_string)
        bib_id = dct.get('901c')
        return bib_id

    def bib_id_to_url(self, bib_id):
        """
        Given a bib ID, return either a URL for examining the bib record, or None.
        """
        if bib_id:
            url = '%seg/opac/record/%s' % (
                self.OPAC_URL, bib_id)
            return url

    if USE_Z3950:
        # only if we are using Z39.50 for catalogue search. Against our Conifer
        # Z39.50 server, results including accented characters are often seriously
        # messed up. (Try searching for "montreal").
        def get_better_copy_of_marc(self, marc_string):
            """
            This function takes a MARCXML record and returns either the same
            record, or another instance of the same record from a different
            source.

            This is a hack. There is currently at least one Z39.50 server that
            returns a MARCXML record with broken character encoding. This
            function declares a point at which we can work around that server.
            """
            bib_id = self.marc_to_bib_id(marc_string)
            better = self.bib_id_to_marcxml(bib_id)
            # don't return the "better" record if there's no 901c in it...
            if better and ('901c' in M.marcxml_to_dictionary(better)):
                return better
            return ET.fromstring(marc_string)

    def marcxml_to_url(self, marc_string):
        """
        Given a MARC record, return either a URL (representing the
        electronic resource) or None.

        Typically this will be the 856$u value; but in Conifer, 856$9 and
        856$u form an associative array, where $9 holds the institution
        codes and $u holds the URLs.
        """

        LIBCODE = 'OWA'			
        if hasattr(settings, 'EVERGREEN_LIBCODE'):
           LIBCODE = settings.EVERGREEN_LIBCODE
        try:
            dct           = M.marcxml_to_dictionary(marc_string)
            words = lambda string: re.findall(r'\S+', string)
            keys  = words(dct.get('8569'))
            urls  = words(dct.get('856u'))
            return urls[keys.index(LIBCODE)]
        except:
            return None

    @disable
    def department_course_catalogue(self):
        """
        Return a list of rows representing all known, active courses and
        the departments to which they belong. Each row should be a tuple
        in the form: ('Department name', 'course-code', 'Course name').
        """

    @disable
    def term_catalogue(self):
        """
        Return a list of rows representing all known terms. Each row
        should be a tuple in the form: ('term-code', 'term-name',
        'start-date', 'end-date'), where the dates are instances of the
        datetime.date class.
        """

    @disable
    def external_person_lookup(self, userid):
        """
        Given a userid, return either None (if the user cannot be found),
        or a dictionary representing the user. The dictionary must contain
        the keys ('given_name', 'surname') and should contain 'email' if
        an email address is known, and 'patron_id' if a library-system ID
        is known.
        """

    @disable
    def external_memberships(self, userid):
        """
        Given a userid, return a list of dicts, representing the user's
        memberships in known external groups. Each dict must include the
        following key/value pairs:
        'group': a group-code, externally defined;
        'role':          the user's role in that group, one of (INSTR, ASSIST, STUDT).
        """

    @disable
    def fuzzy_person_lookup(self, query, include_students=False):
        """
        Given a query, return a list of users who probably match the
        query. The result is a list of (userid, display), where userid
        is the campus userid of the person, and display is a string
        suitable for display in a results-list. Include_students
        indicates that students, and not just faculty/staff, should be
        included in the results.
        """
    @disable
    def derive_group_code_from_section(self, site, section):
        """
        This function is used to simplify common-case permission setting
        on course sites. It takes a site and a section number/code, and
        returns the most likely external group code. (This function will
        probably check the site's term and course codes, and merge those
        with the section code, to derive the group code.) Return None if a
        valid, unambiguous group code cannot be generated.
        """


    @disable
    def download_declaration(self):
        """
        Returns a string. The declaration to which students must agree when
        downloading electronic documents. If not customized, a generic message
        will be used.
        """

    @disable
    def proxify_url(self, url):
        """
        Given a URL, determine whether the URL needs to be passed through
        a reverse-proxy, and if so, return a modified URL that includes
        the proxy. If not, return None.
        """
