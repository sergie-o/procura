# 🏗️ ProcureIQ — Global Equipment Intelligence

Cross-market construction equipment price comparison and AI-powered shipping advisory tool. Built for procurement consultants sourcing heavy machinery across global markets.

## Features

- **Market Comparison Dashboard** — Compare equipment prices across EU, China (Alibaba), UAE, UK, and US markets
- **Equipment Deep Dive** — Full catalog view with multi-equipment scatter comparison and tyre specialisation
- **AI Shipping Advisor** — Claude-powered detailed shipping, customs, duties, and logistics reports for any source → destination route
- **Client Requisition Tracker** — Pre-loaded with Nigerian client order (Excavator, Grader, Dozer, Trucks, Water Tanker, Tyres)

## Setup (Local)

1. **Clone and install**
```bash
cd procure_compare
pip install -r requirements.txt
```

2. **Add API key**
```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit secrets.toml and add your ANTHROPIC_API_KEY
```

3. **Run**
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo
2. Connect repo to [share.streamlit.io](https://share.streamlit.io)
3. In app settings → Secrets, add:
```
ANTHROPIC_API_KEY = "sk-ant-..."
```
4. Set main file path: `app.py`

## Project Structure

```
procure_compare/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── data/
│   ├── __init__.py
│   └── equipment_data.py     # Equipment catalog & market price data
├── utils/
│   ├── __init__.py
│   ├── ai_advisor.py         # Claude API integration
│   └── formatting.py         # Currency/display utilities
└── .streamlit/
    └── secrets.toml          # API keys (not committed to git)
```

## Adding New Equipment / Markets

- **New equipment**: Add entry to `EQUIPMENT_CATALOG` in `data/equipment_data.py`
- **New market**: Add entry to `MARKETS` dict in `data/equipment_data.py` with prices for each equipment
- **New destination**: Update dropdown in `app.py` sidebar and shipping tab

## Notes

- Prices are indicative reference points — always verify with current supplier quotes
- Import duty rates are approximate — verify with a licensed customs broker
- Claude API calls (Shipping Advisor + Market Analysis) require a valid `ANTHROPIC_API_KEY`
