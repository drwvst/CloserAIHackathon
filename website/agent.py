from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import re

import streamlit as st

def _monthly_budget(client_profile: dict[str, Any]) -> float:
    income = float(client_profile.get("income", 0))
    monthly_debt = float(client_profile.get("monthly_debt", 0))
    return max((income / 12 * 0.36) - monthly_debt, 0)


def _fit_score(client_profile: dict[str, Any], listing: dict[str, Any]) -> int:
    score = 50
    price = float(listing.get("price", 0))
    budget = _monthly_budget(client_profile)
    est_monthly = (price * 0.0065) if price else 0

    if est_monthly and budget:
        ratio = est_monthly / budget
        if ratio <= 0.85:
            score += 25
        elif ratio <= 1.0:
            score += 10
        elif ratio > 1.15:
            score -= 20

    credit_score = int(client_profile.get("credit_score", 700))
    if credit_score >= 740:
        score += 10
    elif credit_score < 640:
        score -= 10

    if float(client_profile.get("savings", 0)) >= price * 0.1:
        score += 10

    return max(min(score, 100), 1)


def _build_prompt(client: dict[str, Any], listing: dict[str, Any], comps: list[dict[str, Any]]) -> str:
    return f"""
You are a real-estate analyst assistant for a realtor dashboard.
Given the client profile, listing data, and area comps, produce a concise markdown report with these sections:
1) Executive Summary
2) Fit Assessment
3) Location Intelligence
4) Property Risk Watchlist
5) Suggested Nearby Alternatives (2-3 options from comps)
6) Realtor Next Steps

Client:
{client}

Listing:
{listing}

Area comparables:
{comps}

Important constraints:
- Keep the report concise and scannable with short bullets.
- Do not include follow-up prompts (no "if you'd like", "let me know", or questions to the user).
- Preserve normal spacing and punctuation.
- Be explicit about assumptions and uncertainty when data is inferred.
""".strip()




def _clean_report_markdown(report_md: str) -> str:
    """Normalize occasional malformed spacing/newline artifacts from model output."""
    lines = report_md.splitlines()
    cleaned: list[str] = []
    letter_buffer: list[str] = []

    def flush_letters() -> None:
        if letter_buffer:
            cleaned.append("".join(letter_buffer))
            letter_buffer.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if re.fullmatch(r"[A-Za-z0-9]", line):
            letter_buffer.append(line)
            continue

        flush_letters()
        cleaned.append(raw_line)

    flush_letters()

    text = "\n".join(cleaned)
    text = re.sub(r"\bif you['’]d like\b[^.?!]*[.?!]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(let me know|would you like|can I)\b[^.?!]*[.?!]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_listing_report(client: dict[str, Any], listing: dict[str, Any], comps: list[dict[str, Any]]) -> dict[str, Any]:
    profile = client.get("profile", {})
    fit_score = _fit_score(profile, listing)
    monthly_budget = _monthly_budget(profile)
    est_monthly_cost = float(listing.get("price", 0)) * 0.0065

    report_md: str | None = None
    model_used = "rules-only"

    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    if api_key:
        try:
            from openai import OpenAI

            client_api = OpenAI(api_key=api_key)
            prompt = _build_prompt(client, listing, comps)
            response = client_api.responses.create(
                model="gpt-5-nano",
                input=prompt,
                reasoning={"effort": "low"},
            )
            report_md = _clean_report_markdown(response.output_text)
            model_used = "gpt-5-nano"
        except Exception:
            report_md = None

    if not report_md:
        comp_lines = "\n".join(
            [f"- {c['street']}: ${c['price']:,.0f}, {c['beds']} bd, {c['baths']} ba, {c['sqft']:,} sqft" for c in comps[:3]]
        ) or "- No nearby comparable listings were available at analysis time."
        report_md = _clean_report_markdown(f"""
### Executive Summary
This listing has a **fit score of {fit_score}/100** for this client profile.

### Fit Assessment
- Estimated monthly carrying cost (very rough): **${est_monthly_cost:,.0f}/mo**.
- Client max recommended monthly payment: **${monthly_budget:,.0f}/mo**.
- The final recommendation should be validated with lender pre-approval and full tax/insurance quotes.

### Location Intelligence
- Validate neighborhood crime trends through a local public safety source.
- Review school ratings and district boundaries with official district tools.
- Ask about weather-related historical claims (hail, flooding, wind) in this ZIP.

### Property Risk Watchlist
- If older property, request roof age and permit history.
- Ask for HVAC service records and expected replacement timeline.
- Confirm foundation/water intrusion history and recent inspections.

### Suggested Nearby Alternatives
{comp_lines}

### Realtor Next Steps
1. Verify taxes, HOA dues, and insurance quote.
2. Confirm school assignment and commute time.
3. Request disclosures focused on roof, HVAC, plumbing, and major repairs.
""".strip())

    return {
        "fit_score": fit_score,
        "estimated_monthly_cost": est_monthly_cost,
        "max_recommended_monthly": monthly_budget,
        "report_markdown": report_md,
        "model_used": model_used,
        "created_at": datetime.now(timezone.utc),
    }
