# EPG with dark-background logos

[epgshare01](https://epgshare01.online)'s Canada (`CA2`) and US (`US2`) guides merged into one file,
with each channel's logo swapped for the version drawn for dark backgrounds, for apps with a dark guide
such as TiviMate.

**EPG URL:** `https://thomasmihaljevic27.github.io/epg-dark-logos/epg.xml.gz`

Rebuilt twice a day by GitHub Actions. Listings and channel IDs are epgshare01's, unchanged.

## How

epgshare01 links Gracenote's logo for light backgrounds, e.g. `…/s73963_ll_h15_aa.png`. Gracenote serves
a dark-background version of the same logo with `ld` in place of `ll`. [build.py](build.py) swaps every
logo that has one (about 99% of them). A few channels whose Gracenote logo has no dark version use a
logo from [tv-logo/tv-logos](https://github.com/tv-logo/tv-logos) instead (`OVERRIDES` in build.py).

Logos are the trademarks of their networks; this file only links to them.
