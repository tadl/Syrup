# After having scraped ERES, the Metadata class can extract items'
# metadata from the the scraped HTML.

from pprint import pprint
import re
import os

class Metadata(object):

    def __init__(self, path):
        self._path = path
        self.html = open(path).read()
        self.localid = re.search(r'item(\d+)', self._path).group(1)
        self._scrape()
        del self.html

    @property
    def data(self):
        return self.__dict__

    def __scrape(self, **kwargs):
        for name, pat in kwargs.items():
            try:
                setattr(self, name, re.search(pat, self.html).group(1).strip())
            except:
                pass

    def _scrape(self):
        self.__scrape(
            title=r'<td align="left" nowrap="nowrap">Title:</td><td align="left" width="100%">(.*?)<',
            source_title=r'<td align="left" nowrap="nowrap">Title Primary:</td><td align="left" width="100%">(.*?)<',
            journal=r'<td align="left" nowrap="nowrap">Journal:</td><td align="left" width="100%">(.*?)<',
            volume=r'<td align="left" nowrap="nowrap">Volume:</td><td align="left" width="100%">(.*?)<',
            issue=r'<td align="left" nowrap="nowrap">Issue:</td><td align="left" width="100%">(.*?)<',
            author=r'<td align="left" nowrap="nowrap">Author Primary:</td><td align="left" width="100%">(.*?)<',
            author2=r'<td align="left" nowrap="nowrap">Author Secondary:</td><td align="left" width="100%">(.*?)<',
            pages='<td align="left" nowrap="nowrap">Page Range / Chapter:</td><td align="left" width="100%">(.*?)<',
            publisher='<td align="left" nowrap="nowrap">Publisher:</td><td align="left" width="100%">(.*?)<',
            published='<td align="left" nowrap="nowrap">Date Published:</td><td align="left" width="100%">(.*?)<',
            course='<td class="HEADER1" valign="middle" align="left" height="25">&nbsp;&nbsp;(.*?) -',
            instructor='<td class="HEADER1" valign="middle" align="left" height="25">&nbsp;&nbsp;.*? - .*? - (.*?)<',
            term='<td class="HEADER1" valign="middle" align="left" height="25">&nbsp;&nbsp;.* - .* \((.*?)\)',
            )
        if hasattr(self, 'journal'):
            self.source_title = self.journal
            del self.journal

        pat = re.compile(r"""onClick="javascript:popall\('(.*?)'.*?">Click here for more information</a>""")
        m = pat.search(self.html)
        if m:
            self.type = 'url'
            self.url = m.group(1)
        else:
            pat = re.compile(r"""onClick="javascript:pop\('(download.aspx\?docID=(\d+)&shortname=(.*?))'""")
            m = pat.search(self.html)
            if m:
                self.type = 'file'
                urlpath, itemid, origfile = m.groups()
                self.filename = origfile
                datafile = re.sub(r'(.*)/item(\d+).html', 
                                  r'\1/data\2', self._path)
                datafile = os.path.abspath(datafile)
                self.datafile = datafile

    @property
    def mimetype(self):
        assert self.datafile
        with os.popen('file -i ' + self.datafile) as f:
            tmp = f.readline()
        try:
            return re.search(r': (\w+/\w+);', tmp).group(1)
        except:
            return None
        

    @classmethod
    def find_all(cls, path):
        for name in os.popen('find "%s" -name "item0*.html"' % path).readlines():
            yield Metadata(name.strip())

if __name__ == '__main__':
    for m in Metadata.find_all('data/'):
        #pprint(m.data)
        if m.type == 'file':
            pprint(m.mimetype)
