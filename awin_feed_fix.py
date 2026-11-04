#!/usr/bin/env python3
"""Players Couture - Awin feed fixer.

Matrixify's product export only writes the product metafields (description_plain,
brand, gender, material, delivery cost, Google title, labels, etc.) on the FIRST row of
each product, so every other size/colour row reached Awin blank.

This script:
  1. copies product-level metafield values down onto every variant row of that product
  2. fills safe defaults where a product never had the value (brand, currency, delivery
     cost, language, ships from, in stock, condition, Google category by product type...)
  3. tidies inconsistent values (e.g. "Free UK delivery" -> 0.00, "Y" -> Yes, "FALSE" -> no)
  4. keeps the column order exactly the same, so the Awin column mapping is unchanged
  5. writes a gzipped CSV (and a plain CSV if a second output path ends in .csv)

It only changes the feed file, never the store.
Usage: python3 awin_feed_fix.py <matrixify_export.csv> <out.csv.gz> [out.csv]
"""
import csv, gzip, sys, collections

csv.field_size_limit(10**9)
src, outs = sys.argv[1], sys.argv[2:]

DEFAULTS = {
    'brand_name': 'Players Couture', 'currency': 'GBP', 'delivery_time': '3-5 working days',
    'delivery_cost': '0.00', 'brand_id': '125396', 'language': 'en-GB',
    'promotional_text': 'Made to Order | Free UK Delivery | Sustainable Fashion',
    'gtin_exempt': 'yes', 'identifier_exists': 'no', 'ships_from': 'GB', 'in_stock': 'Yes',
    'pre_order': 'No', 'condition': 'new', 'made_to_order': 'Yes',
}
NORMALISE = {
    'delivery_cost': {'free uk delivery': '0.00', 'free': '0.00', '0': '0.00'},
    'brand_id': {'players couture': '125396'},
    'language': {'english': 'en-GB', 'en': 'en-GB'},
    'gtin_exempt': {'yes': 'yes', 'true': 'yes'},
    'identifier_exists': {'false': 'no', 'no': 'no', 'true': 'yes', 'yes': 'yes'},
    'ships_from': {'united kingdom': 'GB', 'uk': 'GB', 'gb': 'GB'},
    'in_stock': {'y': 'Yes', 'yes': 'Yes', 'n': 'No', 'no': 'No'},
    'pre_order': {'n': 'No', 'no': 'No', 'y': 'Yes', 'yes': 'Yes'},
    'condition': {'new': 'new'},
    'made_to_order': {'made to order': 'Yes', 'yes': 'Yes'},
    'google_product_category': {'apparel & accessories > clothing > shirts & tops': '212',
                                'apparel & accessories > clothing > outerwear': '203'},
}

def key_of(h):
    # "Metafield: custom.brand_name [single_line_text_field]" -> "brand_name"
    return h.split('Metafield: ', 1)[1].split(' ')[0].split('.', 1)[-1]

def clean(k, v):
    v = v.replace('–', '-').replace('—', '-')
    m = NORMALISE.get(k)
    if m and v.strip().lower() in m:
        v = m[v.strip().lower()]
    return v

def rows_of(path):
    f = open(path, newline='', encoding='utf-8')
    r = csv.reader(f)
    return next(r), r

# pass 1: most common Google category per product Type (for products missing one)
hdr, r = rows_of(src)
mf = {i: key_of(h) for i, h in enumerate(hdr) if h.startswith('Metafield:')}
iid, itype = hdr.index('ID'), hdr.index('Type')
igpc = next(i for i, k in mf.items() if k == 'google_product_category')
irec = next((i for i, k in mf.items() if k == 'recipient'), None)
bytype, prev = collections.defaultdict(collections.Counter), None
for row in r:
    if row[iid] != prev:
        prev = row[iid]
        g = clean('google_product_category', row[igpc])
        if g.strip():
            bytype[row[itype]][g] += 1
cat_for_type = {t: c.most_common(1)[0][0] for t, c in bytype.items()}

# pass 2: fill down, default, normalise, write
hdr, r = rows_of(src)
fhs = []
for o in outs:
    fh = gzip.open(o, 'wt', newline='', encoding='utf-8', compresslevel=6) if o.endswith('.gz') else open(o, 'w', newline='', encoding='utf-8')
    w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator='\n'); w.writerow(hdr); fhs.append((fh, w))
stats = collections.Counter()
cur_id, cur = None, None
for row in r:
    stats['rows'] += 1
    if row[iid] != cur_id:
        cur_id = row[iid]
        cur = {}
        for i, k in mf.items():
            v = clean(k, row[i])
            if not v.strip():
                if k in DEFAULTS:
                    v = DEFAULTS[k]; stats['defaulted'] += 1
                elif k == 'google_product_category':
                    v = cat_for_type.get(row[itype], ''); stats['category_by_type'] += bool(v)
                elif k == 'recipient':
                    v = 'Kids' if 'kid' in row[itype].lower() else 'Adults'; stats['defaulted'] += 1
            cur[i] = v
    for i, v in cur.items():
        if row[i] != v:
            if not row[i].strip(): stats['filled'] += 1
            row[i] = v
    for _, w in fhs:
        w.writerow(row)
for fh, _ in fhs:
    fh.close()
print(dict(stats))
