# Agri-Access Developer Documentation

**Technical Implementation Guide**

## Quick Demo Setup

### Prerequisites
- Python 3.8+ 
- 2GB RAM minimum
- Internet connection for satellite tile services

### Installation & Launch
```bash
# Clone repository
git clone <repository-url>
cd agri-access

# Install dependencies
pip install -r requirements.txt

# Start server
python basel_iii_api.py

# Access: http://localhost:5000
```

## Demo Workflow

### 1. Access Platform
Open http://localhost:5000 in your browser

### 2. Load Demo Data
Click any of the pre-configured farm location buttons:
- 🌾 **Indramayu Rice Farm** (West Java) - Traditional rice farming
- 🌴 **Riau Palm Oil Plantation** (Sumatra) - Large-scale palm oil  
- ☕ **Temanggung Coffee Farm** (Central Java) - Mountain coffee cultivation

### 3. Analyze Credit
Click "🚀 Analyze Credit Risk" button to start the analysis

### 4. Review Results (~1 minute processing)
The platform displays:
- **Credit Score Arc**: Visual credit score with risk rating
- **Basel III Parameters**: PD, LGD, EAD, ECL calculations
- **SHAP Analysis**: Feature importance waterfall chart
- **Satellite Imagery**: 6 different satellite data sources
- **Environmental Assessment**: Weather risk factors

## Understanding the Output

### Credit Assessment
- **Credit Score**: 300-850 scale converted to Indonesian SLIK 1-5 system
- **Risk Rating**: Letter grade (AAA to CCC) based on default probability
- **Approval Probability**: Likelihood of loan approval percentage
- **Interest Rate**: Risk-adjusted rate (6-16% range)

### SHAP Explainability
- **Waterfall Chart**: Shows how each feature contributes to final score
- **Baseline**: Starting prediction value before feature adjustments
- **Feature Impact**: Positive (green) increases score, negative (red) decreases
- **Feature Categories**: Satellite (256), Weather (64), Traditional factors

### Basel III Compliance
- **PD (Probability of Default)**: Regulatory-required default likelihood
- **LGD (Loss Given Default)**: Expected loss percentage if default occurs
- **EAD (Exposure at Default)**: Loan amount exposed to loss
- **ECL (Expected Credit Loss)**: PD × LGD × EAD for regulatory reporting

## Technical Architecture

### Data Sources (Real APIs)
1. **Landsat 8**: RGB composite satellite imagery (30m resolution)
2. **Sentinel-2**: NDVI vegetation analysis (10m resolution)
3. **MODIS**: Vegetation index monitoring (250m resolution)
4. **Weather APIs**: OpenWeatherMap, Open-Meteo, BMKG Indonesia
5. **Satellite Tiles**: Real-time image processing from multiple sources

### ML Pipeline
- **Algorithm**: Random Forest Regressor (scikit-learn)
- **Features**: 320 total (256 satellite + 64 weather + traditional)
- **Multi-target**: Simultaneous prediction of PD, LGD, EAD, Credit Score
- **Explainability**: SHAP TreeExplainer for transparency

### Indonesian Banking Integration
- **SLIK Credit Scale**: 1-5 collectibility system
- **KUR Interest Rates**: 6-9% government-subsidized rates
- **NPL Integration**: 2024 agricultural sector NPL data (2.46%)
- **OJK 29/2024**: Alternative credit scoring regulation compliance

## API Testing

### Manual API Test
```bash
# Test basic connectivity
curl http://localhost:5000/api/test

# Test analysis endpoint
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "farmerName": "Test Farmer",
    "latitude": -6.7749,
    "longitude": 107.1389,
    "farmSize": 1.5,
    "primaryCrop": "rice",
    "loanAmount": 50000000,
    "loanTerm": 12,
    "loanPurpose": "working_capital",
    "collateralType": "land"
  }'

# Check model status
curl http://localhost:5000/api/model-status
```

### Python API Integration
```python
import requests

# Credit analysis request
response = requests.post('http://localhost:5000/api/analyze', json={
    'farmerName': 'Pak Budi',
    'latitude': -2.1000,
    'longitude': 102.3000,
    'farmSize': 3.2,
    'primaryCrop': 'palm oil',
    'loanAmount': 75000000,
    'loanTerm': 18,
    'loanPurpose': 'equipment',
    'collateralType': 'land'
})

# Extract Basel III results
if response.status_code == 200:
    result = response.json()
    basel = result['basel_iii_results']
    print(f"Credit Score: {basel['credit_score']}")
    print(f"Risk Rating: {basel['risk_rating']}")
    print(f"ECL: Rp {basel['expected_credit_loss']:,.0f}")
    print(f"Approval Probability: {result['formatted_results']['approval_probability']}")
```

## File Structure

### Core Application Files
```
agri-access/
├── index.html              # Web interface
├── app.js                   # Frontend logic & satellite processing
├── basel_iii_api.py        # Flask API server & ML pipeline
├── banking_credit_model.py # Random Forest model & Basel III
├── requirements.txt        # Python dependencies
├── styles.css              # Main UI styling
├── shared.css              # Common styling
├── shared.js               # Shared JavaScript utilities
├── credit-score-arc.js     # D3.js credit score visualization
├── shap-visualization.js   # SHAP waterfall charts
└── docs/                   # Comprehensive documentation
```

### Key Components
- **Flask Backend**: Pure Python server (no Node.js required)
- **Satellite Integration**: 6 real-time data sources
- **ML Model**: Multi-target Random Forest with SHAP
- **Banking Compliance**: Basel III + Indonesian SLIK standards
- **Responsive UI**: Works on desktop and mobile

## Customization & Modification

### Adding New Demo Locations
Edit `app.js` lines 133-154:
```javascript
function loadDemoLocation(farmer) {
    if (farmer === 'your_location') {
        document.getElementById('farmerName').value = 'Your Farmer Name';
        document.getElementById('latitude').value = -6.2088;
        document.getElementById('longitude').value = 106.8456;
        document.getElementById('farmSize').value = 2.0;
        // ... other parameters
    }
}
```

### Adjusting Risk Models
Edit `banking_credit_model.py` or `basel_iii_api.py`:
- **Credit Score Formula**: Lines 452-486 in `basel_iii_api.py`
- **PD Calculation**: Lines 488-504 
- **LGD Calculation**: Lines 506-520
- **Feature Weights**: Lines 571-620 (SHAP explanations)

### UI Modifications
- **Layout**: `index.html` structure and sections
- **Styling**: `styles.css` for colors, fonts, layout
- **Visualizations**: `credit-score-arc.js` and `shap-visualization.js`

## Troubleshooting

### Common Issues
- **Port 5000 busy**: Change `port=5000` in `basel_iii_api.py` line 636
- **Satellite images not loading**: Check internet connection
- **SHAP visualization empty**: Refresh page and re-run analysis
- **Import/dependency errors**: Run `pip install -r requirements.txt` manually
- **Browser compatibility**: Use Chrome/Firefox for best experience

### Debug Mode
```bash
# Enable Flask debug mode for detailed error messages
export FLASK_ENV=development
export FLASK_DEBUG=1
python basel_iii_api.py
```

### Performance Notes
- **Response Time**: ~1 minute for complete analysis
- **Memory Usage**: ~150MB baseline, 300MB under load
- **CPU Usage**: Moderate (Random Forest inference)
- **Network**: Requires internet for satellite tile services

---

## Evaluation Points for Judges

### Technical Innovation
- Real-time satellite data processing (6 sources)
- Multi-target machine learning (4 simultaneous predictions)
- SHAP explainability for regulatory transparency
- Basel III banking standard compliance

### Indonesian Context
- SLIK credit system integration (1-5 scale)
- OJK 29/2024 alternative credit scoring compliance
- Agricultural NPL data integration (2024 sector data)
- Local crops and farming patterns (rice, palm oil, coffee)

### Market Impact
- 29 million Indonesian farmers addressable market
- 70% interest rate reduction potential (26% → 6-9%)
- Geographic inclusion via satellite (no field visits)
- ~1 minute processing vs weeks for traditional assessment

### Banking Ready
- Basel III PD, LGD, EAD, ECL calculations
- API-first architecture for bank integration
- Regulatory compliance built-in
- Risk-adjusted pricing recommendations

**Platform is production-ready for pilot deployment with Indonesian banks**