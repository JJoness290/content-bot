from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AssetStrategy:
    niche: str
    topic: str
    angle: str
    intent: str
    monetization_type: str
    keywords: tuple[str, ...]
    affiliate_placeholders: tuple[str, str]


_STRATEGIES = (
    AssetStrategy(
        niche="VPN",
        topic="NordVPN vs Surfshark: Which VPN Is Better in 2026?",
        angle="buyer-focused comparison for VPN shoppers",
        intent="comparison",
        monetization_type="affiliate",
        keywords=("NordVPN", "Surfshark", "VPN comparison", "best VPN 2026"),
        affiliate_placeholders=("[NordVPN – Official Site]", "[Surfshark – Official Site]"),
    ),
    AssetStrategy(
        niche="Personal Finance Apps",
        topic="Best Personal Finance Apps in 2026: Simple Tools for Daily Money Tracking",
        angle="intent-driven shortlist for everyday budgeting",
        intent="best-of",
        monetization_type="affiliate",
        keywords=("best personal finance apps", "money tracking app", "budgeting tools"),
        affiliate_placeholders=("[YNAB – Official Site]", "[Monarch – Official Site]"),
    ),
    AssetStrategy(
        niche="Budgeting Tips",
        topic="Budgeting Tips That Actually Work in 2026: A Simple Weekly System",
        angle="intent-driven guide for beginners",
        intent="best-of",
        monetization_type="affiliate",
        keywords=("budgeting tips", "weekly budget", "saving money basics"),
        affiliate_placeholders=("[YNAB – Official Site]", "[Monarch – Official Site]"),
    ),
    AssetStrategy(
        niche="Investing Basics",
        topic="Investing Basics in 2026: A Plain-English Starter Guide",
        angle="intent-driven primer for cautious beginners",
        intent="best-of",
        monetization_type="affiliate",
        keywords=("investing basics", "how to start investing", "beginner investing guide"),
        affiliate_placeholders=("[Vanguard – Official Site]", "[Fidelity – Official Site]"),
    ),
)


def choose_strategy(now: datetime | None = None) -> AssetStrategy:
    if not now:
        now = datetime.utcnow()
    index = now.toordinal() % len(_STRATEGIES)
    return _STRATEGIES[index]
