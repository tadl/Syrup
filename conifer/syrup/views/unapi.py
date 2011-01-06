from lxml import etree

from _common import *

stylesheet = etree.parse(
    file(HERE('templates/unapi/MARC21slim2MODS3-3.xsl')))

xform = etree.XSLT(stylesheet)

def unapi(request):
    id = request.GET.get('id')
    if not id:
        return g.render_xml('unapi/formats.xml', item=None)
    item = get_object_or_404(models.Item, pk=id)
    format = request.GET.get('format')
    if not format:
        return g.render_xml('unapi/formats.xml', item=item)
    print (format, item.item_type)
    if format=='mods3':
        xml = item.marcxml
        if xml:
            doc = etree.fromstring(xml)
            mods = xform(doc)
            return HttpResponse(etree.tostring(mods), 
                                content_type='application/xml')
    elif format=='ris':
        # for non-physical items (so we have no MARC to MODS-ify)
        # FIXME: This is probably broken in a jillion ways. 
        ris = []
        a = ris.append
        a('TY  - JOUR')         # FIXME, should not be hardcoded.
        a('ID  - %s' % item.id)
        a('T1  - %s' % item.title)
        if item.source_title:
            a('JF  - %s' % item.source_title)
        if item.author:
            for author in [x.strip() for x in item.author.split(';')]:
                a('A1  - %s' % author)
        if item.volume:
            a('VL  - %s' % item.volume)
        if item.issue:
            a('IS  - %s' % item.issue) 
        if item.publisher:
            a('PB  - %s' % item.publisher)
        if item.published:
            m = re.search(r'(\d{4})', item.published)
            if m:
                year = m.group(1)
                a('PY  - %s///' % year)
        if item.pages:
            pages = re.findall(r'(\d+)', item.pages)
            if len(pages) > 0:
                a('SP  - %s' % pages[0])
            if len(pages) > 1:
                a('EP  - %s' % pages[1])
        a('UR  - %s' % (item.url or item.item_url()))
        a('ER  - ')
        ris = '\n'.join(ris)
        print ris
        return HttpResponse(ris, content_type='text/plain')


    return HttpResponseNotFound()

