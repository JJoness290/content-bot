from datetime import datetime
from typing import Iterable
import re

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "your",
    "you",
    "are",
    "into",
    "from",
    "best",
    "guide",
    "vs",
    "2026",
    "how",
    "what",
    "why",
    "will",
    "our",
    "their",
    "about",
    "when",
    "where",
    "which",
    "than",
    "over",
    "more",
    "most",
    "use",
    "using",
    "tips",
    "basics",
    "apps",
    "app",
}


def build_unsplash_url(keywords: list[str], sig: int) -> str:
    query = ",".join(keywords)
    return f"https://source.unsplash.com/1600x900/?{query}&sig={sig}"


def extract_keywords(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = [word for word in cleaned.split() if word and word not in _STOPWORDS]
    unique = []
    for word in words:
        if word not in unique:
            unique.append(word)
        if len(unique) >= 3:
            break
    return unique or ["business", "writing", "strategy"]


def _image_line(section_title: str, topic: str, sig: int) -> str:
    keywords = extract_keywords(f"{section_title} {topic}")
    url = build_unsplash_url(keywords, sig)
    alt_text = " ".join([word.capitalize() for word in keywords]) or section_title
    return f'<img src="{url}" alt="{alt_text}" />'


def _ensure_no_markdown_images(content: str) -> None:
    if "![" in content:
        raise ValueError("Markdown image syntax detected.")
    for line in content.splitlines():
        if line.startswith("https://source.unsplash.com/"):
            raise ValueError("Plain image URLs are not permitted.")


def _pad_paragraphs(text: str, target_words: int) -> str:
    words = len(text.split())
    if words >= target_words:
        return text
    filler = (
        " Consider how the choice affects your daily workflow and whether the pricing "
        "still feels fair after the first month. A reliable option usually saves time "
        "and reduces friction, while a cheaper option can be a smart entry point when "
        "you are still validating the need."
    )
    while len(text.split()) < target_words:
        text += filler
    return text


def generate_medium_blog_post(
    topic: str,
    angle: str,
    keywords: Iterable[str],
    affiliate_placeholders: Iterable[str],
) -> str:
    keyword_text = ", ".join(keywords)
    primary_link, secondary_link = list(affiliate_placeholders)[:2]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    sections = [
        ("Quick verdict", "Summarize who should choose each option and why."),
        ("Comparison snapshot", "Highlight the core differences in a simple checklist."),
        ("Deep dive: Premium option", "Explain where the premium option excels."),
        ("Deep dive: Value option", "Explain where the value option wins on cost or simplicity."),
        ("Best for busy buyers", "Recommend the most reliable, low-effort option."),
        ("Best for budget-conscious buyers", "Recommend the best value choice."),
        ("FAQ", "Answer the most common buyer questions clearly."),
        ("Call to action", "Invite the reader to compare current offers."),
    ]
    sig = 101
    content = f"{topic}\n\n{_image_line(topic, topic, sig)}\n\n"
    sig += 1
    intro = (
        "Choosing the right tool matters because it affects security, speed, and long-term cost. "
        "This guide focuses on real-world decision criteria and helps you pick the best option fast. "
        f"SEO focus: {keyword_text}."
    )
    content += _pad_paragraphs(intro, 170) + "\n\n"
    for title, prompt in sections:
        content += f"{title}\n\n{_image_line(title, topic, sig)}\n\n"
        sig += 1
        body = f"{prompt} Keep the advice neutral and actionable for buyers. {angle}."
        content += _pad_paragraphs(body, 170) + "\n\n"
        if title == "Comparison snapshot":
            content += (
                "| Criteria | Premium option | Value option |\n"
                "|---|---|---|\n"
                "| Pricing | Higher | Lower |\n"
                "| Performance | Consistent | Good |\n"
                "| Support | Strong | Good |\n"
                "| Learning curve | Low | Low |\n\n"
            )
        if title == "FAQ":
            content += (
                "**Is the premium option faster?**\n"
                "Generally yes, especially on longer-distance connections.\n\n"
                "**Which is better for families?**\n"
                "The value option often supports more devices, which is ideal for households.\n\n"
                "**Do they work on mobile?**\n"
                "Yes, both have iOS and Android apps.\n\n"
                "**Which is more private?**\n"
                "The premium option typically has the longer record of audits and privacy commitments.\n\n"
            )
        if title == "Call to action":
            content += (
                "Compare offers and current pricing:\n"
                f"- {primary_link}\n"
                f"- {secondary_link}\n\n"
            )
    content += f"---\n\nDraft metadata: {keyword_text} | {angle} | generated {timestamp}\n"
    _ensure_no_markdown_images(content)
    return content


def generate_autopilot_draft(
    topic: str,
    angle: str,
    keywords: Iterable[str],
    affiliate_placeholders: Iterable[str],
) -> str:
    keyword_text = ", ".join(keywords)
    primary_link, secondary_link = list(affiliate_placeholders)[:2]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    sections = [
        ("Why this comparison matters", "Explain why the decision has real-world impact."),
        ("Quick verdict", "Give a concise recommendation for each type of buyer."),
        ("What to compare (the buyer checklist)", "Provide a short checklist to compare options."),
        ("Premium option: deeper look", "Explain premium advantages and trade-offs."),
        ("Value option: deeper look", "Explain value advantages and trade-offs."),
        ("Use-case recommendations", "Offer clear scenarios to match the reader's needs."),
        ("Practical decision framework", "Give a 3-step decision framework."),
        ("FAQ", "Answer common buying questions."),
        ("Call to action", "Invite the reader to compare offers."),
    ]
    sig = 201
    content = f"{topic}\n\n{_image_line(topic, topic, sig)}\n\n"
    sig += 1
    intro = (
        "If you are comparing options in this space, the goal is simple: pick the product that solves "
        "your core problem without wasting time or money. This draft is built to help a buyer make a "
        "decision quickly, using clear criteria and an honest summary. "
        f"SEO focus: {keyword_text}."
    )
    content += _pad_paragraphs(intro, 220) + "\n\n"
    for title, prompt in sections:
        content += f"{title}\n\n{_image_line(title, topic, sig)}\n\n"
        sig += 1
        body = f"{prompt} Keep the guidance neutral and actionable for buyers. {angle}."
        content += _pad_paragraphs(body, 200) + "\n\n"
        if title == "What to compare (the buyer checklist)":
            content += (
                "- Performance: Does it stay stable at peak times?\n"
                "- Ease of use: Can you set it up in under 10 minutes?\n"
                "- Support: Are answers available when something goes wrong?\n"
                "- Pricing clarity: Are discounts clear, and are renewals fair?\n"
                "- Long-term fit: Will it still feel like a good choice in six months?\n\n"
            )
        if title == "FAQ":
            content += (
                "**Is the premium option worth the price?**\n"
                "If you value reliability and quick support, the premium option often pays for itself.\n\n"
                "**Will the value option handle everyday use?**\n"
                "Yes. For typical use cases, it is often more than enough.\n\n"
                "**How do I decide quickly?**\n"
                "If you want the most dependable option, go premium. If you want value, go value.\n\n"
            )
        if title == "Call to action":
            content += (
                "Check the latest pricing and trial options:\n"
                f"- {primary_link}\n"
                f"- {secondary_link}\n\n"
            )
    content += f"---\n\nDraft metadata: {keyword_text} | {angle} | generated {timestamp}\n"
    _ensure_no_markdown_images(content)
    return content


def generate_custom_medium_article(
    topic: str,
    tone: str,
    length: str,
    audience: str,
    keywords: Iterable[str],
    affiliate_placeholders: Iterable[str],
) -> str:
    keyword_text = ", ".join(keywords)
    primary_link, secondary_link = list(affiliate_placeholders)[:2]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    length_map = {"short": 140, "medium": 180, "long": 220}
    target_words = length_map.get(length, 180)
    sections = [
        ("Why this matters", "Frame the decision and the stakes for the reader."),
        ("Quick verdict", "Give a fast, buyer-friendly recommendation."),
        ("Key differences", "Explain the 3–5 most important differences."),
        ("Pros and cons", "Provide a balanced list of trade-offs."),
        ("Best for", "Match each option to a typical buyer profile."),
        ("FAQ", "Answer common buyer questions."),
        ("Call to action", "Invite the reader to compare current offers."),
    ]
    sig = 301
    content = f"{topic}\n\n{_image_line(topic, topic, sig)}\n\n"
    sig += 1
    intro = (
        f"This guide is written in a {tone} tone for {audience} readers. "
        "It focuses on clear, buyer-ready guidance and practical decision criteria. "
        f"SEO focus: {keyword_text}."
    )
    content += _pad_paragraphs(intro, target_words) + "\n\n"
    for title, prompt in sections:
        content += f"{title}\n\n{_image_line(title, topic, sig)}\n\n"
        sig += 1
        body = f"{prompt} Keep the guidance concise and actionable."
        content += _pad_paragraphs(body, target_words) + "\n\n"
        if title == "Pros and cons":
            content += (
                "- Pros: Reliable performance, clear setup, practical features.\n"
                "- Cons: Pricing may be higher or support may be slower depending on the option.\n\n"
            )
        if title == "FAQ":
            content += (
                "**Is the premium option worth it?**\n"
                "It is often worth it if you value reliability and support.\n\n"
                "**Is the value option good enough?**\n"
                "For most everyday use cases, yes.\n\n"
            )
        if title == "Call to action":
            content += (
                "Compare offers and current pricing:\n"
                f"- {primary_link}\n"
                f"- {secondary_link}\n\n"
            )
    content += f"---\n\nDraft metadata: {keyword_text} | {tone} | {audience} | generated {timestamp}\n"
    _ensure_no_markdown_images(content)
    return content
