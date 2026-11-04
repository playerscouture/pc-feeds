# pc-feeds

Public product feeds for Players Couture.

## Awin feed

`awin_feed_fix.py` takes the daily Matrixify Awin export and copies the product-level
fields (description, brand, gender, material, delivery cost, Google title, labels and
category) onto every size and colour row, fills safe defaults and tidies values.
The column order is unchanged, so the Awin mapping stays the same.

The workflow in `.github/workflows/awin-feed.yml` runs hourly from 07:17 to 20:17 UTC,
rebuilds the feed when a new Matrixify file appears and publishes it here:

https://github.com/playerscouture/pc-feeds/releases/download/awin-latest/awin-feed.csv.gz

Secret needed: `MATRIXIFY_AWIN_URL` = the permanent Matrixify link to the latest Awin export.
