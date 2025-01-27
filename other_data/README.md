This data is used to backfill Firefox statistics from v68 to v127.

`hg-changesets.json` is derived from
[product-details](https://product-details.mozilla.org/1.0/l10n/), and includes
the list of changesets used to build Firefox. Changesets are from Mercurial
repositories in [l10n-central](https://hg.mozilla.org/l10n-central).

`hg-commits.json` includes the commit information (date, commit message) for each
hg changeset.

`git-commits.json` includes the best guess for the respective git commits from
[firefox-l10n](https://github.com/mozilla-l10n/firefox-l10n) (a monorepo
generated from individual hg repositories).
