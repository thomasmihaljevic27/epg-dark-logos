#!/usr/bin/env python3
"""epgshare01's Canada and US guides, merged, with channel logos for dark backgrounds.

epgshare01 links each channel's Gracenote logo in its light-background version (…/s73963_ll_h15_aa.png).
Gracenote also serves a dark-background version at the same address with "ld" for "ll", which reads well
in a dark guide such as TiviMate's. This swaps each logo for that version when Gracenote has it, keeps the
original otherwise, and writes one merged guide to site/epg.xml.gz. Listings are untouched.

Usage: python build.py [CA2 US2 ...]   (epgshare01 file names; default CA2 US2). Standard library only.
"""
import concurrent.futures
import gzip
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

SOURCE = "https://epgshare01.online/epgshare01/epg_ripper_{}.xml.gz"
UA = {"User-Agent": "epg-dark-logos (github.com/thomasmihaljevic27/epg-dark-logos)"}
# A Gracenote logo for light backgrounds: station, height class, revision.
LIGHT = re.compile(r"(https?://dtil\.tmsimg\.com/assets/)(s\d+)_ll_(h\d+)_([a-z]{2})(\.png)")
# Channels whose Gracenote logo has no dark version (another URL style, a placeholder, or none at all):
# a dark-background logo from github.com/tv-logo/tv-logos instead.
TV_LOGOS = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/"
OVERRIDES = {
    "TVO.ca2": "canada/tvo-ca.png",
    "AdultSwim.com.Cartoon.Network.us2": "united-states/adult-swim-us.png",
    "The.Weather.Network.Canada.HD.ca2": "canada/the-weather-network-ca.png",
    "ABC.National.Feed.us2": "united-states/abc-white-us.png",
    "MS.NOW.HD.us2": "united-states/ms-now-us.png",
    "CNBC.HD.us2": "united-states/cnbc-us.png",
    "CNBC.Canadian.Feed.ca2": "united-states/cnbc-us.png",
    "CTV.News.Channel.ca2": "canada/ctv-news-ca.png",
    "CTV.News.Channel.HD.ca2": "canada/ctv-news-ca.png",
    "ABC.News.Live.us2": "united-states/abc-news-live-light-hz-us.png",
    "Comedy.Central.HD.us2": "united-states/comedy-central-us.png",
    "Comedy.Central.HD.(Pacific).us2": "united-states/comedy-central-us.png",
    "TSN.2.ca2": "https://dtil.tmsimg.com/assets/s61474_ll_h15_aa.png",
    "TSN.2.HD.ca2": "https://dtil.tmsimg.com/assets/s61474_ll_h15_aa.png",
    "TNT.HD.us2": "united-states/tnt-us.png",
}


def fetch(name):
    with urllib.request.urlopen(urllib.request.Request(SOURCE.format(name), headers=UA), timeout=300) as r:
        return gzip.decompress(r.read()).decode("utf-8")


def exists(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def dark_version(match):
    """The dark-background logo for a light one: same size and revision, else revision aa, else None."""
    base, station, height, rev, ext = match
    for candidate_rev in dict.fromkeys((rev, "aa")):
        url = f"{base}{station}_ld_{height}_{candidate_rev}{ext}"
        if exists(url):
            return url
    return None


# The playlist carries these local affiliates, including their local newscasts.
AFFILIATES = {
    "WBNS-DT.us_locals1": ("CBS Columbus OH WBNS", "WBNS Columbus (CBS)", "cbs-logo-white-us"),
    "WPMT-DT.us_locals1": ("Fox 43", "WPMT Harrisburg (Fox)", "fox-us"),
    "WABC-DT.us_locals1": ("ABC New York NY WABC", "WABC New York (ABC)", "abc-white-us"),
    "WXIA-DT.us_locals1": ("NBC Atlanta GA WXIA", "WXIA Atlanta (NBC)", "nbc-us"),
}


def affiliates(stream):
    """Read only the requested stations from the much larger locals guide."""
    events = ET.iterparse(stream, events=("start", "end"))
    _, root = next(events)
    channels, programmes = [], []
    for event, node in events:
        if event != "end" or node.tag not in ("channel", "programme"):
            continue
        is_channel = node.tag == "channel"
        attr = "id" if is_channel else "channel"
        station = AFFILIATES.get(node.get(attr))
        if station:
            channel_id, name, logo = station
            node.set(attr, channel_id)
            if is_channel:
                for old in node.findall("icon"):
                    node.remove(old)
                node.find("display-name").text = name
                ET.SubElement(node, "icon", src=TV_LOGOS + "united-states/" + logo + ".png")
            (channels if is_channel else programmes).append(ET.tostring(node, encoding="unicode"))
        root.remove(node)
    if len(channels) != len(AFFILIATES) or not programmes:
        raise ValueError("Local affiliate listings missing")
    return "".join(channels), "".join(programmes)


# Exact playlist IDs let TiviMate use the matching artwork automatically.
# Keep the original IDs for viewers who already assigned them manually.
PLAYLIST_IDS = {
    "TVO.ca2": "TVO Kids",
    "ABC.News.Live.us2": "ABC News24 HD",
    "Comedy.Central.HD.us2": "Comedy Central US",
    "CNBC.HD.us2": "CNBC US",
    "TNT.HD.us2": "Turner Network TV HD",
}


def add_playlist_ids(guide):
    ids = "|".join(map(re.escape, PLAYLIST_IDS))
    for tag, attribute in (("channel", "id"), ("programme", "channel")):
        pattern = rf'(<{tag}\b[^>]*? {attribute}=")({ids})(".*?</{tag}>)'
        def duplicate(match):
            before, source, after = match.groups()
            return match[0] + "\n" + before + PLAYLIST_IDS[source] + after
        guide = re.sub(pattern, duplicate, guide, flags=re.S)
    return guide


def main():
    names = sys.argv[1:] or ["CA2", "US2"]
    guides = [fetch(n) for n in names]
    lights = {m.group(0): m.groups() for g in guides for m in LIGHT.finditer(g)}
    with concurrent.futures.ThreadPoolExecutor(32) as pool:
        darks = dict(zip(lights, pool.map(dark_version, lights.values())))
    swap = {url: dark for url, dark in darks.items() if dark}
    print(f"{len(swap)} of {len(lights)} logos have a dark-background version")

    def replace(m):
        return swap.get(m.group(0), m.group(0))

    def override(g):
        for cid, path in OVERRIDES.items():
            block = re.compile(r'(<channel id="%s">)(.*?)(</channel>)' % re.escape(cid), re.S)
            url = path if path.startswith("https://") else TV_LOGOS + path
            icon = f'<icon src="{url}" />'
            g = block.sub(lambda m: m.group(1) + re.sub(r"<icon [^>]*/>", "", m.group(2)) + icon + m.group(3), g)
        return g

    # One <tv> holding every guide's channels and programmes; the channel ids (…ca2, …us2) don't overlap.
    inner = [re.search(r"<tv[^>]*>(.*)</tv>", add_playlist_ids(override(LIGHT.sub(replace, g))), re.S).group(1) for g in guides]
    req = urllib.request.Request(SOURCE.format("US_LOCALS1"), headers=UA)
    with urllib.request.urlopen(req, timeout=300) as response, gzip.GzipFile(fileobj=response) as stream:
        local_channels, local_programmes = affiliates(stream)
    head = re.search(r"^.*?<tv[^>]*>", guides[0], re.S).group(0)
    os.makedirs("site", exist_ok=True)
    with gzip.open(os.path.join("site", "epg.xml.gz"), "wt", encoding="utf-8") as out:
        out.write(head)
        out.write(local_channels)
        # XMLTV readers expect all channel definitions before the first programme.
        sections = [part.partition("<programme ") for part in inner]
        for channels, marker, _ in sections:
            if not marker:
                raise ValueError("Guide has no programmes")
            out.write(channels)
        for _, marker, programmes in sections:
            out.write(marker)
            out.write(programmes)
        out.write(local_programmes)
        out.write("</tv>\n")
    print("wrote site/epg.xml.gz", os.path.getsize(os.path.join("site", "epg.xml.gz")), "bytes")


if __name__ == "__main__":
    main()
