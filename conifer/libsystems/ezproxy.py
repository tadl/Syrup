import re
from xml.etree import ElementTree
from urllib    import urlencode
from urllib2   import *


class EZProxyService(object):

    def __init__(self, host, password, strict=False):
        self.host = host
        self.password = password
        self.query_url = 'http://%s/proxy_url' % host
        self.strict = strict

    def proxify(self, url):
        if not url:             # empty or blank
            return None
        if not self.strict:
            # If the hostname is in the URL, assume it has already
            # been proxified.
            if self.host in url:
                return None
        xml = ('<proxy_url_request password="%s">'
               '<urls><url>%s</url>'
               '</urls></proxy_url_request>') % (
            self.password, url)
        data = urlencode({'xml':xml})
        resp = urlopen(self.query_url, data).read()
        root = ElementTree.fromstring(resp)
        node = root.find('proxy_urls/url')
        needs_proxy = (node.attrib.get('proxy') == 'true')
        if needs_proxy:
            return self.translate(url, **node.attrib)

    pat = re.compile(r'(.*://[^/]+)(.*)$')

    def translate(self, url, **kwargs):
        prefix, suffix = self.pat.match(url).groups()
        return ''.join((prefix, '.', self.host, suffix))
    


host = 'ezproxy.uwindsor.ca'
pwd = 'leddy'
s = EZProxyService(host, pwd)

print s.proxify('http://jstor.org/')
print s.proxify('http://jstor.org.ezproxy.uwindsor.ca/')
