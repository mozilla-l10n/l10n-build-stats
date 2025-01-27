# Firefox backfill (v68 to v127)

This data is used to backfill Firefox statistics from version 68 to 127.

`hg-changesets.json` is generated from
[product-details](https://product-details.mozilla.org/1.0/l10n/), and includes
the list of changesets used to build Firefox. Changesets are from Mercurial
repositories in [l10n-central](https://hg.mozilla.org/l10n-central).

`hg-commits.json` includes the commit information (date, commit message) for each
changeset in `hg-changesets.json`.

For each hg commit in `hg-commits.json`, `git-commits.json` includes the best
match from [firefox-l10n](https://github.com/mozilla-l10n/firefox-l10n) (a
monorepo generated from individual hg repositories).

Scripts are available in [this gist](https://gist.github.com/flodolo/eaed76d43e5c7858ed596a35838eec1d).
