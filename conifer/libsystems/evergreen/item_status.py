from support import ER, E1

def barcode_to_bib_id(barcode):
    bib_id = (E1('open-ils.search.bib_id.by_barcode', barcode))
    if isinstance(bib_id, basestring): # it would be a dict if barcode not found.
        return bib_id
    else:
        return None

def bib_id_to_marcxml(bib_id):
    return E1('open-ils.supercat.record.marcxml.retrieve', bib_id)

if __name__ == '__main__':
    from pprint import pprint
    print bib_id_to_marcxml(barcode_to_bib_id(31862016799294))
