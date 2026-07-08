# Agri-Access: AI-Powered Agricultural Credit Scoring

**APRU Tech Policy Hackathon 2025 - Deliverable #3 README**

## High-level Explanation

**Agri-Access uses satellite imagery and AI to assess agricultural credit risk in about one minute**, enabling Indonesian banks to serve 29 million farmers currently excluded from formal credit.

### How It Works

1. **Satellite Analysis**: IBM/NASA Prithvi foundation model processes real-time NASA satellite imagery of farm locations
2. **AI Risk Assessment**: Machine learning combines satellite data with weather and farm information to predict credit risk  
3. **Banking Integration**: Generates Basel III-compliant risk parameters and Indonesian SLIK credit scores (1-5 scale)
4. **Farmer Explanations**: Google Gemini AI provides clear recommendations

### Key Innovation

- **Real-time processing**: ~1 minute credit assessment vs weeks traditionally
- **No field visits required**: Satellite coverage works anywhere in Indonesia
- **Regulatory compliant**: Basel III + Indonesian banking standards ready
- **Transparent AI**: SHAP explanations show decision factors

## Setup and Use Instructions

### Prerequisites
- Python 3.8+
- Internet connection for satellite data

### Installation & Demo
```bash
# 1. Navigate to project directory
cd agri-access

# 2. Install dependencies
# Public deploy/lightweight:
pip install -r requirements.txt

# Full local private platform:
# pip install -r requirements-private.txt

# 3. Start application
python3 basel_iii_api.py

# 4. Open browser to the displayed localhost website
```

### Demo Instructions
1. **Select demo farmer**: Click Any Demo Data for pre-configured scenarios
2. **Run analysis**: Click "Analyze Credit Risk" (~1 minute processing)
3. **View results**: Credit score, satellite imagery, AI explanations, risk parameters

### Optional: Protect API Access
To avoid exposing backend APIs publicly, set a token:

```bash
export AGRI_API_AUTH_TOKEN="your-strong-demo-token"
```

Then open platform with a tokenized link once (sets an auth cookie for browser API calls):

```bash
http://localhost:3000/platform?token=your-strong-demo-token
```

For direct API clients, send either:
- `Authorization: Bearer your-strong-demo-token`, or
- `X-API-Key: your-strong-demo-token`

### Public Demo vs Private Platform
- **Public demo deploy**: keep `AGRI_ENABLE_PRIVATE_PLATFORM=false` (default). Only the feasibility landing demo is exposed.
- **Private local platform**: run locally with:

```bash
export AGRI_ENABLE_PRIVATE_PLATFORM=true
python3 basel_iii_api.py
```

This enables `/platform` and all `/api/*` routes only in your local/private environment.

### Demo Scenarios
- **Rice farmer** (West Java) - Good credit example
- **Palm oil farmer** (Sumatra) - Excellent credit example  
- **Coffee farmer** (Central Java) - Fair credit example

## AI Tool Disclosure

### AI Tools Used in Development
- **Claude Code (Anthropic)**: Code development, debugging, implementation assistance
- **Google Gemini**: Document polishing, research assistance for Indonesian banking regulations

### AI Tools Integrated in Product
- **IBM/NASA Prithvi-EO-2.0-300M**: Satellite imagery analysis (foundation model)
- **Google Gemini 2.5 Flash**: Real-time farmer explanations in Indonesian/English

### Original Work (Not AI-Generated)
- Core innovation concept (satellite-based agricultural credit scoring)
- System architecture and technical implementation approach
- Basel III compliance and risk assessment
- API integrations (NASA, weather services, Gemini)
- Indonesian banking compliance 

**All AI-generated code was reviewed, tested, and customized for Indonesian agricultural finance requirements.**