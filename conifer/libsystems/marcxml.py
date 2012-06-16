from xml.etree import ElementTree

# Note: the 'record' parameters passed to these functions must be
# Unicode strings, not plain Python strings; or ElementTree instances.

def _to_tree(unicode_or_etree):
    if isinstance(unicode_or_etree, unicode):
        tree = ElementTree.fromstring(unicode_or_etree.encode('utf-8'))
    elif isinstance(unicode_or_etree, ElementTree._ElementInterface):
        tree = unicode_or_etree
    else:
        raise Exception('Bad parameter', unicode_or_etree)
    return tree

def marcxml_to_records(rec):
    tree = _to_tree(rec)
    if tree.tag == '{http://www.loc.gov/MARC21/slim}collection':
        # then we may have multiple records
        records = tree.findall('{http://www.loc.gov/MARC21/slim}record')
    elif tree.tag == '{http://www.loc.gov/MARC21/slim}record':
        records = [tree]
    else:
        return []
    return records
    
def record_to_dictionary(rec, multiples=True):
    tree = _to_tree(rec)
    dct = {}
    for cf in tree.findall('{http://www.loc.gov/MARC21/slim}controlfield'):
        t = cf.attrib['tag']
        if not cf.text is None:
           dct.setdefault(t, []).append(cf.text)
    for df in tree.findall('{http://www.loc.gov/MARC21/slim}datafield'):
        t = df.attrib['tag']
        for sf in df.findall('{http://www.loc.gov/MARC21/slim}subfield'):
            c = sf.attrib['code']
            v = sf.text or ''
            dct.setdefault(t+c, []).append(v)
    try:
        dct = dict((k,'\n'.join(v or [])) for k,v in dct.items())
    except TypeError:
        print "Unable to extract all of the record"
    return dct

def marcxml_to_dictionary(rec, multiples=False):
    tree = _to_tree(rec)
    if tree.tag == '{http://www.loc.gov/MARC21/slim}collection':
        # then we may have multiple records
        records = tree.findall('{http://www.loc.gov/MARC21/slim}record')
    elif tree.tag == '{http://www.loc.gov/MARC21/slim}record':
        records = [tree]
    else:
        return []
    out = []
    for r in records:
        dct = {}
        for cf in r.findall('{http://www.loc.gov/MARC21/slim}controlfield'):
            t = cf.attrib['tag']
            dct.setdefault(t, []).append(cf.text)
        for df in r.findall('{http://www.loc.gov/MARC21/slim}datafield'):
            t = df.attrib['tag']
            for sf in df.findall('{http://www.loc.gov/MARC21/slim}subfield'):
                c = sf.attrib['code']
                v = sf.text or ''
                dct.setdefault(t+c, []).append(v)
        try:
            dct = dict((k,'\n'.join(v or [])) for k,v in dct.items())
        except TypeError:
            print "Unable to extract all of the record"
            
        out.append(dct)
    if multiples is False:
        return out and out[0] or None
    else:
        return out

def marcxml_dictionary_to_dc(dct):
    """Take a dictionary generated by marcxml_to_dictionary, and
    extract some Dublin Core elements from it. Fixme, I'm sure this
    could be way improved."""
    out = {}
    meta = [('245a', 'dc:title'),
            ('260c', 'dc:date'), 
            ('700a', 'dc:contributor')]
    for marc, dc in meta:
        value = dct.get(marc)
        if value:
            out[dc] = value

    pub = [strip_punct(v) for k,v in sorted(dct.items()) if k in ('260a', '260b')]
    if pub:
        out['dc:publisher'] = ': '.join(pub)

    title = [v.strip() for k,v in sorted(dct.items()) if k in ('245a', '245b')]
    if title:
        out['dc:title'] = strip_punct(' '.join(title))

    for k in ('100a', '110a', '700a', '710a'):
        if dct.get(k):
            out['dc:creator'] = strip_punct(dct[k])
            break

    return out

    
def strip_punct(s):
    # strip whitespace and trailing single punctuation characters
    s = s.strip()
    if s and (s[-1] in ',.;:/'):
        s = s[:-1]
    return s.strip()
