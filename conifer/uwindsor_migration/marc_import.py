from conifer.libsystems.marcxml import *
from conifer.plumbing.hooksystem import *
from xml.etree import ElementTree as ET
# this is copied from views/items.py. It should be factored out
# properly, but I'm in a hurry.

def marc_import(site, raw_pickitem, bookbag_url):
    parent_item = None
    pickitem = marcxml_to_dictionary(raw_pickitem)
    dublin = marcxml_dictionary_to_dc(pickitem)
    assert dublin

    #TODO: this data munging does not belong here. 

    # one last thing. If this picked item has an 856$9 field, then
    # it's an electronic resource, not a physical item. In that
    # case, we add it as a URL, not a PHYS.
    url = callhook('marcxml_to_url', raw_pickitem)
    if url:
        dct = dict(item_type='URL', url=url)
    else:
        dct = dict(item_type='PHYS')

    try:
        pubdate = dublin.get('dc:date')
        m = re.search('([0-9]+)', pubdate)
        if m:
            pubdate = m.group(1)
    except:
        pubdate = ''

    item = site.item_set.create(parent_heading=parent_item,
                                title=dublin.get('dc:title','Untitled'),
                                author=dublin.get('dc:creator'),
                                publisher=dublin.get('dc:publisher',''),
                                published=pubdate,
                                marcxml=unicode(ET.tostring(raw_pickitem)),
                                **dct)
    item.save()
