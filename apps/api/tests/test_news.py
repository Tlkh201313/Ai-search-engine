"""News feed parsing: RSS 2.0, Atom, thumbnails, dates, interleaving."""

from __future__ import annotations

from app.news.feeds import NewsItem, interleave, parse_feed

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>BBC News</title>
    <item>
      <title>First &amp; biggest story</title>
      <link>https://www.bbc.co.uk/news/one</link>
      <description><![CDATA[<p>Some <b>bold</b> summary here.</p>]]></description>
      <pubDate>Wed, 02 Jul 2026 10:00:00 GMT</pubDate>
      <media:thumbnail width="240" url="https://img.example/small.jpg"/>
      <media:thumbnail width="976" url="https://img.example/big.jpg"/>
    </item>
    <item>
      <title>Second story</title>
      <link>https://www.bbc.co.uk/news/two</link>
      <description>Plain text summary</description>
      <pubDate>Wed, 02 Jul 2026 09:00:00 GMT</pubDate>
      <enclosure url="https://img.example/enc.jpg" type="image/jpeg"/>
    </item>
    <item>
      <title></title>
      <link>https://www.bbc.co.uk/news/broken</link>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>The Verge</title>
  <entry>
    <title>Atom entry title</title>
    <link rel="alternate" type="text/html" href="https://www.theverge.com/a"/>
    <summary type="html">&lt;p&gt;Atom summary&lt;/p&gt;</summary>
    <published>2026-07-02T08:30:00Z</published>
  </entry>
</feed>
"""


def test_parse_rss_basics() -> None:
    items = parse_feed(RSS_SAMPLE, "BBC News")
    assert len(items) == 2  # titleless entry dropped
    first = items[0]
    assert first.title == "First & biggest story"
    assert first.url == "https://www.bbc.co.uk/news/one"
    assert first.source == "BBC News"
    assert first.domain == "bbc.co.uk"
    assert "bold summary" in first.summary and "<" not in first.summary
    assert first.image == "https://img.example/big.jpg"  # widest thumbnail wins
    assert first.published_at is not None and first.published_at.startswith("2026-07-02T10:00")
    assert items[1].image == "https://img.example/enc.jpg"  # enclosure fallback


def test_parse_atom_basics() -> None:
    items = parse_feed(ATOM_SAMPLE, "The Verge")
    assert len(items) == 1
    item = items[0]
    assert item.title == "Atom entry title"
    assert item.url == "https://www.theverge.com/a"
    assert item.summary == "Atom summary"
    assert item.published_at is not None and item.published_at.startswith("2026-07-02T08:30")


def test_parse_garbage_returns_empty() -> None:
    assert parse_feed("not xml at all", "X") == []
    assert parse_feed("", "X") == []


def test_interleave_round_robins_sources() -> None:
    a = [NewsItem(title=f"a{i}", url=f"http://a/{i}", source="A", domain="a") for i in range(3)]
    b = [NewsItem(title=f"b{i}", url=f"http://b/{i}", source="B", domain="b") for i in range(1)]
    mixed = interleave([a, b])
    assert [i.title for i in mixed] == ["a0", "b0", "a1", "a2"]
