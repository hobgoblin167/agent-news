import feedparser
import requests
from bs4 import BeautifulSoup

RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"


def fetch_feed():
    feed = feedparser.parse(RSS_URL)

    articles = []

    for entry in feed.entries:
        article_id = entry.get("id") or entry.get("link")

        articles.append({
            "id": article_id,
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published_at": entry.get("published", ""),
            "source": "BBC"
        })

    return articles


def fetch_article_text(article: dict) -> dict:
    try:
        response = requests.get(
            article["url"],
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        paragraphs = soup.find_all("p")

        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in paragraphs
        )

        article["text"] = text[:20000]

    except Exception as e:
        print(f"Failed to load article: {article['title']}")
        print(e)

        article["text"] = ""

    return article