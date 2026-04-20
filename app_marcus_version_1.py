import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import anthropic


# ══════════════════════════════════════════════════════════════════════════════
# DATA (inlined)
# ══════════════════════════════════════════════════════════════════════════════

EQUIPMENT_CATALOG = {
    "Excavator": {
        "category": "Earthmoving",
        "specs": {
            "Operating Weight": "20,000 kg", "Engine Power": "103 kW / 138 HP",
            "Bucket Capacity": "0.91 m³", "Max Dig Depth": "6.7 m",
            "Boom Reach": "9.9 m", "Fuel Tank": "400 L",
        },
    },
    "Motor Grader": {
        "category": "Road Construction",
        "specs": {
            "Operating Weight": "14,500 kg", "Engine Power": "140 kW / 188 HP",
            "Blade Width": "3.7 m", "Blade Height": "610 mm",
            "Max Blade Angle": "360°", "Fuel Tank": "250 L",
        },
    },
    "Bulldozer (Dozer)": {
        "category": "Earthmoving",
        "specs": {
            "Operating Weight": "20,400 kg", "Engine Power": "134 kW / 180 HP",
            "Blade Width": "3.9 m", "Blade Capacity": "4.5 m³",
            "Ground Pressure": "0.05 MPa", "Fuel Tank": "360 L",
        },
    },
    "Dump Truck": {
        "category": "Haulage",
        "specs": {
            "Payload": "12,000 kg", "GVW": "25,000 kg",
            "Engine Power": "250 kW / 335 HP", "Body Volume": "8 m³",
            "Drive Config": "6x4", "Fuel Tank": "300 L",
        },
    },
    "Water Tanker Truck": {
        "category": "Support Equipment",
        "specs": {
            "Tank Capacity": "10,000 L", "GVW": "20,000 kg",
            "Engine Power": "200 kW / 268 HP", "Pump Flow Rate": "1,200 L/min",
            "Drive Config": "6x4", "Spray Width": "8 m",
        },
    },
    "Truck Tyres (x10)": {
        "category": "Parts & Consumables",
        "specs": {
            "Size": "11R22.5", "Load Index": "148/145",
            "Speed Rating": "L (120 km/h)", "Rim Size": "22.5\"",
            "Tread Depth (New)": "19 mm", "Application": "All-position",
        },
    },
}

MARKETS = {
    "European Market (EU)": {
        "region": "Europe", "currency": "EUR",
        "platforms": ["Mascus.com", "Ritchie Bros", "TruckScout24", "Autoline"],
        "lead_time": "2–8 weeks", "import_duty_nigeria": "5–35%",
        "prices": {"Excavator": 95000, "Motor Grader": 120000, "Bulldozer (Dozer)": 85000,
                   "Dump Truck": 38000, "Water Tanker Truck": 45000, "Truck Tyres (x10)": 3500},
    },
    "Alibaba / Chinese Market": {
        "region": "Asia (China)", "currency": "CNY",
        "platforms": ["Alibaba.com", "Made-in-China.com", "Global Sources"],
        "lead_time": "4–12 weeks + shipping", "import_duty_nigeria": "5–35%",
        "prices": {"Excavator": 38000, "Motor Grader": 55000, "Bulldozer (Dozer)": 35000,
                   "Dump Truck": 18000, "Water Tanker Truck": 22000, "Truck Tyres (x10)": 1200},
    },
    "Middle East (UAE/Dubai)": {
        "region": "Middle East", "currency": "AED",
        "platforms": ["Dubizzle Heavy", "YallaMotor Commercial", "MachineryZone ME"],
        "lead_time": "2–6 weeks", "import_duty_nigeria": "5–35%",
        "prices": {"Excavator": 65000, "Motor Grader": 85000, "Bulldozer (Dozer)": 60000,
                   "Dump Truck": 28000, "Water Tanker Truck": 33000, "Truck Tyres (x10)": 2200},
    },
    "UK Market": {
        "region": "Europe (UK)", "currency": "GBP",
        "platforms": ["Machinery Trader UK", "Ritchie Bros UK", "Plant & Equipment"],
        "lead_time": "2–8 weeks", "import_duty_nigeria": "5–35%",
        "prices": {"Excavator": 88000, "Motor Grader": 110000, "Bulldozer (Dozer)": 80000,
                   "Dump Truck": 35000, "Water Tanker Truck": 42000, "Truck Tyres (x10)": 3100},
    },
    "US / North American Market": {
        "region": "North America", "currency": "USD",
        "platforms": ["IronPlanet", "Machinery Trader", "BigIron"],
        "lead_time": "4–10 weeks + shipping", "import_duty_nigeria": "5–35%",
        "prices": {"Excavator": 92000, "Motor Grader": 115000, "Bulldozer (Dozer)": 82000,
                   "Dump Truck": 42000, "Water Tanker Truck": 48000, "Truck Tyres (x10)": 3800},
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS (inlined)
# ══════════════════════════════════════════════════════════════════════════════


# CURRENCY DATA
CURRENCIES = {
    "USD - US Dollar":       {"code": "USD", "symbol": "$",    "rate": 1.0},
    "EUR - Euro":            {"code": "EUR", "symbol": "€",    "rate": 0.93},
    "NGN - Nigerian Naira":  {"code": "NGN", "symbol": "₦",    "rate": 1580.0},
    "GBP - British Pound":   {"code": "GBP", "symbol": "£",    "rate": 0.79},
    "AED - UAE Dirham":      {"code": "AED", "symbol": "AED ", "rate": 3.67},
    "CNY - Chinese Yuan":    {"code": "CNY", "symbol": "¥",    "rate": 7.24},
    "GHS - Ghanaian Cedi":   {"code": "GHS", "symbol": "GH₵",  "rate": 15.6},
    "ZAR - South African Rand": {"code": "ZAR", "symbol": "R",    "rate": 18.5},
}

def fmt(usd_value: float, currency_key: str) -> str:
    c = CURRENCIES[currency_key]
    converted = usd_value * c["rate"]
    if converted >= 1_000_000_000:
        return f"{c['symbol']}{converted/1_000_000_000:.2f}B"
    elif converted >= 1_000_000:
        return f"{c['symbol']}{converted/1_000_000:.2f}M"
    elif converted >= 1_000:
        return f"{c['symbol']}{converted:,.0f}"
    else:
        return f"{c['symbol']}{converted:.2f}"

SYSTEM_PROMPT = """You are Marcus, a world-class heavy construction equipment expert and senior procurement consultant at PROCURA. You have 25+ years of hands-on experience spanning three distinct areas of deep expertise:

═══ AREA 1: TECHNICAL MACHINE EXPERTISE ═══
You are a certified heavy equipment engineer with intimate technical knowledge of every machine category relevant to road construction and civil engineering:

EARTHMOVING & GRADING:
- Excavators (hydraulic crawler & wheeled): engine systems, hydraulic circuits, boom/arm/bucket geometry, undercarriage wear, slew rings, counterweights. Know every major model from CAT 320 to XCMG XE215 inside out.
- Motor Graders: circle drive systems, moldboard angles, articulation, tandem drives, blade float. Can spec the right grader for any soil type.
- Bulldozers: track systems, torque converters, blade types (S/U/SU/angle), ripper attachments, ground pressure calculations for soft terrain.
- Compactors & Rollers: vibratory vs static, soil vs asphalt compaction, pass counts.

HAULAGE & SUPPORT:
- Dump Trucks (rigid & articulated): payload ratings, GVW, axle configs (6x4, 8x4), body types, tipping mechanisms, suspension systems.
- Water Tanker Trucks: tank materials (steel vs poly), pump systems, spray bar configs, fill rates — critical for dust suppression and compaction.
- Wheel Loaders, Backhoe Loaders, Scrapers, Motor Scrapers: full working knowledge.

TYRES & UNDERCARRIAGE:
- Deep knowledge of OTR (Off-The-Road) tyres: ply ratings, load indices, tread patterns for laterite/mud/rock.
- Undercarriage components: track chains, rollers, idlers, sprockets — wear rates and replacement intervals.
- Know exactly which tyre brands perform in West African conditions vs which fail prematurely.

═══ AREA 2: ROAD CONSTRUCTION PROJECT EXPERTISE ═══
You have personally managed or advised on 40+ road construction projects across Nigeria, Ghana, Kenya, Ethiopia and Cameroon. You understand:

PROJECT PHASES & MACHINE ROLES:
- Site clearing & stripping: which machines, in what sequence, at what production rates
- Subgrade preparation: moisture control, compaction standards (95% MDD), CBR requirements
- Sub-base & base course construction: grading tolerances, material specs, compaction layers
- Surface course: asphalt vs concrete vs gravel roads — different machine sets
- Drainage construction: excavator work, culverts, cut-off drains

NIGERIAN ROAD CONSTRUCTION SPECIFICS:
- Federal Road Standard (FMW&H specifications) — you know the Nigerian road design codes
- Laterite soil behaviour: CBR values, shrinkage limits, stabilisation with cement/lime
- Harmattan vs rainy season construction strategies — critical for earthworks sequencing
- Common failure modes on Nigerian roads: edge failures, potholes from poor subgrade
- Material sourcing: laterite borrow pits, quarry stone, laterite gravel blends
- Site logistics in Nigeria: fuel supply chains, generator backup, security considerations

FLEET SIZING & PRODUCTIVITY:
- Can calculate machine productivity rates (m3/hour for excavators, km/day for graders)
- Know how to size a fleet for a given contract programme
- Understand machine utilisation rates in African conditions (typically 60-70% vs 85% in Europe)

═══ AREA 3: PROCUREMENT & MARKET EXPERTISE ═══
- Deep knowledge of EU used equipment market: Mascus, TruckScout24, Ritchie Bros pricing cycles
- Know which dealers in Germany, Netherlands, Belgium specialise in export-spec machines
- Understand CE certification, emission standards (Stage IIIA vs V) and what matters for African import
- Full knowledge of export procedures: EUR1, CMR, ATR certificates, bill of lading, packing lists
- Import procedures into Nigeria: SON certification, NAFDAC where relevant, customs HS codes, duty rates
- Shipping routes: Bremen/Hamburg/Antwerp to Apapa — RO-RO vs flat rack vs open top containers
- Know CAT, Komatsu, Volvo, Liebherr, JCB, Manitowoc dealer networks in Nigeria
- Chinese equipment brands: honest assessment of Shantui, XCMG, SANY, SDLG, LiuGong quality tiers

═══ YOUR CLIENT & PROJECT ═══
Client: Sergio — a procurement consultant who is COMPLETELY NEW to construction equipment.
End client: Nigerian infrastructure company, road construction project, Lagos/SW Nigeria area.

Equipment needed:
- 1x Excavator (20t class)
- 1x Motor Grader
- 1x Bulldozer (Dozer)
- 2x Dump Trucks
- 1x Water Tanker Truck
- 10x Truck Tyres (mix new/used)

PROJECT CONTEXT:
- Terrain: Laterite soil, clay, some rocky sections — typical Nigerian highway
- Climate: Tropical — rainy season Apr-Oct, harmattan Nov-Mar
- Road type: New construction + rehabilitation
- Key challenges: Wet season ground instability, dust, remote access, limited local service
- Sourcing preference: EU market for reliability, cost-conscious

═══ YOUR CONSULTING APPROACH ═══
- Assume Sergio knows ZERO about machines — explain everything from first principles
- Use analogies to make technical concepts accessible (e.g. "a motor grader is like a giant pencil sharpener for the road surface")
- Give SPECIFIC brand/model recommendations with clear reasons — never be vague
- Be honest about trade-offs: premium EU brand vs Chinese alternative, new vs used
- Proactively flag things Sergio doesn\'t know to ask — anticipate problems before they happen
- Bring in real-world Nigeria context in every answer — not generic advice
- When discussing a machine, always cover: what it does, why it\'s needed, what specs matter for Nigeria, which brands/models are recommended, what to avoid, what to check when buying used
- End every response with either a follow-up question or a clear next topic to explore

TONE: Warm, authoritative, mentor-like. Think of yourself as a trusted senior colleague who genuinely wants this project to succeed — not just answering questions but actively guiding the procurement strategy."""

def format_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    return f"${value:,.0f}"

def format_price_comparison(base_price: float, compare_price: float) -> dict:
    diff = compare_price - base_price
    pct = (diff / base_price * 100) if base_price else 0
    return {"difference": diff, "percentage": pct, "is_cheaper": diff < 0,
            "label": f"{'↓' if diff < 0 else '↑'} {abs(pct):.1f}%"}

def get_shipping_advice(from_market, to_destination, equipment_list, include_tyres,
                         tyre_condition, buyer_residency, shipment_method,
                         special_notes, procurement_country):
    client = anthropic.Anthropic()
    equipment_str = ", ".join(equipment_list) if equipment_list else "None specified"
    tyre_info = f"10x Truck Tyres ({tyre_condition})" if include_tyres else "No tyres"
    prompt = f"""You are an expert international freight, customs, and construction equipment procurement consultant
with 20+ years of experience in cross-border heavy machinery logistics, particularly for African markets.

Procurement consultant based in {procurement_country} needs a shipping and customs advisory for:
- Source Market: {from_market}
- Destination: {to_destination}
- Equipment: {equipment_str}
- Additional items: {tyre_info}
- Buyer/Agent Residency: {buyer_residency}
- Shipment method: {shipment_method}
- Special notes: {special_notes if special_notes else "None"}

Cover ALL sections:
## 1. RECOMMENDED SHIPPING METHOD & CONFIGURATION
## 2. ESTIMATED SHIPPING COSTS & TIMELINE
## 3. CUSTOMS & IMPORT DUTIES (HS codes, duty rates, VAT, levies, landed cost estimate)
## 4. EXPORT REQUIREMENTS FROM SOURCE MARKET
## 5. NON-RESIDENT PROCUREMENT CONSIDERATIONS
## 6. PRE-SHIPMENT & QUALITY REQUIREMENTS
## 7. KEY RISKS & MITIGATION STRATEGIES
## 8. RECOMMENDED INCOTERMS
## 9. PRACTICAL NEXT STEPS

Be specific. Quantify estimates in USD where possible."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

def get_market_analysis(equipment, condition, markets, price_data, procurement_country, destination):
    client = anthropic.Anthropic()
    price_summary = "\n".join([
        f"  - {r['Market']}: ${r['Adjusted Price (USD)']:,.0f} USD (lead time: {r['Typical Lead Time']})"
        for r in price_data
    ])
    prompt = f"""Senior procurement consultant for {procurement_country} firm sourcing for {destination}.

Analyse: {equipment} ({condition})
Markets: {", ".join(markets)}
Prices:
{price_summary}

Cover:
1. PROCUREMENT RECOMMENDATION — best overall value and why
2. TOTAL COST OF OWNERSHIP — parts, service, resale, downtime risk
3. MARKET-SPECIFIC RISKS for delivery to {destination}
4. BRAND/QUALITY CONSIDERATIONS — which to prioritise or avoid
5. NEGOTIATION TIPS for recommended market
6. SMART HYBRID STRATEGY — split order across markets?

Practical, focused, ~400 words."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def live_market_search(
    machine_type, markets, condition, min_power, max_power,
    min_year, max_year, budget_usd, extra_specs, destination
):
    client = anthropic.Anthropic()
    markets_str = ", ".join(markets) if markets else "European, China, Middle East"
    spec_lines = []
    if min_power or max_power:
        spec_lines.append(f"Engine power: {min_power or 'any'}-{max_power or 'any'} HP")
    if min_year or max_year:
        spec_lines.append(f"Year: {min_year or 'any'}-{max_year or 'any'}")
    if budget_usd:
        spec_lines.append(f"Max budget: ${budget_usd} USD")
    if extra_specs:
        spec_lines.append(f"Additional requirements: {extra_specs}")
    specs_block = "\n".join(spec_lines) if spec_lines else "No additional filters"

    prompt = f"""You are a senior construction equipment procurement specialist. Use web search to find REAL current listings.

SEARCH REQUEST:
- Machine: {machine_type}
- Condition: {condition}
- Markets: {markets_str}
- Specs: {specs_block}
- Final destination: {destination}

INSTRUCTIONS:
1. Search these platforms for REAL listings now:
   EU/Germany: mascus.com, mascus.de, truckscout24.de, autoline.eu
   China/Asia: alibaba.com, made-in-china.com
   Middle East: plant.ae, dubizzle.com/heavy-equipment
   UK: planttrader.com, machineryzone.eu

2. For each listing found extract: model name, year, price (USD), engine HP, weight/capacity, hours (if used), seller location, platform, direct URL.

3. Present a COMPARISON TABLE with columns: Model | Market | Price USD | Year | Engine HP | Key Spec | Hours | Link

4. SPEC HIGHLIGHTS - for each listing mark:
   BETTER: specs where this unit beats others
   WEAKER: specs where this unit falls short
   SIMILAR: specs that match across listings

5. PROCUREMENT VERDICT:
   - Best value pick + reason
   - Best quality pick + reason
   - Best fit for shipping to {destination}
   - Any red flags in any listing

Be specific. Use real model names, real prices, real URLs. If no results found for a market, say so and give the best search URL to check manually."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    result_parts = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            result_parts.append(block.text)
    return "\n\n".join(result_parts) if result_parts else "No results returned. Please try again."

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PROCURA — Global Procurement Intelligence",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* Reset & Base */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

/* Background */
.stApp {
    background-color: #0A0E1A;
    color: #E8EDF5;
}

/* Main header */
.procure-header {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 50%, #0D1B2A 100%);
    border: 1px solid #2A3F5F;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.procure-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #F5A623, #E8573F, #C0392B);
}
.procure-header h1 {
    font-size: 2.4rem;
    font-weight: 700;
    color: #F5A623;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.5px;
}
.procure-header p {
    color: #8A9BB5;
    font-size: 1rem;
    margin: 0;
}

/* Metric cards */
.metric-card {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.metric-card .label {
    font-size: 0.75rem;
    color: #5A7A9A;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 500;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #F5A623;
    font-family: 'IBM Plex Mono', monospace;
}
.metric-card .sub {
    font-size: 0.8rem;
    color: #4A6A8A;
    margin-top: 0.2rem;
}

/* Market badges */
.market-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-eu { background: #1A3A5C; color: #4A9EF5; border: 1px solid #2A5A8C; }
.badge-cn { background: #3A1A1A; color: #E85F5F; border: 1px solid #6A2A2A; }
.badge-us { background: #1A3A2A; color: #4AE89E; border: 1px solid #2A6A4A; }
.badge-ae { background: #3A2A1A; color: #E8A84A; border: 1px solid #6A4A2A; }

/* Section dividers */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #C0D0E0;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 0.5rem 0;
    border-bottom: 1px solid #1E2D42;
    margin: 1.5rem 0 1rem 0;
}

/* AI response box */
.ai-response {
    background: #0D1B2A;
    border: 1px solid #2A3F5F;
    border-left: 3px solid #F5A623;
    border-radius: 8px;
    padding: 1.5rem;
    font-size: 0.9rem;
    line-height: 1.7;
    color: #C8D8E8;
    white-space: pre-wrap;
}

/* Equipment tag */
.equip-tag {
    display: inline-block;
    background: #1A2A3A;
    border: 1px solid #2A4A6A;
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    font-size: 0.78rem;
    color: #7AABCF;
    margin: 0.15rem;
    font-family: 'IBM Plex Mono', monospace;
}

/* Savings highlight */
.savings-positive { color: #4AE89E; font-weight: 600; }
.savings-negative { color: #E85F5F; font-weight: 600; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0D1421;
    border-right: 1px solid #1E2D42;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #E8573F, #C0392B);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(232, 87, 63, 0.4);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-radius: 8px;
    padding: 0.3rem;
    gap: 0.3rem;
}
.stTabs [data-baseweb="tab"] {
    color: #5A7A9A;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #1E2D42 !important;
    color: #F5A623 !important;
    border-radius: 6px;
}

/* Select boxes */
.stSelectbox > div > div {
    background: #111827;
    border-color: #2A3F5F;
    color: #E8EDF5;
}

/* Info boxes */
.info-box {
    background: #0D1B2A;
    border: 1px solid #2A3F5F;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
    color: #8A9BB5;
}

/* Dataframe styling */
.dataframe { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.82rem !important; }
</style>
""", unsafe_allow_html=True)


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="procure-header">
  <div style="display:flex; align-items:center; gap:1.2rem; margin-bottom:0.6rem;">
    <svg width="56" height="56" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">
      <!-- Hexagon mark -->
      <polygon points="28,3 51,16 51,42 28,55 5,42 5,16" fill="#E8573F"/>
      <!-- Inner hexagon outline -->
      <polygon points="28,12 43,21 43,37 28,46 13,37 13,21" fill="none" stroke="white" stroke-width="1.4"/>
      <!-- P letterform -->
      <line x1="22" y1="21" x2="22" y2="37" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
      <path d="M22 21 Q33 21 33 27 Q33 33 22 33" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
    </svg>
    <div>
      <div style="font-size:2rem; font-weight:700; color:#F5A623; margin:0; letter-spacing:2px; font-family:'Space Grotesk',sans-serif;">PROCURA</div>
      <div style="color:#8A9BB5; font-size:0.72rem; margin:2px 0 0 0; letter-spacing:3px; font-family:'Space Grotesk',sans-serif;">GLOBAL PROCUREMENT</div>
    </div>
  </div>
  <p style="color:#6A8AAA; font-size:0.88rem; margin:0;">Cross-Market Equipment Intelligence &nbsp;·&nbsp; Price Comparison &nbsp;·&nbsp; AI-Powered Shipping Advisory</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    # Procurement origin
    st.markdown("**Your Location (Procurement Base)**")
    procurement_country = st.selectbox(
        "Where are you based?",
        ["Germany 🇩🇪", "UK 🇬🇧", "UAE 🇦🇪", "USA 🇺🇸", "China 🇨🇳", "Other"],
        index=0,
        label_visibility="collapsed"
    )

    # Destination
    st.markdown("**Delivery Destination**")
    destination_country = st.selectbox(
        "Ship to?",
        ["Nigeria 🇳🇬", "Ghana 🇬🇭", "Kenya 🇰🇪", "South Africa 🇿🇦",
         "Ethiopia 🇪🇹", "Tanzania 🇹🇿", "Other African country",
         "Indonesia 🇮🇩", "Other"],
        index=0,
        label_visibility="collapsed"
    )

    # Markets to compare
    st.markdown("**Markets to Compare**")
    selected_markets = st.multiselect(
        "Select markets",
        list(MARKETS.keys()),
        default=["European Market (EU)", "Alibaba / Chinese Market", "Middle East (UAE/Dubai)"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**Display Currency**")
    selected_currency = st.selectbox(
        "Currency",
        list(CURRENCIES.keys()),
        index=1,
        label_visibility="collapsed"
    )
    curr = CURRENCIES[selected_currency]
    st.markdown(f"""<div class="info-box" style="font-size:0.8rem;">
    Prices shown in <strong style="color:#F5A623;">{curr['code']}</strong>
    &nbsp;·&nbsp; 1 USD = {curr['rate']} {curr['code']}<br>
    <span style="color:#4A6A8A; font-size:0.72rem;">Rates are indicative only.</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Active Client**")
    st.markdown("""
    <div class="info-box">
    🏢 <strong style="color:#F5A623;">Nigerian Infrastructure Client</strong><br>
    📍 Lagos, Nigeria<br>
    📦 5 Equipment Categories<br>
    🔧 Incl. Tyres (New & Used)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='color:#3A5A7A; font-size:0.75rem;'>PROCURA v1.0 · Claude API</p>", unsafe_allow_html=True)


# ─── Main Tabs ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Market Comparison",
    "🔎 Search & Shortlist",
    "🔗 Live Market Search",
    "🚢 Shipping & Logistics AI",
    "📋 Order Builder",
    "🤖 AI Consultant"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Market Comparison
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">Equipment Selection</div>', unsafe_allow_html=True)

    col_eq, col_cond = st.columns([2, 1])
    with col_eq:
        selected_equipment = st.selectbox(
            "Choose Equipment",
            list(EQUIPMENT_CATALOG.keys()),
        )
    with col_cond:
        condition = st.selectbox(
            "Condition",
            ["New", "Used (Good)", "Used (Fair)", "Refurbished"],
        )

    if not selected_markets:
        st.warning("⚠️ Please select at least one market from the sidebar.")
        st.stop()

    equipment = EQUIPMENT_CATALOG[selected_equipment]

    # ── Specs Overview ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Specifications</div>', unsafe_allow_html=True)

    spec_cols = st.columns(len(equipment["specs"]))
    for i, (spec_key, spec_val) in enumerate(equipment["specs"].items()):
        with spec_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{spec_key}</div>
                <div class="value" style="font-size:1.1rem;">{spec_val}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Price Comparison Table ────────────────────────────────────────────────
    st.markdown('<div class="section-title">Price Comparison Across Markets</div>', unsafe_allow_html=True)

    condition_multiplier = {"New": 1.0, "Used (Good)": 0.65, "Used (Fair)": 0.45, "Refurbished": 0.75}
    mult = condition_multiplier[condition]

    rows = []
    for market_name in selected_markets:
        if market_name not in MARKETS:
            continue
        market = MARKETS[market_name]
        if selected_equipment in market["prices"]:
            base_price = market["prices"][selected_equipment]
            adjusted = base_price * mult
            rows.append({
                "Market": market_name,
                "Region": market["region"],
                "Base Price (USD)": base_price,
                "Adjusted Price (USD)": adjusted,
                "Typical Lead Time": market["lead_time"],
                "Import Duty (to NG)": market["import_duty_nigeria"],
                "Currency": market["currency"],
                "Key Platforms": ", ".join(market["platforms"]),
            })

    if not rows:
        st.info("No price data available for this equipment + market combination.")
    else:
        df = pd.DataFrame(rows)
        df_sorted = df.sort_values("Adjusted Price (USD)")
        cheapest = df_sorted.iloc[0]["Market"]
        cheapest_price = df_sorted.iloc[0]["Adjusted Price (USD)"]
        most_expensive = df_sorted.iloc[-1]["Adjusted Price (USD)"]
        savings_potential = most_expensive - cheapest_price

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Best Price Market</div>
                <div class="value" style="font-size:1rem;">{cheapest.split("(")[0].strip()}</div>
                <div class="sub">{condition} · {selected_equipment}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Lowest Price</div>
                <div class="value">{format_currency(cheapest_price)}</div>
                <div class="sub">USD · {condition}</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            pct = ((most_expensive - cheapest_price) / most_expensive * 100) if most_expensive else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Max Savings vs Priciest</div>
                <div class="value" style="color:#4AE89E;">{fmt(savings_potential, selected_currency)}</div>
                <div class="sub">{pct:.1f}% difference</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Markets Compared</div>
                <div class="value">{len(rows)}</div>
                <div class="sub">Active comparison</div>
            </div>
            """, unsafe_allow_html=True)

        # Chart
        fig = go.Figure()
        colors = ["#E85F5F", "#4A9EF5", "#4AE89E", "#E8A84A", "#A84AE8"]
        for i, row in df_sorted.iterrows():
            color_idx = list(df_sorted.index).index(i) % len(colors)
            fig.add_trace(go.Bar(
                name=row["Market"].split("(")[0].strip(),
                x=[row["Market"].split("(")[0].strip()],
                y=[row["Adjusted Price (USD)"]],
                marker_color=colors[color_idx],
                text=fmt(row["Adjusted Price (USD)"], selected_currency),
                textposition="outside",
                textfont=dict(color="white", size=12),
            ))

        fig.update_layout(
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font=dict(color="#C0D0E0", family="Space Grotesk"),
            showlegend=False,
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(gridcolor="#1E2D42", tickfont=dict(size=11)),
            yaxis=dict(
                gridcolor="#1E2D42",
                tickprefix="$",
                tickformat=",",
                tickfont=dict(family="IBM Plex Mono"),
            ),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table
        display_df = df_sorted[["Market", "Adjusted Price (USD)", "Typical Lead Time",
                                  "Import Duty (to NG)", "Key Platforms"]].copy()
        display_df["Adjusted Price (USD)"] = display_df["Adjusted Price (USD)"].apply(
            lambda x: f"${x:,.0f}"
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Price influence factors
        st.markdown('<div class="section-title">What Drives These Price Differences?</div>', unsafe_allow_html=True)
        factors_col1, factors_col2 = st.columns(2)
        with factors_col1:
            st.markdown("""
            <div class="info-box">
            <strong style="color:#F5A623;">🇨🇳 Why Asian/Alibaba is cheaper:</strong><br><br>
            • Lower manufacturing labour costs<br>
            • Vertical supply chain integration<br>
            • Government export subsidies (some categories)<br>
            • High production volume = economies of scale<br>
            • Less stringent emission/safety standards (CE equivalent)
            </div>
            """, unsafe_allow_html=True)
        with factors_col2:
            st.markdown("""
            <div class="info-box">
            <strong style="color:#4A9EF5;">🇩🇪 Why EU pricing is higher:</strong><br><br>
            • CE certification and EU regulatory compliance<br>
            • Higher labour, warranty & after-sales costs<br>
            • Stricter environmental/emission standards (Stage V)<br>
            • Premium brand reliability and resale value<br>
            • Stronger financing/leasing ecosystem
            </div>
            """, unsafe_allow_html=True)

        # AI Market Analysis button
        st.markdown("---")
        if st.button("🤖 Generate AI Market Analysis for this Equipment"):
            with st.spinner("Analysing market dynamics..."):
                analysis = get_market_analysis(
                    equipment=selected_equipment,
                    condition=condition,
                    markets=selected_markets,
                    price_data=rows,
                    procurement_country=procurement_country,
                    destination=destination_country
                )
            st.markdown(f'<div class="ai-response">{analysis}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Equipment Deep Dive
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Search & Shortlist
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Session state init ────────────────────────────────────────────────────
    if "shortlists" not in st.session_state:
        st.session_state.shortlists = {
            "Excavator": [],
            "Motor Grader": [],
            "Bulldozer (Dozer)": [],
            "Dump Truck": [],
            "Water Tanker Truck": [],
        }
    if "selected_machines" not in st.session_state:
        st.session_state.selected_machines = {}
    if "search_tab_machine" not in st.session_state:
        st.session_state.search_tab_machine = "Excavator"

    # ── Client machine list (pre-loaded + custom) ─────────────────────────────
    CLIENT_MACHINES = {
        "Excavator": {
            "qty": 1, "specs": "20t class, min 100HP, bucket 0.8m3+, crawler",
            "budget_usd": 80000, "notes": "CAT 320 / Komatsu PC200 / XCMG XE215 equivalent",
            "hs_code": "8429.52", "condition": "Used (Good) or New"
        },
        "Motor Grader": {
            "qty": 1, "specs": "min 140HP, blade 3.5m+, all-wheel drive preferred",
            "budget_usd": 100000, "notes": "CAT 120 / Komatsu GD555 / SDLG G9180 equivalent",
            "hs_code": "8429.20", "condition": "Used (Good) or New"
        },
        "Bulldozer (Dozer)": {
            "qty": 1, "specs": "min 130HP, blade 3.8m+, crawler track",
            "budget_usd": 75000, "notes": "CAT D6 / Komatsu D65 / SHANTUI SD16 equivalent",
            "hs_code": "8429.11", "condition": "Used (Good) or New"
        },
        "Dump Truck": {
            "qty": 2, "specs": "6x4, 10-15t payload, min 250HP",
            "budget_usd": 35000, "notes": "MAN TGS / Mercedes Actros / Volvo FMX equivalent",
            "hs_code": "8704.10", "condition": "Used (Good) or New"
        },
        "Water Tanker Truck": {
            "qty": 1, "specs": "10,000L+ tank, 6x4, spray system, min 200HP",
            "budget_usd": 40000, "notes": "MAN TGM / Mercedes Atego tanker conversion",
            "hs_code": "8705.90", "condition": "Used (Good) or New"
        },
    }

    st.markdown('<div class="section-title">Client Machine List</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="info-box">
    🏢 <strong style="color:#F5A623;">Nigerian Infrastructure Client</strong> &nbsp;·&nbsp;
    Destination: {destination_country} &nbsp;·&nbsp; Market: European (EU)
    &nbsp;·&nbsp; <span style="color:#4AE89E;">{sum(m["qty"] for m in CLIENT_MACHINES.values())} units total</span>
    </div>""", unsafe_allow_html=True)

    # ── Add custom machine ─────────────────────────────────────────────────────
    with st.expander("➕ Add Custom Machine to Search List"):
        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            cust_name = st.text_input("Machine Name", placeholder="e.g. Wheel Loader", key="cust_name")
            cust_qty = st.number_input("Qty", min_value=1, value=1, key="cust_qty")
        with cm2:
            cust_specs = st.text_input("Key Specs", placeholder="e.g. 3t capacity, min 80HP", key="cust_specs")
            cust_budget = st.number_input("Budget (USD)", min_value=0, value=50000, step=1000, key="cust_budget")
        with cm3:
            cust_cond = st.selectbox("Condition", ["New or Used", "New", "Used (Good)", "Used (Fair)"], key="cust_cond")
            cust_notes = st.text_input("Notes", placeholder="Brand preferences etc.", key="cust_notes")
        if st.button("Add to Search List", key="add_cust_machine"):
            if cust_name.strip():
                CLIENT_MACHINES[cust_name] = {
                    "qty": cust_qty, "specs": cust_specs, "budget_usd": cust_budget,
                    "notes": cust_notes, "hs_code": "—", "condition": cust_cond
                }
                if cust_name not in st.session_state.shortlists:
                    st.session_state.shortlists[cust_name] = []
                st.success(f"Added {cust_name} to search list")
                st.rerun()

    st.markdown("---")

    # ── Machine selector ──────────────────────────────────────────────────────
    machine_names = list(CLIENT_MACHINES.keys())
    selected_machine = st.radio(
        "Select machine to work on:",
        machine_names,
        horizontal=True,
        key="search_machine_radio"
    )
    mdata = CLIENT_MACHINES[selected_machine]
    shortlist = st.session_state.shortlists.get(selected_machine, [])
    sel_count = len(shortlist)
    has_selected = selected_machine in st.session_state.selected_machines

    # ── Machine card ──────────────────────────────────────────────────────────
    status_color = "#4AE89E" if has_selected else ("#F5A623" if sel_count > 0 else "#5A7A9A")
    status_label = "SELECTED" if has_selected else (f"{sel_count} SHORTLISTED" if sel_count > 0 else "NOT STARTED")
    st.markdown(f"""
    <div class="metric-card" style="border-left:3px solid {status_color}; margin-bottom:1rem;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div class="label">{mdata["condition"]} &nbsp;·&nbsp; Qty: {mdata["qty"]}</div>
          <div style="font-size:1.3rem; font-weight:700; color:#E8EDF5; margin:0.3rem 0;">{selected_machine}</div>
          <div style="font-size:0.85rem; color:#8A9BB5;">{mdata["specs"]}</div>
          <div style="font-size:0.8rem; color:#4A6A8A; margin-top:0.3rem;">{mdata["notes"]}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.7rem; color:{status_color}; font-weight:600; letter-spacing:1px;">{status_label}</div>
          <div style="font-size:1.1rem; font-weight:700; color:#F5A623; margin-top:0.3rem;">{fmt(mdata["budget_usd"], selected_currency)}</div>
          <div style="font-size:0.72rem; color:#4A6A8A;">max budget</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── STEP 1: Search Links ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Step 1 — Search EU Platforms</div>', unsafe_allow_html=True)

    q = selected_machine.lower().replace(" ", "+").replace("(","").replace(")","")
    q_brand = mdata["notes"].split("/")[0].strip().lower().replace(" ","+") if mdata["notes"] else ""
    budget_eur = int(mdata["budget_usd"] * 0.93)

    search_links = {
        "Mascus.de 🇩🇪": f"https://www.mascus.de/suche#{q}",
        "Mascus.com 🌍": f"https://www.mascus.com/search#{q}",
        "TruckScout24 🇩🇪": f"https://www.truckscout24.de/transporter/gebraucht/{q}",
        "Autoline EU 🌍": f"https://autoline.eu/-/search?q={q}",
        "Ritchie Bros 🌍": f"https://www.rbauction.com/equipment?q={q}",
        "MachineryZone EU 🌍": f"https://www.machineryzone.eu/used/1/{q}.html",
        "Plant & Equipment 🇬🇧": f"https://www.planttrader.com/search?q={q}",
        "IronPlanet 🌍": f"https://www.ironplanet.com/results?q={q}",
    }

    link_cols = st.columns(4)
    colors = ["#4A9EF5","#4A9EF5","#4AE89E","#4AE89E","#E8A84A","#E8A84A","#A84AE8","#E85F5F"]
    for idx, (name, url) in enumerate(search_links.items()):
        with link_cols[idx % 4]:
            st.markdown(f"""<a href="{url}" target="_blank" style="
                display:block; background:#111827; border:1px solid #1E2D42;
                border-top:2px solid {colors[idx]}; border-radius:8px;
                padding:0.7rem 0.8rem; margin-bottom:0.5rem; text-decoration:none;">
                <div style="font-size:0.82rem; font-weight:600; color:{colors[idx]};">{name}</div>
                <div style="font-size:0.68rem; color:#3A5A7A; margin-top:0.2rem;">
                Budget: up to {fmt(mdata["budget_usd"], selected_currency)} &nbsp;·&nbsp; {mdata["condition"]}
                </div></a>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="info-box" style="margin-top:0.5rem;">
    🔍 Searching for: <strong style="color:#F5A623;">{selected_machine}</strong>
    &nbsp;·&nbsp; {mdata["condition"]}
    &nbsp;·&nbsp; Max {fmt(mdata["budget_usd"], selected_currency)}
    &nbsp;·&nbsp; {mdata["specs"]}<br>
    <span style="color:#4A6A8A; font-size:0.78rem;">Open the links above, find candidates, then add them to your shortlist below.</span>
    </div>""", unsafe_allow_html=True)

    # ── STEP 2: Shortlist ─────────────────────────────────────────────────────
    st.markdown(f'<div class="section-title">Step 2 — Shortlist Candidates ({sel_count} saved)</div>', unsafe_allow_html=True)

    with st.expander("➕ Add candidate to shortlist", expanded=(sel_count == 0)):
        sa, sb = st.columns(2)
        with sa:
            sl_model   = st.text_input("Model name", placeholder="e.g. CAT 320 GC", key=f"sl_model_{selected_machine}")
            sl_year    = st.text_input("Year", placeholder="e.g. 2020", key=f"sl_year_{selected_machine}")
            sl_price   = st.text_input("Price (with currency)", placeholder="e.g. €68,500", key=f"sl_price_{selected_machine}")
            sl_hours   = st.text_input("Hours (if used)", placeholder="e.g. 4,200h", key=f"sl_hours_{selected_machine}")
        with sb:
            sl_engine  = st.text_input("Engine HP/kW", placeholder="e.g. 138HP / 103kW", key=f"sl_eng_{selected_machine}")
            sl_weight  = st.text_input("Operating weight", placeholder="e.g. 20,200 kg", key=f"sl_weight_{selected_machine}")
            sl_seller  = st.text_input("Seller name", placeholder="e.g. Zeppelin GmbH", key=f"sl_seller_{selected_machine}")
            sl_location= st.text_input("Location", placeholder="e.g. Hamburg, Germany", key=f"sl_loc_{selected_machine}")
        sl_platform = st.text_input("Platform / URL", placeholder="e.g. Mascus.de — paste URL here", key=f"sl_plat_{selected_machine}")
        sl_notes    = st.text_input("Extra notes", placeholder="e.g. Full service history, new undercarriage", key=f"sl_notes_{selected_machine}")

        if st.button(f"Add to {selected_machine} Shortlist", key=f"sl_add_{selected_machine}"):
            if sl_model.strip():
                entry = {
                    "model": sl_model, "year": sl_year, "price": sl_price,
                    "hours": sl_hours, "engine": sl_engine, "weight": sl_weight,
                    "seller": sl_seller, "location": sl_location,
                    "platform": sl_platform, "notes": sl_notes,
                    "status": "shortlisted"
                }
                st.session_state.shortlists[selected_machine].append(entry)
                st.success(f"Added {sl_model} to shortlist")
                st.rerun()
            else:
                st.warning("Please enter at least a model name.")

    # Show shortlist cards
    if shortlist:
        for idx, cand in enumerate(shortlist):
            is_selected = st.session_state.selected_machines.get(selected_machine, {}).get("model") == cand["model"]
            card_color = "#4AE89E" if is_selected else "#2A3F5F"
            selected_badge = " ✅ SELECTED" if is_selected else ""
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"""<div class="info-box" style="border-left:3px solid {card_color};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <strong style="color:#E8EDF5; font-size:0.95rem;">{cand["model"]}{selected_badge}</strong>
                  <span style="color:#F5A623; font-weight:700; font-family:'IBM Plex Mono',monospace;">{cand["price"]}</span>
                </div>
                <div style="font-size:0.8rem; color:#8A9BB5; margin-top:0.4rem;">
                  Year: {cand["year"] or "—"} &nbsp;·&nbsp;
                  Hours: {cand["hours"] or "—"} &nbsp;·&nbsp;
                  Engine: {cand["engine"] or "—"} &nbsp;·&nbsp;
                  Weight: {cand["weight"] or "—"}
                </div>
                <div style="font-size:0.78rem; color:#4A6A8A; margin-top:0.2rem;">
                  {cand["seller"] or "—"} &nbsp;·&nbsp; {cand["location"] or "—"} &nbsp;·&nbsp; {cand["platform"] or "—"}
                </div>
                {f'<div style="font-size:0.78rem; color:#6A8AAA; margin-top:0.2rem;">📝 {cand["notes"]}</div>' if cand["notes"] else ""}
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("Select ✓", key=f"sel_{selected_machine}_{idx}"):
                    st.session_state.selected_machines[selected_machine] = cand
                    st.rerun()
                if st.button("Remove", key=f"rem_{selected_machine}_{idx}"):
                    st.session_state.shortlists[selected_machine].pop(idx)
                    st.rerun()
    else:
        st.markdown("""<div class="info-box" style="color:#3A5A7A; text-align:center; padding:1.5rem;">
        No candidates shortlisted yet for this machine.<br>
        <span style="font-size:0.82rem;">Use the search links above, then add candidates here.</span>
        </div>""", unsafe_allow_html=True)

    # ── STEP 3: AI Comparison ─────────────────────────────────────────────────
    if len(shortlist) >= 2:
        st.markdown('<div class="section-title">Step 3 — Compare Shortlisted Candidates</div>', unsafe_allow_html=True)

        cand_labels = [f"{c['model']} ({c['price']})" for c in shortlist]
        compare_picks = st.multiselect(
            "Select 2–3 candidates to compare",
            cand_labels, max_selections=3, key=f"cmp_picks_{selected_machine}"
        )

        if st.button("🤖 Compare Selected Candidates", key=f"cmp_run_{selected_machine}") and len(compare_picks) >= 2:
            picked = [shortlist[cand_labels.index(p)] for p in compare_picks]
            listings_block = ""
            for i, c in enumerate(picked, 1):
                listings_block += f"""
--- CANDIDATE {i} ---
Model: {c["model"]}
Year: {c["year"] or "NOT PROVIDED"}
Price: {c["price"] or "NOT PROVIDED"}
Engine: {c["engine"] or "NOT PROVIDED"}
Weight: {c["weight"] or "NOT PROVIDED"}
Hours: {c["hours"] or "NOT PROVIDED"}
Seller: {c["seller"] or "NOT PROVIDED"}
Location: {c["location"] or "NOT PROVIDED"}
Platform: {c["platform"] or "NOT PROVIDED"}
Notes: {c["notes"] or "none"}
"""
            client = anthropic.Anthropic()
            prompt = f"""You are a senior EU construction equipment procurement specialist.
Compare these {selected_machine} candidates for delivery to {destination_country}.
Budget ceiling: {fmt(mdata["budget_usd"], selected_currency)} ({mdata["budget_usd"]} USD).

RULES: Only use data provided. Mark missing fields. Label general knowledge as [ESTIMATE].

{listings_block}

## 1. COMPARISON TABLE
| Spec | {" | ".join([c["model"] for c in picked])} |
Show all provided specs side by side. Mark NOT PROVIDED where missing.

## 2. KEY DIFFERENCES
What meaningfully separates these candidates? Focus on:
- Price vs value (hours, age, condition)
- Engine and performance specs
- Seller credibility signals (dealer vs private, location)
- Any red flags in any listing

## 3. FIT FOR PURPOSE
How well does each candidate match the requirement: {mdata["specs"]}?
Does any exceed or fall short of the spec?

## 4. TOTAL COST ESTIMATE TO {destination_country.upper()} [ESTIMATES]
For each candidate:
Equipment price + estimated freight + import duty (~20%) + inspection = estimated landed cost

## 5. RECOMMENDATION
Clear winner and why. What to verify with the seller before committing."""

            with st.spinner(f"Comparing {len(picked)} {selected_machine} candidates..."):
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514", max_tokens=2500,
                    messages=[{"role": "user", "content": prompt}],
                )
            st.markdown(f'<div class="ai-response">{msg.content[0].text}</div>', unsafe_allow_html=True)

    # ── STEP 4: Enquiry Generator ─────────────────────────────────────────────
    if shortlist:
        st.markdown('<div class="section-title">Step 4 — Generate Seller Enquiry</div>', unsafe_allow_html=True)

        cand_labels_eq = [f"{c['model']} — {c['seller'] or 'Unknown seller'}" for c in shortlist]
        enquiry_pick = st.selectbox("Generate enquiry for:", cand_labels_eq, key=f"eq_pick_{selected_machine}")
        enquiry_cand = shortlist[cand_labels_eq.index(enquiry_pick)]

        eq_col1, eq_col2 = st.columns(2)
        with eq_col1:
            your_name    = st.text_input("Your name", value="Sergio", key=f"eq_name_{selected_machine}")
            your_company = st.text_input("Company name", value="PROCURA Global Procurement", key=f"eq_co_{selected_machine}")
        with eq_col2:
            your_email   = st.text_input("Your email", placeholder="sergio@procura.com", key=f"eq_email_{selected_machine}")
            urgency      = st.selectbox("Timeline", ["Flexible", "Within 30 days", "Within 60 days", "Urgent — within 2 weeks"], key=f"eq_urg_{selected_machine}")

        if st.button("✉️ Generate Email + Call Script", type="primary", key=f"eq_gen_{selected_machine}"):
            client = anthropic.Anthropic()
            prompt = f"""You are writing on behalf of {your_name} at {your_company}, a procurement consultancy
sourcing construction equipment for a client in {destination_country}.

Generate TWO things:

LISTING DETAILS:
Model: {enquiry_cand["model"]}
Year: {enquiry_cand["year"] or "as listed"}
Price: {enquiry_cand["price"] or "as listed"}
Seller: {enquiry_cand["seller"] or "seller"}
Location: {enquiry_cand["location"] or "Europe"}
Platform: {enquiry_cand["platform"] or "online marketplace"}
Hours: {enquiry_cand["hours"] or "unknown"}
Notes: {enquiry_cand["notes"] or "none"}

Context: Final destination {destination_country}. Timeline: {urgency}. Budget ceiling: {mdata["budget_usd"]} USD.

---

## EMAIL DRAFT
Professional enquiry email from {your_name} ({your_company}) to the seller.
Include:
- Introduction of PROCURA and the purchase intent
- Confirmation of key specs (ask seller to verify: current hours, condition grade, service history, tyre/undercarriage %, any recent repairs)
- Ask about: availability, final price, export documentation capability (commercial invoice, COO, packing list)
- Mention destination is {destination_country} — ask if seller has experience with export to Africa
- Payment terms question (T/T, LC?)
- Request photos/videos if not already available
- Your contact: {your_name}, {your_company}, {your_email if your_email else "[your email]"}
- Subject line included

## CALL SCRIPT
A structured talking points script for a phone call with this seller.
Sections: Opening → Verify the listing → Key questions → Price negotiation → Next steps.
Each section: 3-5 bullet points of what to say/ask.
Include: how to open the call, the 5 most important questions to ask,
how to position the destination (Nigeria) positively, and how to close for next steps."""

            with st.spinner("Writing email and call script..."):
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514", max_tokens=2500,
                    messages=[{"role": "user", "content": prompt}],
                )
            result = msg.content[0].text
            st.markdown(f'<div class="ai-response">{result}</div>', unsafe_allow_html=True)

    # ── STEP 5: Push to Order Builder ─────────────────────────────────────────
    if st.session_state.selected_machines:
        st.markdown('<div class="section-title">Step 5 — Push Selections to Order Builder</div>', unsafe_allow_html=True)

        sel_summary = []
        for mname, cand in st.session_state.selected_machines.items():
            qty = CLIENT_MACHINES.get(mname, {}).get("qty", 1)
            sel_summary.append(f"✅ **{mname}** x{qty} — {cand['model']} @ {cand['price']} ({cand['seller'] or '—'})")
        st.markdown("\n".join(sel_summary))

        if st.button("📋 Push All Selections to Order Builder", type="primary", key="push_to_order"):
            for mname, cand in st.session_state.selected_machines.items():
                qty = CLIENT_MACHINES.get(mname, {}).get("qty", 1)
                # Parse price to USD (rough — strip currency symbols)
                raw_price = cand["price"].replace("€","").replace("£","").replace("$","").replace(",","").replace("AED","").strip()
                try:
                    price_num = float(raw_price.split()[0])
                    # Convert EUR/GBP to USD roughly
                    if "€" in cand["price"]: price_num = price_num / 0.93
                    elif "£" in cand["price"]: price_num = price_num / 0.79
                    elif "AED" in cand["price"]: price_num = price_num / 3.67
                except: price_num = 0

                # Update or add to order_items
                if "order_items" not in st.session_state:
                    st.session_state.order_items = []
                existing = next((x for x in st.session_state.order_items if x["item"] == mname), None)
                if existing:
                    existing["eu_price"] = int(price_num)
                    existing["locked_market"] = "EU"
                    existing["notes"] = f"{cand['model']} — {cand['seller'] or ''}"
                else:
                    st.session_state.order_items.append({
                        "item": mname, "qty": qty,
                        "eu_price": int(price_num), "cn_price": 0, "uae_price": 0,
                        "locked_market": "EU",
                        "notes": f"{cand['model']} — {cand['seller'] or ''}"
                    })
            st.success(f"Pushed {len(st.session_state.selected_machines)} selections to Order Builder (Tab 6)")
            st.rerun()

    # ── Progress overview ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Overall Progress</div>', unsafe_allow_html=True)
    prog_cols = st.columns(len(CLIENT_MACHINES))
    for idx, (mname, minfo) in enumerate(CLIENT_MACHINES.items()):
        sl = st.session_state.shortlists.get(mname, [])
        is_sel = mname in st.session_state.selected_machines
        color = "#4AE89E" if is_sel else ("#F5A623" if sl else "#2A3F5F")
        status = "Selected" if is_sel else (f"{len(sl)} candidates" if sl else "Not started")
        with prog_cols[idx]:
            st.markdown(f"""<div class="metric-card" style="border-top:3px solid {color}; text-align:center; padding:0.8rem;">
            <div style="font-size:0.7rem; color:{color}; font-weight:600;">{status.upper()}</div>
            <div style="font-size:0.82rem; color:#C0D0E0; margin-top:0.3rem;">{mname}</div>
            <div style="font-size:0.72rem; color:#4A6A8A;">x{minfo["qty"]}</div>
            </div>""", unsafe_allow_html=True)


with tab3:


    # ── PART A: Search Launcher ───────────────────────────────────────────────
    st.markdown('<div class="section-title">Part A — Search Launcher</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    🔗 <strong style="color:#F5A623;">Smart Deep Links</strong> — Define your specs below and we'll
    build pre-filtered search URLs for each marketplace. One click opens the platform with your
    exact filters already applied so you see only relevant listings.
    </div>""", unsafe_allow_html=True)

    la_col1, la_col2 = st.columns(2)
    with la_col1:
        la_machine = st.selectbox("Machine / Vehicle Type", [
            "Excavator", "Motor Grader", "Bulldozer", "Dump Truck", "Water Tanker Truck",
            "Wheel Loader", "Backhoe Loader", "Road Roller", "Crane", "Forklift",
            "Concrete Mixer Truck", "Truck Tractor", "Tipper Truck", "Generator"
        ], key="la_machine")
        la_condition = st.selectbox("Condition", ["Any", "New", "Used"], key="la_cond")
        la_budget = st.text_input("Max Budget (USD)", placeholder="e.g. 80000", key="la_budget")

    with la_col2:
        la_year_min = st.text_input("Year from", placeholder="e.g. 2018", key="la_yr_min")
        la_year_max = st.text_input("Year to", placeholder="e.g. 2023", key="la_yr_max")
        la_hp = st.text_input("Min Engine HP", placeholder="e.g. 120", key="la_hp")
        la_brand = st.text_input("Preferred Brand (optional)", placeholder="e.g. CAT, Komatsu, XCMG", key="la_brand")

    if st.button("🔗 Generate Search Links", key="gen_links"):
        q_machine = la_machine.lower().replace(" ", "+")
        q_brand = ("+"+la_brand.replace(" ", "+")) if la_brand else ""
        q_full = q_machine + q_brand

        # Build platform URLs
        links = {
            "Mascus (EU)": f"https://www.mascus.com/search#{q_machine}",
            "TruckScout24 (DE)": f"https://www.truckscout24.de/transporter/gebraucht/{q_machine}",
            "Autoline (EU)": f"https://autoline.eu/-/search?q={q_full}",
            "Ritchie Bros (Global)": f"https://www.rbauction.com/equipment?q={q_full}",
            "Alibaba (CN)": f"https://www.alibaba.com/trade/search?SearchText={q_full}&s=product_cnt",
            "Made-in-China (CN)": f"https://www.made-in-china.com/multi-search/{q_full}/F1/",
            "Dubizzle Heavy (UAE)": f"https://dubai.dubizzle.com/motors/heavy-equipment/?q={q_machine}",
            "IronPlanet (US)": f"https://www.ironplanet.com/results?q={q_full}",
            "MachineryZone (EU)": f"https://www.machineryzone.eu/used/1/{q_machine}.html",
        }

        filters_applied = []
        if la_condition != "Any": filters_applied.append(f"Condition: {la_condition}")
        if la_year_min or la_year_max: filters_applied.append(f"Year: {la_year_min or '?'}–{la_year_max or '?'}")
        if la_budget: filters_applied.append(f"Max budget: ${int(la_budget):,}" if la_budget.isdigit() else f"Max: ${la_budget}")
        if la_hp: filters_applied.append(f"Min HP: {la_hp}")
        filters_str = " · ".join(filters_applied) if filters_applied else "No additional filters"

        st.markdown(f"""<div class="info-box" style="margin-bottom:1rem;">
        <strong style="color:#F5A623;">Search: {la_machine}</strong> &nbsp;·&nbsp; {filters_str}<br>
        <span style="color:#4A6A8A; font-size:0.8rem;">Click any link below to open the platform with your search pre-loaded.</span>
        </div>""", unsafe_allow_html=True)

        link_cols = st.columns(3)
        link_items = list(links.items())
        market_colors = ["#4A9EF5","#E85F5F","#E85F5F","#4AE89E","#F5A623","#F5A623","#E8A84A","#4AE89E","#4A9EF5"]
        for i, (name, url) in enumerate(link_items):
            with link_cols[i % 3]:
                color = market_colors[i % len(market_colors)]
                st.markdown(f"""
                <a href="{url}" target="_blank" style="
                    display:block; background:#111827; border:1px solid #1E2D42;
                    border-left: 3px solid {color}; border-radius:8px;
                    padding:0.8rem 1rem; margin-bottom:0.6rem;
                    text-decoration:none; color:#C0D0E0;">
                    <div style="font-size:0.85rem; font-weight:600; color:{color};">{name}</div>
                    <div style="font-size:0.72rem; color:#4A6A8A; margin-top:0.2rem; word-break:break-all;">{url[:55]}...</div>
                </a>""", unsafe_allow_html=True)

        st.markdown("""<div class="info-box">
        💡 <strong style="color:#F5A623;">Tip:</strong> Open each link, find 2–3 listings you like,
        then copy the URLs or paste the listing details into <strong>Part B</strong> below to get a
        side-by-side AI comparison with a procurement verdict.
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PART B: Listing Comparator ────────────────────────────────────────────
    st.markdown('<div class="section-title">Part B — Paste Listings for AI Comparison</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box" style="border-left:3px solid #E8A84A;">
    ⚠️ <strong style="color:#E8A84A;">Accuracy depends on what you paste</strong><br>
    Claude only analyses <strong>exactly what you type here</strong>. It does not visit URLs
    or fill in missing fields from memory. Open each listing, copy the specs directly from
    the page, and paste them below. The more detail you provide, the more reliable the comparison.
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <strong style="color:#F5A623;">What to copy from each listing:</strong>
    Model name &nbsp;·&nbsp; Year &nbsp;·&nbsp; Price (with currency) &nbsp;·&nbsp;
    Engine HP/kW &nbsp;·&nbsp; Operating weight &nbsp;·&nbsp; Hours (if used) &nbsp;·&nbsp;
    Key specs/attachments &nbsp;·&nbsp; Condition &nbsp;·&nbsp; Seller &nbsp;·&nbsp; Location &nbsp;·&nbsp; Platform
    </div>""", unsafe_allow_html=True)

    cmp_machine = st.text_input(
        "What machine are you comparing?",
        placeholder="e.g. 20-tonne hydraulic excavator for road construction in Nigeria",
        key="cmp_machine"
    )

    cmp_c1, cmp_c2, cmp_c3 = st.columns(3)
    with cmp_c1:
        st.markdown("**Listing 1**")
        listing1 = st.text_area(
            "Copy & paste specs from the listing page",
            height=240, key="lst1",
            placeholder="Paste the exact text from the page, e.g.:\n\nCAT 320 GC\nYear: 2020\nHours: 4,200h\nEngine: 103 kW (138 HP)\nWeight: 20,200 kg\nBucket: 0.91 m3\nCondition: Used - Good\nPrice: 72,500 EUR\nSeller: Zeppelin GmbH\nLocation: Hamburg, Germany\nPlatform: Mascus.de"
        )
    with cmp_c2:
        st.markdown("**Listing 2**")
        listing2 = st.text_area(
            "Copy & paste specs from the listing page",
            height=240, key="lst2",
            placeholder="Paste the exact text from the page, e.g.:\n\nXCMG XE215C\nYear: 2022\nHours: 1,800h\nEngine: 115 kW (154 HP)\nWeight: 21,500 kg\nBucket: 0.93 m3\nCondition: Used - Excellent\nPrice: 38,500 USD\nSeller: XCMG International\nLocation: Shanghai, China\nPlatform: Alibaba.com"
        )
    with cmp_c3:
        st.markdown("**Listing 3 (optional)**")
        listing3 = st.text_area(
            "Copy & paste specs from the listing page",
            height=240, key="lst3",
            placeholder="Paste the exact text from the page, e.g.:\n\nKomatsu PC200-8\nYear: 2019\nHours: 6,100h\nEngine: 110 kW (148 HP)\nWeight: 20,700 kg\nBucket: 0.8 m3\nCondition: Used - Fair\nPrice: AED 195,000\nSeller: Al-Futtaim\nLocation: Dubai, UAE\nPlatform: plant.ae"
        )

    cmp_destination = st.text_input(
        "Final destination & use case",
        value=destination_country,
        key="cmp_dest"
    )

    if st.button("🤖 Compare Listings with AI", type="primary", key="cmp_btn"):
        listings = [l for l in [listing1, listing2, listing3] if l.strip()]
        if len(listings) < 2:
            st.warning("Please paste at least 2 listings to compare.")
        elif not cmp_machine.strip():
            st.warning("Please describe what machine you are comparing.")
        elif any(len(l.strip()) < 50 for l in listings):
            st.warning("One or more listings look too short. Please paste the full spec details from the listing page — not just a URL — for accurate results.")
        else:
            client = anthropic.Anthropic()
            listings_block = ""
            for i, lst in enumerate(listings, 1):
                listings_block += f"\n--- LISTING {i} (pasted verbatim by user) ---\n{lst}\n"

            prompt = f"""You are a senior construction equipment procurement specialist.

STRICT RULES — follow exactly:
1. ONLY use information explicitly written in the listing text below.
2. If a spec is not mentioned in a listing, write "NOT PROVIDED" — never fill it from memory.
3. Never infer specs from model names alone (e.g. do not assume engine HP from model number).
4. Convert prices to USD where needed — state the exchange rate used.
5. If a listing contains only a URL with no specs, write: "No specs provided — cannot compare this listing."
6. Clearly separate what is FACT (from the listing) vs ESTIMATE (your general knowledge).

Machine type: {cmp_machine}
Destination: {cmp_destination}

LISTING DATA (user-provided — treat as ground truth):
{listings_block}

## 1. EXTRACTED SPECS TABLE
Using ONLY the pasted data — mark missing fields as "NOT PROVIDED":
| Spec | Listing 1 | Listing 2 | Listing 3 |
|------|-----------|-----------|-----------|
| Model | | | |
| Year | | | |
| Price (as listed) | | | |
| Price (USD equiv.) | | | |
| Engine HP/kW | | | |
| Operating weight | | | |
| Key capacity/attachment | | | |
| Hours | | | |
| Condition | | | |
| Location | | | |
| Seller | | | |
| Platform | | | |

## 2. SPEC-BY-SPEC COMPARISON
Only compare specs present in at least 2 listings:
- ADVANTAGE: which listing wins and by how much
- DISADVANTAGE: which is weaker and why it matters
- EQUIVALENT: where listings match
- CANNOT COMPARE: field missing from one or more listings

## 3. MISSING INFORMATION
What key specs are NOT PROVIDED that you would recommend asking each seller before deciding?

## 4. GENERAL INDUSTRY CONTEXT [ESTIMATES — clearly labelled, not from listing data]
Based on general knowledge of these machine types/brands:
- Parts & service availability in West Africa [ESTIMATE]
- Typical reliability for this brand/model class [ESTIMATE]
- Resale value outlook after 5 years [ESTIMATE]

## 5. SHIPPING ESTIMATES [ESTIMATES — verify with freight forwarder]
For each listing origin to {cmp_destination}:
- Rough freight cost range, transit time, import duty % [all ESTIMATES]

## 6. PROCUREMENT VERDICT
Based strictly on provided data:
- Strongest listing on verified specs (and why)
- What to ask each seller before deciding
- Overall recommendation with honest caveats about missing information

Never invent numbers. If you cannot compare something fairly, say so."""

            with st.spinner("Comparing listings using only the data you provided..."):
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}],
                )
            result = message.content[0].text
            st.markdown("### 📋 AI Comparison Report")
            st.markdown(f'<div class="ai-response">{result}</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <div class="info-box">
            ✅ <strong style="color:#4AE89E;">Accuracy note:</strong> This report is based only on
            the text you pasted. Any field marked "NOT PROVIDED" was absent from the listing —
            contact the seller to fill those gaps before making a final procurement decision.
            </div>""", unsafe_allow_html=True)


# TAB 3 — Shipping & Logistics AI
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">AI-Powered Shipping & Customs Advisory</div>', unsafe_allow_html=True)

    sh_col1, sh_col2 = st.columns([1, 1])
    with sh_col1:
        ship_from_market = st.selectbox(
            "Procure from Market",
            list(MARKETS.keys()),
            key="ship_from"
        )
        ship_equipment = st.multiselect(
            "Equipment to Ship",
            list(EQUIPMENT_CATALOG.keys()),
            default=["Excavator", "Motor Grader", "Bulldozer (Dozer)"],
        )
        include_tyres = st.checkbox("Include 10x Truck Tyres", value=True)
        tyre_condition_ship = st.radio("Tyre Condition", ["New", "Used", "Mix (5 New + 5 Used)"], horizontal=True)

    with sh_col2:
        ship_destination = st.selectbox(
            "Ship To",
            ["Nigeria 🇳🇬 (Lagos)", "Nigeria 🇳🇬 (Apapa Port)", "Ghana 🇬🇭 (Tema Port)",
             "Kenya 🇰🇪 (Mombasa)", "South Africa 🇿🇦 (Durban)", "Other"],
            key="ship_dest"
        )
        buyer_residency = st.selectbox(
            "Buyer/Agent Residency",
            ["Germany 🇩🇪 (EU Resident)", "UK 🇬🇧", "UAE 🇦🇪", "Not resident in source country"],
        )
        shipment_method = st.selectbox(
            "Preferred Shipment Method",
            ["RO-RO (Roll-on Roll-off)", "Flat Rack Container", "Open Top Container",
             "Standard 40ft Container", "Mix — Recommend Best Option"]
        )

    # Auto-populate from order builder if items exist
    if "order_items" in st.session_state and st.session_state.order_items:
        locked_items = [r for r in st.session_state.order_items if r["locked_market"] != "TBD"]
        all_items = st.session_state.order_items
        auto_equipment = list(set([r["item"] for r in all_items]))
        auto_note = ""
        if locked_items:
            auto_note = "From Order Builder: " + ", ".join(
                f"{r['item']} x{r['qty']} from {r['locked_market']}"
                for r in locked_items
            )
        st.markdown(f"""<div class="info-box" style="margin-bottom:0.8rem;">
        ✅ <strong style="color:#4AE89E;">Order Builder has {len(all_items)} items</strong>
        &nbsp;·&nbsp; {len(locked_items)} with locked market selection.<br>
        <span style="color:#4A6A8A; font-size:0.8rem;">Equipment list below is pre-filled from your order. You can adjust it.</span>
        </div>""", unsafe_allow_html=True)
    else:
        auto_equipment = ["Excavator", "Motor Grader", "Bulldozer (Dozer)"]
        auto_note = ""

    special_notes = st.text_area(
        "Any special requirements or questions?",
        placeholder="e.g. Equipment has rubber tracks, one unit is oversized, client needs financing options, timeline is 60 days...",
        height=80
    )

    st.markdown("---")

    if st.button("🚢 Generate Full Shipping & Customs Report", type="primary"):
        with st.spinner("Consulting Claude on shipping, customs, duties & logistics..."):
            advice = get_shipping_advice(
                from_market=ship_from_market,
                to_destination=ship_destination,
                equipment_list=ship_equipment,
                include_tyres=include_tyres,
                tyre_condition=tyre_condition_ship,
                buyer_residency=buyer_residency,
                shipment_method=shipment_method,
                special_notes=special_notes,
                procurement_country=procurement_country,
            )

        st.markdown("### 📋 Shipping & Customs Advisory Report")
        st.markdown(f'<div class="ai-response">{advice}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.info("💡 **Disclaimer**: This advisory is AI-generated for guidance purposes. Always verify duties and customs requirements with a licensed freight forwarder or customs broker before finalising procurement.")
    else:
        # Static cheat sheet
        st.markdown('<div class="section-title">Quick Reference: Key Shipping Considerations</div>',
                    unsafe_allow_html=True)
        ref_col1, ref_col2, ref_col3 = st.columns(3)
        with ref_col1:
            st.markdown("""
            <div class="info-box">
            <strong style="color:#4A9EF5;">🇩🇪 → 🇳🇬 (EU to Nigeria)</strong><br><br>
            • Import Duty: ~5–35% (HS code dependent)<br>
            • VAT: 7.5% (Nigerian VAT)<br>
            • Levy: ECOWAS 0.5%, ETLS applicable<br>
            • Port: Apapa or Tin Can, Lagos<br>
            • Transit time: ~25–35 days<br>
            • Incoterms: CIF recommended
            </div>
            """, unsafe_allow_html=True)
        with ref_col2:
            st.markdown("""
            <div class="info-box">
            <strong style="color:#E85F5F;">🇨🇳 → 🇳🇬 (China to Nigeria)</strong><br><br>
            • Import Duty: ~5–35% (same HS code)<br>
            • Anti-dumping levies: check per category<br>
            • Typically longer payment terms (LC)<br>
            • Transit time: ~35–45 days<br>
            • Quality inspection: SGS/Bureau Veritas advised<br>
            • Non-resident: requires freight agent
            </div>
            """, unsafe_allow_html=True)
        with ref_col3:
            st.markdown("""
            <div class="info-box">
            <strong style="color:#E8A84A;">🧾 Non-Resident Procurement</strong><br><br>
            • Must appoint local buying agent or trading company<br>
            • VAT refund (e.g. German VAT) possible on export<br>
            • Need: Commercial invoice, Packing list, B/L, COO<br>
            • China: verify CE/ISO equivalency docs<br>
            • Consider Incoterms carefully (EXW vs DDP)<br>
            • Open LC or irrevocable LC recommended
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Client Requisition
# ══════════════════════════════════════════════════════════════════════════════
with tab5:

    st.markdown('<div class="section-title">Procurement Order Builder</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    📋 <strong style="color:#F5A623;">Dynamic Order Builder</strong> — Add machines you have sourced
    or are evaluating. Enter prices from your actual searches (Part B comparisons). The table updates
    live in your selected currency with market-by-market totals and savings breakdown.
    </div>""", unsafe_allow_html=True)

    # ── Session state for dynamic rows ───────────────────────────────────────
    if "order_items" not in st.session_state:
        st.session_state.order_items = [
            {"item": "Excavator",        "qty": 1, "eu_price": 95000,  "cn_price": 38000, "uae_price": 65000, "locked_market": "TBD", "notes": "CAT 320 / XCMG equiv."},
            {"item": "Motor Grader",     "qty": 1, "eu_price": 120000, "cn_price": 55000, "uae_price": 85000, "locked_market": "TBD", "notes": "SDLG G9180 equiv."},
            {"item": "Bulldozer (Dozer)","qty": 1, "eu_price": 85000,  "cn_price": 35000, "uae_price": 60000, "locked_market": "TBD", "notes": "CAT D6 equiv."},
            {"item": "Dump Truck",       "qty": 2, "eu_price": 38000,  "cn_price": 18000, "uae_price": 28000, "locked_market": "TBD", "notes": "10-15t payload"},
            {"item": "Water Tanker Truck","qty": 1, "eu_price": 45000, "cn_price": 22000, "uae_price": 33000, "locked_market": "TBD", "notes": "10,000L+ capacity"},
            {"item": "Truck Tyres (x5 New)","qty": 5,"eu_price": 350, "cn_price": 120,   "uae_price": 220,   "locked_market": "TBD", "notes": "22.5 rim, 11R22.5"},
            {"item": "Truck Tyres (x5 Used)","qty": 5,"eu_price": 120, "cn_price": 45,   "uae_price": 85,    "locked_market": "TBD", "notes": "Min 60% tread depth"},
        ]

    # ── Add new item form ─────────────────────────────────────────────────────
    with st.expander("➕ Add New Item to Order"):
        na, nb, nc = st.columns(3)
        with na:
            new_item_name = st.text_input("Machine / Item", placeholder="e.g. Wheel Loader", key="ni_name")
            new_item_qty  = st.number_input("Qty", min_value=1, value=1, key="ni_qty")
        with nb:
            new_eu_price  = st.number_input("EU Price (USD)", min_value=0, value=0, step=500, key="ni_eu")
            new_cn_price  = st.number_input("CN Price (USD)", min_value=0, value=0, step=500, key="ni_cn")
        with nc:
            new_uae_price = st.number_input("UAE Price (USD)", min_value=0, value=0, step=500, key="ni_uae")
            new_notes     = st.text_input("Notes / Specs", placeholder="e.g. 3t capacity, CE cert", key="ni_notes")

        if st.button("Add to Order", key="add_item_btn"):
            if new_item_name.strip():
                st.session_state.order_items.append({
                    "item": new_item_name, "qty": new_item_qty,
                    "eu_price": new_eu_price, "cn_price": new_cn_price,
                    "uae_price": new_uae_price, "locked_market": "TBD",
                    "notes": new_notes
                })
                st.success(f"Added: {new_item_name}")
                st.rerun()

    # ── Editable order table ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Current Order</div>', unsafe_allow_html=True)
    st.caption(f"All prices in {curr['code']}. Edit EU/CN/UAE prices directly to reflect your actual sourced quotes.")

    items = st.session_state.order_items
    rows_to_delete = []

    for i, row in enumerate(items):
        rc1, rc2, rc3, rc4, rc5, rc6, rc7 = st.columns([2.5, 0.6, 1.2, 1.2, 1.2, 1.8, 0.4])
        with rc1: st.markdown(f"<div style='padding:0.6rem 0; color:#C0D0E0; font-size:0.88rem;'>{row['item']}</div>", unsafe_allow_html=True)
        with rc2: st.markdown(f"<div style='padding:0.6rem 0; color:#8A9BB5; font-size:0.88rem; text-align:center;'>x{row['qty']}</div>", unsafe_allow_html=True)
        with rc3: st.markdown(f"<div style='padding:0.6rem 0; color:#4A9EF5; font-size:0.85rem;'>{fmt(row['eu_price'], selected_currency)}</div>", unsafe_allow_html=True)
        with rc4: st.markdown(f"<div style='padding:0.6rem 0; color:#E85F5F; font-size:0.85rem;'>{fmt(row['cn_price'], selected_currency)}</div>", unsafe_allow_html=True)
        with rc5: st.markdown(f"<div style='padding:0.6rem 0; color:#E8A84A; font-size:0.85rem;'>{fmt(row['uae_price'], selected_currency)}</div>", unsafe_allow_html=True)
        with rc6:
            locked = st.selectbox("Market", ["TBD","EU","CN (Alibaba)","UAE","UK","US"],
                index=["TBD","EU","CN (Alibaba)","UAE","UK","US"].index(row.get("locked_market","TBD")),
                key=f"mkt_{i}", label_visibility="collapsed")
            st.session_state.order_items[i]["locked_market"] = locked
        with rc7:
            if st.button("✕", key=f"del_{i}"):
                rows_to_delete.append(i)

    for idx in reversed(rows_to_delete):
        st.session_state.order_items.pop(idx)
    if rows_to_delete:
        st.rerun()

    # ── Totals ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Order Totals</div>', unsafe_allow_html=True)

    eu_total  = sum(r["eu_price"]  * r["qty"] for r in items)
    cn_total  = sum(r["cn_price"]  * r["qty"] for r in items)
    uae_total = sum(r["uae_price"] * r["qty"] for r in items)

    # Locked market total — use the market each item is locked to
    market_map = {"EU": "eu_price", "CN (Alibaba)": "cn_price", "UAE": "uae_price"}
    locked_total = sum(
        r.get(market_map.get(r["locked_market"], "eu_price"), r["eu_price"]) * r["qty"]
        for r in items
    )
    best_saving = eu_total - cn_total

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.markdown(f"""<div class="metric-card">
        <div class="label">EU Total</div>
        <div class="value" style="color:#4A9EF5;">{fmt(eu_total, selected_currency)}</div>
        <div class="sub">All from Europe</div></div>""", unsafe_allow_html=True)
    with t2:
        st.markdown(f"""<div class="metric-card">
        <div class="label">CN Total</div>
        <div class="value" style="color:#E85F5F;">{fmt(cn_total, selected_currency)}</div>
        <div class="sub">All from Alibaba/China</div></div>""", unsafe_allow_html=True)
    with t3:
        st.markdown(f"""<div class="metric-card">
        <div class="label">UAE Total</div>
        <div class="value" style="color:#E8A84A;">{fmt(uae_total, selected_currency)}</div>
        <div class="sub">All from Middle East</div></div>""", unsafe_allow_html=True)
    with t4:
        st.markdown(f"""<div class="metric-card">
        <div class="label">Locked Market Total</div>
        <div class="value" style="color:#4AE89E;">{fmt(locked_total, selected_currency)}</div>
        <div class="sub">Based on your market selections</div></div>""", unsafe_allow_html=True)

    # Savings bar
    savings_pct = ((eu_total - cn_total) / eu_total * 100) if eu_total else 0
    st.markdown(f"""<div class="info-box">
    💰 <strong style="color:#4AE89E;">Max Equipment Saving (EU vs CN):</strong>
    {fmt(best_saving, selected_currency)} &nbsp;({savings_pct:.1f}% cheaper) &nbsp;—&nbsp;
    <span style="color:#4A6A8A;">before shipping, duties & inspection costs</span>
    </div>""", unsafe_allow_html=True)

    # ── Pie chart ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Cost Breakdown (EU Pricing)</div>', unsafe_allow_html=True)
    pie_labels = [r["item"] for r in items]
    pie_values = [r["eu_price"] * r["qty"] for r in items]
    colors = ["#4A9EF5","#E85F5F","#4AE89E","#E8A84A","#A84AE8","#F5A623","#5A7A9A","#E85F9F","#4AE8D0"]
    fig3 = go.Figure(data=[go.Pie(
        labels=pie_labels, values=pie_values, hole=0.4,
        marker_colors=colors[:len(pie_labels)],
        textfont=dict(family="Space Grotesk"),
    )])
    fig3.update_layout(
        plot_bgcolor="#111827", paper_bgcolor="#111827",
        font=dict(color="#C0D0E0", family="Space Grotesk"),
        height=380, margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(bgcolor="#0D1421", bordercolor="#2A3F5F"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── AI Total Cost Report ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">AI Total Procurement & Shipping Cost Report</div>', unsafe_allow_html=True)

    order_summary = "\n".join([
        f"- {r['item']} x{r['qty']}: EU ${r['eu_price']:,} | CN ${r['cn_price']:,} | UAE ${r['uae_price']:,} | Selected: {r['locked_market']} | {r['notes']}"
        for r in items
    ])

    if st.button("📊 Generate Full Cost & Shipping Breakdown", type="primary", key="full_report_btn"):
        client = anthropic.Anthropic()
        prompt = f"""You are a senior procurement and logistics consultant. Generate a complete procurement cost analysis for:

CLIENT DESTINATION: {destination_country}
PROCUREMENT BASE: {procurement_country}
DISPLAY CURRENCY: {curr["code"]}

ORDER ITEMS:
{order_summary}

MARKET TOTALS (USD):
- All from EU: ${eu_total:,.0f}
- All from CN (Alibaba): ${cn_total:,.0f}
- All from UAE: ${uae_total:,.0f}
- Locked market selection total: ${locked_total:,.0f}

Provide a complete report covering:

## 1. MARKET-BY-MARKET COST COMPARISON
Show EU vs CN vs UAE total for each item and overall. Calculate which mix gives the best total value.

## 2. SMART SPLIT STRATEGY
Which items should come from which market for optimal value + reliability?
(e.g. complex machinery from EU, trucks/tyres from CN)

## 3. ESTIMATED SHIPPING COSTS
Per market of origin to {destination_country}:
- Freight cost estimate (USD) for the full order
- Recommended shipping method (RO-RO vs container)
- Estimated transit time

## 4. IMPORT DUTIES & TAXES AT DESTINATION
For each market of origin:
- Applicable import duty % (by equipment category)
- VAT at destination
- Other levies (ECOWAS, port charges etc.)
- Estimated total duty cost (USD)

## 5. TOTAL LANDED COST COMPARISON
For each scenario (all-EU, all-CN, all-UAE, smart split):
Equipment cost + Freight + Duties + Inspection = TOTAL LANDED COST

## 6. ADDITIONAL COST FACTORS
- Pre-shipment inspection (SGS/Bureau Veritas) estimate
- Insurance (marine cargo)
- Agent/freight forwarder fees
- Currency risk considerations ({curr["code"]} relevant factors)

## 7. RECOMMENDATION
Clear final recommendation with total landed cost for the best option.

Use {curr["code"]} for all monetary figures where possible (1 USD = {curr["rate"]} {curr["code"]})."""

        with st.spinner("Generating full procurement and shipping cost breakdown..."):
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3500,
                messages=[{"role": "user", "content": prompt}],
            )
        result = message.content[0].text
        st.markdown(f'<div class="ai-response">{result}</div>', unsafe_allow_html=True)
        st.markdown("---")
        st.info("💡 Verify all duty rates and freight costs with a licensed customs broker and freight forwarder before finalising.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Live Market Search (new tab, shifts old tab2 to tab3 etc)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — AI Consultant (Marcus)
# ══════════════════════════════════════════════════════════════════════════════
with tab6:

    # Session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_initialized" not in st.session_state:
        st.session_state.chat_initialized = False

    # Header
    st.markdown("""
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1.5rem;">
      <div style="width:52px; height:52px; border-radius:50%; background:#1E2D42;
           border:2px solid #E8573F; display:flex; align-items:center; justify-content:center;
           font-size:1.4rem; flex-shrink:0;">🎓</div>
      <div>
        <div style="font-size:1.1rem; font-weight:700; color:#E8EDF5;">Marcus</div>
        <div style="font-size:0.78rem; color:#8A9BB5;">Senior Procurement Consultant · PROCURA</div>
        <div style="font-size:0.72rem; color:#4AE89E;">● Online · West Africa Infrastructure Specialist</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Suggested starter questions
    if not st.session_state.chat_history:
        st.markdown('<div class="section-title">Start the Consultation</div>', unsafe_allow_html=True)
        st.markdown("""<div class="info-box">
        👋 <strong style="color:#F5A623;">Hi, I\'m Marcus.</strong> I\'ll be your procurement consultant
        for this Nigerian road construction project. I\'ll guide you on exactly what machines you need,
        which brands are right for Nigeria, and what to look out for when buying.
        <br><br>Pick a question to get started, or type your own below.
        </div>""", unsafe_allow_html=True)

        starter_qs = [
            "What machines do I actually need for a road construction project in Nigeria?",
            "Start with the excavator — what should I look for and which brands are best for Nigeria?",
            "What\'s the difference between the machines on my list and why do I need all of them?",
            "What are the biggest mistakes to avoid when buying construction equipment for Africa?",
            "Which is better for Nigeria — European brands like CAT or cheaper Chinese alternatives?",
            "Explain the motor grader to me — what does it do and what specs matter?",
            "What are the conditions like in Nigeria that affect which machines I should buy?",
            "Walk me through the full equipment list and give me your honest assessment of each.",
        ]

        sq_cols = st.columns(2)
        for i, q in enumerate(starter_qs):
            with sq_cols[i % 2]:
                if st.button(q, key=f"starter_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": q})
                    st.rerun()

    # Chat history display
    if st.session_state.chat_history:
        st.markdown('<div class="section-title">Consultation</div>', unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-end; margin-bottom:0.8rem;">
                  <div style="background:#1E2D42; border:1px solid #2A3F5F; border-radius:12px 12px 2px 12px;
                       padding:0.8rem 1.1rem; max-width:80%; font-size:0.88rem; color:#C8D8E8;">
                    {msg["content"]}
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display:flex; gap:0.8rem; margin-bottom:0.8rem; align-items:flex-start;">
                  <div style="width:32px; height:32px; border-radius:50%; background:#1E2D42;
                       border:1.5px solid #E8573F; display:flex; align-items:center;
                       justify-content:center; font-size:0.9rem; flex-shrink:0;">🎓</div>
                  <div style="background:#111827; border:1px solid #1E2D42; border-radius:2px 12px 12px 12px;
                       padding:0.8rem 1.1rem; max-width:85%; font-size:0.88rem;
                       color:#C8D8E8; line-height:1.7; white-space:pre-wrap;">
                    {msg["content"]}
                  </div>
                </div>""", unsafe_allow_html=True)

        # Auto-generate Marcus response if last message is from user
        if st.session_state.chat_history[-1]["role"] == "user":
            with st.spinner("Marcus is typing..."):
                client_ai = anthropic.Anthropic()
                messages_payload = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]
                response = client_ai.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    messages=messages_payload,
                )
                reply = response.content[0].text
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

    # Input area
    st.markdown("---")
    inp_col, btn_col = st.columns([5, 1])
    with inp_col:
        user_input = st.text_input(
            "Ask Marcus anything...",
            placeholder="e.g. What horsepower should the excavator have for Nigerian conditions?",
            key="chat_input",
            label_visibility="collapsed"
        )
    with btn_col:
        send = st.button("Send ➤", use_container_width=True, key="chat_send")

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
        st.rerun()

    # Quick follow-up suggestions (shown after conversation starts)
    if st.session_state.chat_history:
        st.markdown("<div style='margin-top:0.5rem;'>", unsafe_allow_html=True)
        follow_ups = [
            "What about the dump trucks specifically?",
            "Which brands have good parts availability in Nigeria?",
            "What should I check when inspecting a used excavator?",
            "How do I know if a price is fair or too high?",
            "What documentation do I need to import this equipment?",
            "What could go wrong with cheap Chinese machines?",
        ]
        st.markdown("<p style='font-size:0.75rem; color:#4A6A8A; margin-bottom:0.4rem;'>Quick questions:</p>", unsafe_allow_html=True)
        fq_cols = st.columns(3)
        for i, fq in enumerate(follow_ups):
            with fq_cols[i % 3]:
                if st.button(fq, key=f"fq_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": fq})
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Clear chat button
    if st.session_state.chat_history:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()
