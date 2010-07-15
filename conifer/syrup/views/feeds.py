from _common import *
from django.utils.translation import ugettext as _

#-----------------------------------------------------------------------------
# Site feeds

@public                         # and proud of it!
def site_feeds(request, site_id, feed_type):
    site = get_object_or_404(models.Site, pk=site_id)
    if feed_type == '':
        return g.render('feeds/site_feed_index.xhtml', 
                        site=site)
    else:
        items = site.items()
        def render_title(item):
            return item.title
        if feed_type == 'top-level':
            items = items.filter(parent_heading=None).order_by('-sort_order')
        elif feed_type == 'recent-changes':
            items = items.order_by('-last_modified')
        elif feed_type == 'tree':
            def flatten(nodes, acc):
                for node in nodes:
                    item, kids = node
                    acc.append(item)
                    flatten(kids, acc)
                return acc
            items = flatten(site.item_tree(), [])
            def render_title(item):
                if item.parent_heading:
                    return '%s :: %s' % (item.parent_heading.title, item.title)
                else:
                    return item.title
        lastmod = items and max(i.last_modified for i in items) or datetime.now()
        resp = g.render('feeds/site_atom.xml',
                        site=site,
                        feed_type=feed_type,
                        lastmod=lastmod,
                        render_title=render_title,
                        items=items,
                        root='http://%s' % request.get_host(),
                        _serialization='xml')
        resp['Content-Type'] = 'application/atom+xml'
        return resp



