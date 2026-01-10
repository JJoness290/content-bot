from typing import Any

from app.core import notifier


def fetch_summary(url: str) -> dict[str, Any]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        notifier.add_notification(
            "WARNING",
            "Research summary unavailable in Limited Mode. Install dependencies to enable fetching.",
        )
        return {
            "url": url,
            "title": "Limited Mode",
            "summary": ["Research dependencies are not installed."],
        }

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    return {
        "url": url,
        "title": title,
        "summary": paragraphs[:3],
    }
