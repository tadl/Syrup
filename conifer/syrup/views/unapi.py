from lxml import etree

from _common import *

stylesheet = etree.parse(
    file(HERE('templates/unapi/MARC21slim2MODS3-3.xsl')))

xform = etree.XSLT(stylesheet)

def unapi(request):
    id = request.GET.get('id')
    format = request.GET.get('format')
    if not format:
        return g.render_xml('unapi/formats.xml', id=id)
    elif format=='mods3':
        item = get_object_or_404(models.Item, pk=id)
        xml = item.marcxml
        if xml:
            doc = etree.fromstring(xml)
            mods = xform(doc)
            return HttpResponse(etree.tostring(mods), 
                                content_type='application/xml')
    return HttpResponseNotFound()
