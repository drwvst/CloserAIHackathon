from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import re
import streamlit as st


def _monthly_budget(client_profile: dict[str, Any]) -> float:
    """Calculates the max monthly budget based on a 45% DTI rule."""
    income = float(client_profile.get("income", 0))
    monthly_debt = float(client_profile.get("monthly_debt", 0))
    # Using 45% DTI for better flexibility
    return max((income / 12 * 0.45) - monthly_debt, 0)


def _fit_score(client_profile: dict[str, Any], listing: dict[str, Any]) -> int:
    """Calculates a numerical fit score (1-100) considering HOA and Credit Score."""
    score = 50
    price = float(listing.get("price", 0))
    hoa = float(listing.get("hoa_monthly", 0))
    budget = _monthly_budget(client_profile)

    # Estimate PITI (0.65% of price) + HOA fees
    est_monthly = (price * 0.0065) + hoa if price else 0

    # Budget Fit logic
    if est_monthly > 0 and budget > 0:
        ratio = est_monthly / budget
        if ratio <= 0.85:
            score += 25
        elif ratio <= 1.0:
            score += 10
        elif ratio > 1.15:
            score -= 25
    elif est_monthly > 0 and budget == 0:
        score -= 30

    # Credit Score logic
    credit_score = int(client_profile.get("credit_score", 700))
    if credit_score >= 740:
        score += 15
    elif credit_score < 620:
        score -= 30  # Heavy penalty for subprime scores
    elif credit_score < 680:
        score -= 10

    # Savings logic
    savings = float(client_profile.get("savings", 0))
    if price > 0 and savings >= (price * 0.1):
        score += 15

    return max(min(score, 100), 1)


def _build_prompt(client: dict[str, Any], listing: dict[str, Any], comps: list[dict[str, Any]]) -> str:
    # Handle the key mismatch robustly
    profile = client.get("profile", client.get("financial_profile", client))

    income = float(profile.get("income", 0))
    savings = float(profile.get("savings", 0))
    monthly_debt = float(profile.get("monthly_debt", 0))
    credit_score = profile.get("credit_score", "Unknown")

    client_prefs = client.get("preferences", "No specific lifestyle preferences provided.")
    realtor_notes = client.get("notes", "No additional realtor notes.")

    max_budget = _monthly_budget(profile)
    price = float(listing.get("price", 0))
    hoa = float(listing.get("hoa_monthly", 0))

    # Calculate total monthly including HOA
    est_monthly = (price * 0.0065) + hoa

    year_built = listing.get('year_built', 'Unknown')
    address = f"{listing.get('street')}, {listing.get('city')}, {listing.get('state')}"

    return f"""
You are a High-End Real Estate Strategist & Financial Advisor. Analyze this specific property for your client. 
CRITICAL: You must explicitly evaluate how the Credit Score ({credit_score}) affects mortgage eligibility and how the HOA fees (${hoa:,.0f}/mo) impact the total monthly carry.

### TARGET PROPERTY ###
- **Address: {address}**
- Price: ${price:,.0f}
- HOA Fees: ${hoa:,.0f}/mo
- Estimated Monthly Total (PITI + HOA): ${est_monthly:,.0f}
- Specs: {listing.get('beds')} beds, {listing.get('baths')} baths, {listing.get('sqft', 0):,} sqft
- Year Built: {year_built}

### CLIENT PROFILE ###
- Annual Income: ${income:,.0f}
- Monthly Debt: ${monthly_debt:,.0f}
- Credit Score: {credit_score}
- Available Savings: ${savings:,.0f}
- Target Housing Budget: ${max_budget:,.0f}/month
- Preferences: "{client_prefs}"
- Realtor Notes: "{realtor_notes}"

### MARKET CONTEXT (COMPS) ###
{comps}

### REPORT INSTRUCTIONS ###
Provide a structured report:
1. **EXECUTIVE SUMMARY & VERDICT**: Start with a PASS, CONSIDER, or BUY verdict. Include the property address.
2. **FINANCIAL FEASIBILITY**: Compare costs (including HOA) to budget. Address the credit score impact on financing.
3. **LIFESTYLE & SPECS MATCH**: Evaluate preferences.
4. **MARKET ANALYSIS**: Compare price to comps.
5. **PROPERTY RISK WATCHLIST**: Focus on the year {year_built}.

Keep your tone professional, scannable, and direct.
""".strip()


def _clean_report_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def generate_listing_report(client: dict[str, Any], listing: dict[str, Any], comps: list[dict[str, Any]]) -> dict[
    str, Any]:
    # Robust profile retrieval
    profile = client.get("profile", client.get("financial_profile", client))

    fit_score = _fit_score(profile, listing)
    monthly_budget = _monthly_budget(profile)

    # Monthly cost for the return dict (PITI + HOA)
    hoa = float(listing.get("hoa_monthly", 0))
    est_monthly_cost = (float(listing.get("price", 0)) * 0.0065) + hoa

    address = f"{listing.get('street')}, {listing.get('city')}, {listing.get('state')}"

    report_md: str | None = None
    model_used = "rules-only"

    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None

    if api_key:
        try:
            from openai import OpenAI
            client_api = OpenAI(api_key=api_key)
            prompt = _build_prompt(client, listing, comps)
            response = client_api.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            report_md = _clean_report_markdown(response.choices[0].message.content)
            model_used = "gpt-4o"
        except Exception as e:
            st.warning(f"AI generation failed: {e}")
            report_md = None

    if not report_md:
        comp_lines = "\n".join(
            [f"- {c['street']}: ${c['price']:,.0f} ({c['beds']}bd/{c['baths']}ba)" for c in comps[:3]]
        ) or "- No nearby comparable listings available."

        report_md = _clean_report_markdown(f"""
**Analysis for: {address}**

### Executive Summary
This listing has a **fit score of {fit_score}/100**.

### Fit Assessment
- **Estimated Monthly Cost:** ${est_monthly_cost:,.0f}/mo (Includes HOA).
- **Client Max Budget:** ${monthly_budget:,.0f}/mo.
- **Credit Score Status:** {profile.get('credit_score', 'Unknown')}
- {'The property fits well within budget.' if est_monthly_cost <= monthly_budget else 'The property exceeds recommended limits.'}

### Property Risk Watchlist
- **Age:** Built in {listing.get('year_built')}. {'Immediate inspection of HVAC/Roof recommended.' if listing.get('year_built', 0) < 1995 else 'Verify modern code compliance.'}

### Suggested Nearby Alternatives
{comp_lines}
""".strip())

    return {
        "fit_score": fit_score,
        "estimated_monthly_cost": est_monthly_cost,
        "max_recommended_monthly": monthly_budget,
        "report_markdown": report_md,
        "model_used": model_used,
        "created_at": datetime.now(timezone.utc),
    }