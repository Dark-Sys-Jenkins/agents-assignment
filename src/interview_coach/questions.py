"""Curated interview question plans by role and experience level."""

from __future__ import annotations

from typing import Final

QuestionPlan = tuple[str, ...]

QUESTION_BANK: Final[dict[str, dict[str, QuestionPlan]]] = {
    "backend engineer": {
        "beginner": (
            "Describe how an HTTP request travels from a client to a web service.",
            "How would you validate input before saving it to a database?",
            "Tell me about a bug you investigated and how you narrowed down its cause.",
            "What would you check first if an endpoint suddenly became "
            "slow?",
        ),
        "intermediate": (
            "Design an API endpoint for creating an order while preventing "
            "duplicate submissions.",
            "How would you investigate and reduce latency in a service "
            "backed by a database?",
            "Describe a production issue you would expect from a cache and "
            "how you would diagnose it.",
            "How would you make a background job safe to retry after a "
            "partial failure?",
        ),
        "advanced": (
            "Design a multi-region service that must preserve order "
            "consistency during a regional outage.",
            "How would you evolve a high-traffic API without breaking older "
            "clients?",
            "Describe the trade-offs between synchronous and event-driven "
            "service boundaries for a critical workflow.",
            "How would you identify and mitigate cascading failures across "
            "dependent services?",
        ),
    },
    "data analyst": {
        "beginner": (
            "How would you explain the difference between a metric and a dimension?",
            "What checks would you make before trusting a new dataset?",
            "How would you compare conversion rates between two groups?",
            "Tell me about a chart you would use to explain a trend over time.",
        ),
        "intermediate": (
            "A dashboard conversion rate drops after a release. How would "
            "you investigate the change?",
            "How would you design an experiment to evaluate a new "
            "onboarding flow?",
            "What would you do if two trusted data sources disagree on a "
            "key metric?",
            "How would you communicate uncertainty in an analysis to a "
            "non-technical stakeholder?",
        ),
        "advanced": (
            "How would you estimate the causal impact of a product change "
            "when randomization is unavailable?",
            "How would you detect and account for selection bias in an "
            "observational analysis?",
            "A company is changing its north-star metric. How would you "
            "validate the proposed replacement?",
            "How would you build a measurement strategy that remains "
            "reliable as a product scales?",
        ),
    },
    "product manager": {
        "beginner": (
            "How would you learn what problem a new feature should solve?",
            "How do you decide what information belongs in a product requirement?",
            "Tell me about a time you had to prioritize competing requests.",
            "How would you tell whether a feature is useful after launch?",
        ),
        "intermediate": (
            "How would you prioritize a customer request that conflicts with the product roadmap?",
            "A feature has high adoption but low retention. What would you investigate?",
            "How would you align engineering, design, and support around a risky launch?",
            "Describe how you would define success metrics for a new workflow.",
        ),
        "advanced": (
            "How would you decide whether to enter a market where customer "
            "demand is still uncertain?",
            "How would you balance near-term revenue goals against a "
            "foundational platform investment?",
            "A key product metric improves while customer complaints "
            "increase. How would you respond?",
            "How would you revise a multi-quarter strategy after a major "
            "change in market conditions?",
        ),
    },
}


def available_roles() -> tuple[str, ...]:
    """Return supported role names in display order."""
    return tuple(QUESTION_BANK)


def available_levels() -> tuple[str, ...]:
    """Return supported experience levels in display order."""
    return tuple(next(iter(QUESTION_BANK.values())))


def get_question_plan(role: str, level: str) -> QuestionPlan:
    """Return the interview questions for a supported role and experience level."""
    normalized_role = role.strip().casefold()
    normalized_level = level.strip().casefold()

    if normalized_role not in QUESTION_BANK:
        roles = ", ".join(available_roles())
        raise ValueError(f"Unsupported role {role!r}. Choose one of: {roles}.")

    levels = QUESTION_BANK[normalized_role]
    if normalized_level not in levels:
        supported_levels = ", ".join(levels)
        raise ValueError(
            f"Unsupported level {level!r} for {normalized_role}. "
            f"Choose one of: {supported_levels}."
        )

    return levels[normalized_level]
