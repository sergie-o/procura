# utils/ai_advisor.py
# ProcureIQ — Claude API Integration for Shipping & Market Advisory

import anthropic
import streamlit as st

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"


def get_shipping_advice(
    from_market: str,
    to_destination: str,
    equipment_list: list,
    include_tyres: bool,
    tyre_condition: str,
    buyer_residency: str,
    shipment_method: str,
    special_notes: str,
    procurement_country: str,
) -> str:
    """Generate detailed shipping, customs, and logistics advice using Claude."""

    equipment_str = ", ".join(equipment_list) if equipment_list else "None specified"
    tyre_info = f"10x Truck Tyres ({tyre_condition})" if include_tyres else "No tyres"

    prompt = f"""You are an expert international freight, customs, and construction equipment procurement consultant
with 20+ years of experience in cross-border heavy machinery logistics, particularly for African markets.

A procurement consultant based in {procurement_country} needs a comprehensive shipping and customs advisory report
for the following scenario:

---
PROCUREMENT DETAILS:
- Source Market: {from_market}
- Destination: {to_destination}
- Equipment to ship: {equipment_str}
- Additional items: {tyre_info}
- Buyer/Agent Residency: {buyer_residency}
- Preferred shipment method: {shipment_method}
- Special requirements/notes: {special_notes if special_notes else "None"}
---

Please provide a thorough, actionable advisory report covering ALL of the following sections:

## 1. RECOMMENDED SHIPPING METHOD & CONFIGURATION
- Best shipping method for this equipment mix (RO-RO vs container types)
- Estimated container/vessel requirements
- Stowage and lashing considerations for heavy machinery

## 2. ESTIMATED SHIPPING COSTS & TIMELINE
- Approximate freight cost ranges (USD) for this route
- Transit time estimate
- Port handling and demurrage considerations at destination port
- Seasonal/routing factors that could affect cost or timing

## 3. CUSTOMS & IMPORT DUTIES (Destination Country)
- Applicable HS codes for each equipment category
- Import duty rates at the destination
- VAT and other levies (ECOWAS levy, port surcharges, etc.)
- Total estimated landed cost as a % markup over equipment price
- Any duty exemptions or investment promotion incentives that may apply

## 4. EXPORT REQUIREMENTS FROM SOURCE MARKET
- Export documentation required (commercial invoice, packing list, COO, bill of lading, etc.)
- Certificates or compliance docs needed (CE, emission certs, etc.)
- Any export restrictions or controls on heavy machinery from this market
- Special considerations for non-residents procuring in {from_market.split("(")[0].strip()} (if applicable)

## 5. NON-RESIDENT PROCUREMENT CONSIDERATIONS
- If the buyer is NOT resident in the source country, what structures/agents are needed?
- VAT recovery on export (if applicable for EU/UK sourcing)
- Payment structures and escrow recommendations
- Risk mitigation (Letter of Credit, Incoterms recommendation)

## 6. PRE-SHIPMENT & QUALITY REQUIREMENTS
- Pre-shipment inspection recommendations (SGS, Bureau Veritas, etc.)
- What to inspect for used vs new equipment
- Documentation for used equipment (hours log, service history, etc.)

## 7. KEY RISKS & MITIGATION STRATEGIES
- Top 3-5 risks for this specific procurement route
- How to mitigate each risk
- Insurance recommendations (marine cargo, breakdown, etc.)

## 8. RECOMMENDED INCOTERMS
- Best Incoterms for this scenario and why
- Comparison of alternatives

## 9. PRACTICAL NEXT STEPS
- Concrete action steps in chronological order
- Recommended type of freight forwarder/agent to engage
- Timeline from order placement to delivery

Be specific, practical and quantify estimates where possible. Use USD for cost estimates.
Flag any regulations that may have changed recently and recommend verification with local customs authorities.
"""

    with st.spinner(""):
        message = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )

    return message.content[0].text


def get_market_analysis(
    equipment: str,
    condition: str,
    markets: list,
    price_data: list,
    procurement_country: str,
    destination: str,
) -> str:
    """Generate market analysis and procurement recommendation using Claude."""

    markets_str = ", ".join(markets)
    price_summary = "\n".join([
        f"  - {row['Market']}: ${row['Adjusted Price (USD)']:,.0f} USD "
        f"(lead time: {row['Typical Lead Time']}, import duty to NG: {row['Import Duty (to NG)']})"
        for row in price_data
    ])

    prompt = f"""You are a senior construction equipment procurement consultant advising a firm
based in {procurement_country} that sources equipment for clients in {destination}.

Provide a concise but insightful market analysis for the following:

EQUIPMENT: {equipment} ({condition})
MARKETS COMPARED: {markets_str}

PRICE DATA:
{price_summary}

Your analysis should cover:

1. **PROCUREMENT RECOMMENDATION**: Which market offers the best overall value proposition (not just cheapest price) and why?

2. **TOTAL COST OF OWNERSHIP PERSPECTIVE**: Beyond purchase price, what factors affect TCO over 5 years?
   (Parts availability, local service networks, fuel efficiency, resale value, downtime risk)

3. **MARKET-SPECIFIC RISKS**: What are the top risks of procuring from each market for delivery to {destination}?

4. **BRAND/QUALITY CONSIDERATIONS**: For {equipment} specifically, which brands/manufacturers to prioritise
   in each market, and which to avoid?

5. **NEGOTIATION TIPS**: Practical tips for negotiating price and terms in the recommended market.

6. **SMART HYBRID STRATEGY**: Is there a case for splitting the order across markets?
   (e.g. EU for complex machinery, CN for tyres/consumables)

Keep the response practical, specific, and focused on actionable insights for a procurement consultant.
Use bullet points where helpful. Aim for ~400-500 words.
"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
