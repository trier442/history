#!/usr/bin/env python3
"""Generate the Naver-compatible RSS feed from representative learning pages."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://moduhistory.com"
KST = timezone(timedelta(hours=9))
PUBLISHED = datetime(2026, 7, 18, 12, 0, tzinfo=KST)
BUILT = datetime(2026, 7, 19, 2, 30, tzinfo=KST)

# RSS is for recent representative content; sitemap.xml contains every page.
FEED_PATHS = [
    Path("history/hv2/hv2 2-2.html"),
    Path("history/hv2/hv2 2-3.html"),
    *[Path(f"history/st2026/st{number}.html") for number in range(1, 16)],
    Path("social/vwh/unit01_01_human_civilization.html"),
    Path("social/vwh/unit01_02_india_east_asia.html"),
    Path("social/vwh/unit01_03_western_world.html"),
    Path("social/vwh/unit02_01_islam_mongol.html"),
    Path("social/vwh/unit02_02_new_routes_fiscal_military.html"),
    Path("social/vwh/unit02_03_global_trade.html"),
    Path("social/vwh/unit03_01_empires.html"),
    Path("social/vwh/unit03_02_citizen_revolutions.html"),
    Path("social/vwh/unit03_03_industrial_imperialism.html"),
    Path("social/vwh/unit03_04_nation_building_movements.html"),
    Path("social/vwh/unit04_01_world_wars.html"),
    Path("social/vwh/unit04_02_cold_war_post_cold_war.html"),
    Path("social/vwh/unit04_03_global_issues.html"),
]


class VisibleText(HTMLParser):
    SKIP_TAGS = {"head", "script", "style", "nav", "footer"}
    BLOCK_TAGS = {"article", "div", "h1", "h2", "h3", "h4", "li", "p", "section", "summary", "table", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.editorial_aside = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in self.SKIP_TAGS:
            self.skip += 1
        elif attributes.get("id") == "site-editorial-note":
            self.skip += 1
            self.editorial_aside += 1
        elif not self.skip and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self.skip:
            self.skip -= 1
        elif tag == "aside" and self.editorial_aside:
            self.skip -= 1
            self.editorial_aside -= 1
        elif not self.skip and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def page_title(document: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", document, re.I | re.S)
    if not match:
        raise ValueError("Page has no title")
    title = re.sub(r"<[^>]+>", "", match.group(1))
    return html.unescape(title).strip()


def page_url(path: Path) -> str:
    return f"{BASE_URL}/{quote(path.as_posix(), safe='/')}"


def add_text(parent: ET.Element, name: str, text: str, **attributes: str) -> ET.Element:
    element = ET.SubElement(parent, name, attributes)
    element.text = text
    return element


def main() -> None:
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    add_text(channel, "title", "모두의 사탐 최신 학습자료")
    add_text(channel, "link", f"{BASE_URL}/")
    add_text(channel, "description", "한국사와 세계사를 중심으로 한 모두의 사탐 최신 웹 학습지")
    add_text(channel, "language", "ko-KR")
    add_text(channel, "lastBuildDate", format_datetime(BUILT))
    ET.SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        {"href": f"{BASE_URL}/rss.xml", "rel": "self", "type": "application/rss+xml"},
    )

    for relative in FEED_PATHS:
        path = ROOT / relative
        document = path.read_text(encoding="utf-8")
        parser = VisibleText()
        parser.feed(document)
        content = parser.text()
        if not content:
            raise ValueError(f"No visible content extracted from {relative}")
        url = page_url(relative)
        item = ET.SubElement(channel, "item")
        add_text(item, "title", page_title(document))
        add_text(item, "link", url)
        add_text(item, "description", content)
        add_text(item, "pubDate", format_datetime(PUBLISHED))
        add_text(item, "guid", url, isPermaLink="true")

    ET.indent(rss, space="  ")
    tree = ET.ElementTree(rss)
    tree.write(ROOT / "rss.xml", encoding="utf-8", xml_declaration=True)
    print(f"Generated rss.xml with {len(FEED_PATHS)} items")


if __name__ == "__main__":
    main()
