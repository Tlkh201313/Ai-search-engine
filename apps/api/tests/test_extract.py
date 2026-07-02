from app.fetch.extract import extract

_HTML = """
<html>
<head>
  <title>Fallback Title</title>
  <meta property="og:title" content="Real Title" />
  <meta name="description" content="A short description." />
  <meta name="author" content="Jane Doe" />
  <meta property="article:published_time" content="2024-03-15T10:00:00Z" />
  <link rel="canonical" href="https://example.com/canonical" />
</head>
<body>
  <nav>menu junk</nav>
  <article>
    <h1>Main Heading</h1>
    <p>This is the first real paragraph of readable body content for extraction.</p>
    <p>This is a second substantial paragraph with more useful information inside.</p>
  </article>
  <footer>footer junk</footer>
  <script>var x = 1;</script>
</body>
</html>
"""


def test_extract_metadata_and_text():
    result = extract(_HTML, "https://example.com/page", max_chars=5000)
    assert result.title == "Real Title"
    assert result.description == "A short description."
    assert result.author == "Jane Doe"
    assert result.published_at.startswith("2024-03-15")
    assert result.canonical == "https://example.com/canonical"
    assert "readable body content" in result.text
    # Boilerplate removed.
    assert "menu junk" not in result.text
    assert "footer junk" not in result.text
    assert "var x" not in result.text


def test_extract_respects_max_chars():
    result = extract(_HTML, "https://example.com/page", max_chars=20)
    assert len(result.text) <= 20
