# Localization Build Stats

Script to extract completion levels of Firefox and Firefox for Android
from mozilla-unified.

## Data backfills

### Firefox desktop (v68 to v127)

This data is used to backfill Firefox statistics from version 68 to 127.

`other_data/hg-changesets.json` is generated from
[product-details](https://product-details.mozilla.org/1.0/l10n/), and includes
the list of changesets used to build Firefox. Changesets are from Mercurial
repositories in [l10n-central](https://hg.mozilla.org/l10n-central).

`other_data/hg-commits.json` includes the commit information (date, commit message) for each
changeset in `hg-changesets.json`.

For each hg commit in `other_data/hg-commits.json`, `git-commits.json` includes the best
match from [firefox-l10n](https://github.com/mozilla-l10n/firefox-l10n) (a
monorepo generated from individual hg repositories).

Scripts are available in [this gist](https://gist.github.com/flodolo/eaed76d43e5c7858ed596a35838eec1d).

### Firefox for Android (v111 to v125)

Data is generated from the archived GitHub repository
[mozilla-mobile/firefox-android](https://github.com/mozilla-mobile/firefox-android),
using tags as reference (e.g. `fenix-v111.0` for v111).

### Firefox for Android (v79 to v110)

Data is generated from two archived repositories:
* [fenix](https://github.com/mozilla-mobile/fenix)
* [android-components](https://github.com/mozilla-mobile/android-components)

Versions are out of sync, so using the version declared in
`buildSrc/src/main/java/AndroidComponents.kt` within the `fenix` repository.
