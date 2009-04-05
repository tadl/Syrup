from conifer.syrup import models
from django.db.models import Q

#http://www.poromenos.org/node/87. Credit to Poromenos. It's under BSD.
def levenshtein_distance(first, second):
    """Find the Levenshtein distance between two strings."""
    if len(first) > len(second):
        first, second = second, first
    if len(second) == 0:
        return len(first)
    first_length = len(first) + 1
    second_length = len(second) + 1
    distance_matrix = [range(second_length) for x in range(first_length)]
    for i in xrange(1, first_length):
        for j in range(1, second_length):
            deletion = distance_matrix[i-1][j] + 1
            insertion = distance_matrix[i][j-1] + 1
            substitution = distance_matrix[i-1][j-1]
            if first[i-1] != second[j-1]:
                substitution += 1
            distance_matrix[i][j] = min(insertion, deletion, substitution)

    return distance_matrix[first_length-1][second_length-1]

def rank_pending_items(dct):
    title = dct.get('dc:title','')
    author = dct.get('dc:creator','')
    publisher = dct.get('dc:publisher','')
    pubdate  = dct.get('dc:pubdate','')

    # not right... also, prefetch metadata
    all_items = models.Item.objects.select_related('metadata')
    all_pending_items = all_items.filter(Q(item_type='PHYS'), 
                                         ~Q(metadata__name='syrup:barcode'))
    all_pending_items = all_items.filter(Q(item_type='PHYS'), 
                                         ~Q(metadata__name='syrup:barcode',
                                            metadata__value__in=[p.barcode for p in models.PhysicalObject.live_objects()]))
    results = []
    # not sure I like these weights, but let's play a bit.
    METRICS = (('dc:title', 1), ('dc:creator', 1), ('dc:publisher', 0.5), ('dc:pubdate', 0.25))
    for item in all_pending_items:
        scores = []
        for heading, weight in METRICS:
            try:
                ival = item.metadata_set.get(name=heading).value or ''
            except:
                ival = ''
            dist = levenshtein_distance(dct.get(heading) or '', ival)
            scores.append(dist/weight)
        score = sum(scores)
        results.append((score, item))
    results.sort()
    return results
