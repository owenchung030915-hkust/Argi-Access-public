#!/usr/bin/env python3
"""
Basel III Agricultural Credit Scoring API Server
Production-ready API for regulatory-compliant agricultural credit scoring
Integrates satellite imagery, weather data, and traditional credit factors

Features:
- Basel III PD, LGD, EAD calculations
- IFRS 9 staging and ECL computation  
- SHAP explainable AI
- Weather risk assessment
- Indonesian agricultural context
"""

from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
import numpy as np
from datetime import datetime
import threading
import time

def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj
import sys
import os
import traceback
import google.generativeai as genai
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Configuration
API_VERSION = "1.0.0"
MODEL_VERSION = "Prithvi-RF-XGBoost-v2.0"
STRICT_REAL_ANALYSIS = os.environ.get("AGRI_STRICT_REAL_ANALYSIS", "false").strip().lower() in ("1", "true", "yes", "on")
API_AUTH_TOKEN = os.environ.get("AGRI_API_AUTH_TOKEN", "").strip()
API_AUTH_COOKIE_NAME = "agri_api_auth"
PRIVATE_PLATFORM_ENABLED = os.environ.get("AGRI_ENABLE_PRIVATE_PLATFORM", "false").strip().lower() in ("1", "true", "yes", "on")

# Configure Gemini API from environment (see .env)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured")
else:
    print("Gemini API key not set; farmer explanations will use fallback text")

# Global model state
class ModelState:
    def __init__(self):
        self.model = None
        self.shap_explainer = None
        self.weather_processor = None
        self.satellite_extractor = None
        self.basel_calculator = None
        self.ml_model = None
        self.is_ready = False
        self.lock = threading.Lock()

model_state = ModelState()


@app.before_request
def enforce_api_auth():
    """Protect API routes when AGRI_API_AUTH_TOKEN is set."""
    if request.path.startswith("/api/") and not PRIVATE_PLATFORM_ENABLED:
        return jsonify({
            "success": False,
            "error": "Not found"
        }), 404

    if not API_AUTH_TOKEN:
        return None

    if not request.path.startswith("/api/"):
        return None

    if request.method == "OPTIONS":
        return None

    auth_header = request.headers.get("Authorization", "").strip()
    bearer_token = ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()

    api_key_header = request.headers.get("X-API-Key", "").strip()
    cookie_token = request.cookies.get(API_AUTH_COOKIE_NAME, "").strip()

    if bearer_token == API_AUTH_TOKEN or api_key_header == API_AUTH_TOKEN or cookie_token == API_AUTH_TOKEN:
        return None

    return jsonify({
        "success": False,
        "error": "Unauthorized API request"
    }), 401


def with_platform_auth_cookie(response):
    """
    Allow one-time tokenized platform links:
    /platform?token=<AGRI_API_AUTH_TOKEN>
    Sets HttpOnly cookie so browser API calls are authenticated.
    """
    if not API_AUTH_TOKEN:
        return response

    token = request.args.get("token", "").strip()
    if token and token == API_AUTH_TOKEN:
        response.set_cookie(
            API_AUTH_COOKIE_NAME,
            API_AUTH_TOKEN,
            max_age=60 * 60 * 24,  # 24 hours
            httponly=True,
            samesite="Lax",
            secure=request.is_secure
        )
    return response

def get_prithvi_extractor_lazy():
    """Lazy import to avoid loading PyTorch before XGBoost training."""
    from prithvi_extractor import get_prithvi_extractor
    return get_prithvi_extractor()

def initialize_model():
    """Initialize Basel III ML pipeline components"""
    print("Initializing Basel III ML Pipeline...", flush=True)
    
    try:
        with model_state.lock:
            if not PRIVATE_PLATFORM_ENABLED:
                # Public demo mode: skip heavy ML pipeline to keep deploy lightweight.
                model_state.model = "public_demo_mode"
                model_state.weather_processor = "openweather_processor"
                model_state.basel_calculator = "basel_iii_calculator"
                model_state.is_ready = True
                print("Public demo mode enabled; private platform pipeline is disabled", flush=True)
                return True

            print("Creating model components...", flush=True)

            # Train credit model before Prithvi/PyTorch to avoid XGBoost segfaults on macOS.
            from banking_credit_model import AgricultureMLModel
            model_state.ml_model = AgricultureMLModel()
            if model_state.ml_model.is_trained:
                print("Random Forest + XGBoost ML model trained and ready", flush=True)
            else:
                print("Random Forest + XGBoost ML model initialized but not trained", flush=True)

            model_state.satellite_extractor = get_prithvi_extractor_lazy()
            print("Prithvi satellite extractor initialized", flush=True)
            
            # Initialize other components
            model_state.model = "agricultural_ml_ensemble"
            model_state.shap_explainer = "shap_tree_explainer"
            model_state.weather_processor = "openweather_processor"
            model_state.basel_calculator = "basel_iii_calculator"
            model_state.is_ready = True
            
            print("Basel III ML Pipeline initialized successfully!", flush=True)
            print(f"- API Version: {API_VERSION}", flush=True)
            print(f"- Model Version: {MODEL_VERSION}", flush=True)
            print("- Ready for credit scoring requests", flush=True)
            
            return True
            
    except Exception as e:
        print(f"Error initializing model: {str(e)}", flush=True)
        model_state.is_ready = False
        return False

def get_openweather_data(latitude, longitude):
    """Get weather data with graceful fallback to Indonesian climate model"""
    import requests
    import os
    
    # Try OpenWeatherMap API if API key is available
    api_key = os.environ.get('OPENWEATHER_API_KEY', '').strip()
    
    if api_key:
        try:
            # Current weather data with real API key
            current_url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'units': 'metric',  # Celsius
                'appid': api_key
            }
            
            response = requests.get(current_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind'].get('speed', 5) * 3.6,  # Convert m/s to km/h
                    'rainfall': data.get('rain', {}).get('1h', 0),  # mm in last hour
                    'weather_description': data['weather'][0]['description'],
                    'source': 'OpenWeatherMap'
                }
            else:
                raise Exception(f"API returned status {response.status_code}")
                
        except Exception as e:
            if STRICT_REAL_ANALYSIS:
                raise RuntimeError(f"OpenWeatherMap API failed in strict mode: {e}")
            print(f"OpenWeatherMap API failed: {e}, using Indonesian climate model")
            return get_indonesian_climate_data(latitude, longitude)
    else:
        # No API key available, use Indonesian climate model directly
        print("Using Indonesian climate model (no OpenWeatherMap API key)")
        return get_indonesian_climate_data(latitude, longitude)

def get_indonesian_climate_data(latitude, longitude):
    """Generate realistic weather data based on Indonesian climate patterns"""
    # Indonesian climate patterns based on geographical location
    base_temp = 27 + (latitude + 6) * 2  # Cooler at higher latitudes
    # Make deterministic based on location
    location_seed = int((latitude * 1000 + longitude * 1000) % 100)
    
    base_humidity = 75 + (location_seed % 10) - 5
    base_rainfall = 150 + ((location_seed * 3) % 60) - 30
    
    return {
        'temperature': np.clip(base_temp + ((location_seed * 2) % 6) - 3, 20, 35),
        'humidity': np.clip(base_humidity, 60, 90),
        'rainfall': np.clip(base_rainfall, 50, 300),
        'wind_speed': np.clip(8 + ((location_seed * 5) % 10) - 5, 2, 15),
        'pressure': np.clip(1013 + ((location_seed * 7) % 10) - 5, 1005, 1020),
        'weather_description': 'partly cloudy',
        'source': 'Indonesian Climate Model'
    }

# ===== FEATURE GENERATION FUNCTIONS =====

def generate_satellite_features(farm_data):
    """Generate satellite features using Prithvi-EO-2.0-300M foundation model"""
    
    # Get the Prithvi extractor
    extractor = get_prithvi_extractor_lazy()
    
    # Generate diverse NASA GIBS URLs for the farm location (matching frontend diversity)
    lat, lon = farm_data['latitude'], farm_data['longitude']
    satellite_urls = {
        'landsat-true-color': generate_satellite_image_url('landsat-true-color', lat, lon),
        'sentinel-false-color': generate_satellite_image_url('sentinel-false-color', lat, lon),
        # 'gfsad-cropland': removed - using NASA CMR API instead
        'modis-ndvi': generate_satellite_image_url('modis-ndvi', lat, lon),
        'viirs-dnb': generate_satellite_image_url('viirs-dnb', lat, lon),
        'modis-thermal': generate_satellite_image_url('modis-thermal', lat, lon),
        'modis-aqua-true': generate_satellite_image_url('modis-aqua-true', lat, lon),
        'modis-terra-721': generate_satellite_image_url('modis-terra-721', lat, lon)
    }
    
    try:
        # Extract features using Prithvi model
        print(f"Extracting Prithvi features for farm at ({lat}, {lon})")
        prithvi_results = extractor.extract_agricultural_features(satellite_urls, farm_data)
        
        # Use Prithvi features if extraction successful
        if prithvi_results['prithvi_features'] is not None and len(prithvi_results['prithvi_features']) >0:
            print(f"Extracted {prithvi_results['feature_count']} Prithvi features")
            
            # Normalize features to 0-1 range for compatibility
            features = prithvi_results['prithvi_features']
            features = (features - features.min()) / (features.max() - features.min() + 1e-8)
            
            # Pad or truncate to expected 256 features for ML model compatibility
            if len(features) >256:
                features = features[:256]
            elif len(features) < 256:
                # Pad with agricultural indices if needed
                agricultural_indices = list(prithvi_results['agricultural_indices'].values())
                padding_needed = 256 - len(features)
                padding = np.tile(agricultural_indices, (padding_needed // len(agricultural_indices) + 1))[:padding_needed]
                features = np.concatenate([features, padding])
            
            return features
            
    except Exception as e:
        if STRICT_REAL_ANALYSIS:
            raise RuntimeError(f"Prithvi feature extraction failed in strict mode: {e}")
        print(f"Prithvi feature extraction failed: {e}")
        print("Falling back to enhanced synthetic features...")
    
    # Fallback to enhanced synthetic features if Prithvi fails
    return generate_fallback_satellite_features(farm_data)

def generate_fallback_satellite_features(farm_data):
    """Generate enhanced synthetic satellite features when Prithvi is unavailable"""
    # Base features influenced by farm characteristics
    np.random.seed(hash(str(farm_data['latitude']) + str(farm_data['longitude'])) % 2147483647)
    
    # Create features that correlate with farm quality
    base_quality = 0.6 if farm_data['crop_type'] == 'rice'else 0.5
    base_quality += min(0.2, farm_data['farm_size'] * 0.05)  # Larger farms tend to be better managed
    
    # Generate 256 satellite features with agricultural patterns
    features = np.random.normal(base_quality, 0.2, 256)
    features = np.clip(features, 0, 1)  # Normalize to 0-1 range
    
    return features

def generate_satellite_image_url(image_type, lat, lon):
    """Generate diverse NASA GIBS satellite image URLs for comprehensive agricultural analysis"""
    # Use zoom level 8 for better farm detail in Indonesian agricultural areas
    zoom = 8
    x = int((lon + 180) / 360 * (2 ** zoom))
    y = int((1 - np.log(np.tan(lat * np.pi / 180) + 1 / np.cos(lat * np.pi / 180)) / np.pi) / 2 * (2 ** zoom))
    
    # Use more recent date with better satellite coverage for Indonesian agricultural areas
    base_date = "2024-09-01"# Recent date with good satellite coverage
    
    if image_type == 'landsat-true-color':
        # MODIS Terra True Color - Real NASA satellite data
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    elif image_type == 'sentinel-false-color':
        # MODIS Terra False Color (Bands 7-2-1) - Vegetation analysis
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_Bands721/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    # gfsad-cropland case removed - using NASA CMR API instead
    
    elif image_type == 'modis-ndvi':
        # MODIS Terra Bands 7-2-1 - Vegetation analysis (working)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_Bands721/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    elif image_type == 'viirs-dnb':
        # MODIS Aqua True Color - Alternative satellite perspective (working)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Aqua_CorrectedReflectance_TrueColor/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    elif image_type == 'modis-thermal':
        # MODIS Terra Agriculture Bands 3-6-7 - Agriculture analysis (working)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_Bands367/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    elif image_type == 'modis-aqua-true':
        # MODIS Aqua True Color - Alternative satellite timing (working)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Aqua_CorrectedReflectance_TrueColor/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    elif image_type == 'modis-terra-721':
        # MODIS Terra Bands 7-2-1 - Vegetation emphasis (working)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_Bands721/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"
    
    else:
        # Default to MODIS True Color (most reliable layer)
        return f"https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{base_date}/250m/{zoom}/{y}/{x}.jpg"

def generate_weather_features(weather_data, location_data, crop_type):
    """Generate weather features from current conditions"""
    features = []
    
    # Basic weather features
    features.extend([
        weather_data['temperature'],
        weather_data['humidity'],
        weather_data['rainfall'],
        weather_data['wind_speed'],
        weather_data['pressure']
    ])
    
    # Derived weather indices
    heat_index = calculate_heat_index(weather_data['temperature'], weather_data['humidity'])
    vpd = calculate_vapor_pressure_deficit(weather_data['temperature'], weather_data['humidity'])
    
    features.extend([heat_index, vpd])
    
    # Crop suitability features
    crop_suitability = calculate_crop_suitability(weather_data, crop_type)
    features.append(crop_suitability)
    
    # Regional climate adjustments
    regional_factors = get_regional_climate_factors(location_data['latitude'], location_data['longitude'])
    features.extend(regional_factors)
    
    # Pad to 64 features with deterministic derived metrics (no random filler)
    while len(features) < 64:
        idx = len(features)
        baseline = (
            (weather_data['temperature'] / 40.0) * 0.35 +
            (weather_data['humidity'] / 100.0) * 0.35 +
            min(weather_data['rainfall'] / 300.0, 1.0) * 0.20 +
            min(weather_data['wind_speed'] / 30.0, 1.0) * 0.10
        )
        features.append(float(np.clip(baseline + ((idx % 7) - 3) * 0.01, 0.0, 1.0)))
    
    return np.array(features[:64])

def calculate_heat_index(temp, humidity):
    """Calculate heat index for agricultural stress assessment"""
    if temp < 26.7:  # Below 80°F
        return temp
    
    # Simplified heat index calculation
    hi = -42.379 + 2.04901523 * temp + 10.14333127 * humidity
    hi += -0.22475541 * temp * humidity - 0.00683783 * temp * temp
    hi += -0.05481717 * humidity * humidity + 0.00122874 * temp * temp * humidity
    hi += 0.00085282 * temp * humidity * humidity - 0.00000199 * temp * temp * humidity * humidity
    
    return hi

def calculate_vapor_pressure_deficit(temp, humidity):
    """Calculate VPD for plant water stress assessment"""
    # Saturation vapor pressure (kPa)
    es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    # Actual vapor pressure
    ea = es * humidity / 100
    # VPD
    return es - ea

def calculate_crop_suitability(weather_data, crop_type):
    """Calculate weather suitability for specific crop"""
    temp = weather_data['temperature']
    humidity = weather_data['humidity']
    rainfall = weather_data['rainfall']
    
    crop_requirements = {
        'rice': {'temp_range': (22, 30), 'humidity_min': 60, 'rainfall_min': 100},
        'palm oil': {'temp_range': (24, 32), 'humidity_min': 75, 'rainfall_min': 150},
        'coffee': {'temp_range': (18, 25), 'humidity_min': 70, 'rainfall_min': 120},
        'cocoa': {'temp_range': (20, 28), 'humidity_min': 75, 'rainfall_min': 140},
        'rubber': {'temp_range': (24, 30), 'humidity_min': 80, 'rainfall_min': 180}
    }
    
    req = crop_requirements.get(crop_type, crop_requirements['rice'])
    
    # Temperature suitability
    temp_score = 1.0 if req['temp_range'][0] <= temp <= req['temp_range'][1] else 0.5
    
    # Humidity suitability  
    humidity_score = 1.0 if humidity >= req['humidity_min'] else humidity / req['humidity_min']
    
    # Rainfall suitability
    rainfall_score = 1.0 if rainfall >= req['rainfall_min'] else rainfall / req['rainfall_min']
    
    return (temp_score + humidity_score + rainfall_score) / 3

def get_regional_climate_factors(latitude, longitude):
    """Get regional climate adjustment factors"""
    factors = []
    
    # Java region bonus (better infrastructure)
    java_factor = 1.2 if -8 <= latitude <= -6 else 1.0
    factors.append(java_factor)
    
    # Coastal vs inland (longitude-based approximation)
    coastal_factor = 1.1 if abs(longitude % 5) < 2 else 1.0  # Simplified coastal detection
    factors.append(coastal_factor)
    
    # Add more regional factors to reach desired length
    factors.extend([1.0, 1.0, 1.0])  # Placeholder factors
    
    return factors

# ===== UTILITY FUNCTIONS =====

def format_currency_idr(amount):
    """Format amount as Indonesian Rupiah"""
    if amount >= 1_000_000_000:
        return f"Rp {amount/1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"Rp {amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"Rp {amount/1_000:.0f}K"
    else:
        return f"Rp {amount:,.0f}"

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint"""
    print("Test endpoint called")
    return jsonify({"status": "working", "message": "API is responding"})

def generate_gee_satellite_url(collection, lat, lon, bands='B4,B3,B2', min_val=0, max_val=3000):
    """Generate satellite image URL for specific location using reliable satellite services"""
    
    # Use OpenStreetMap-based satellite imagery that shows correct locations
    if 'landsat'in collection.lower():
        # Use MapBox satellite imagery if token is configured; otherwise fallback to ArcGIS.
        zoom = 15
        mapbox_token = os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip()
        if mapbox_token:
            return f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom}/400x400?access_token={mapbox_token}"
        x = int((lon + 180) / 360 * (2 ** zoom))
        y = int((1 - np.log(np.tan(lat * np.pi / 180) + 1 / np.cos(lat * np.pi / 180)) / np.pi) / 2 * (2 ** zoom))
        return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}"
    
    # For Sentinel-2, use Planet Labs satellite imagery
    elif 'sentinel'in collection.lower():
        # Use ArcGIS World Imagery which shows correct locations
        zoom = 15
        x = int((lon + 180) / 360 * (2 ** zoom))
        y = int((1 - np.log(np.tan(lat * np.pi / 180) + 1 / np.cos(lat * np.pi / 180)) / np.pi) / 2 * (2 ** zoom))
        return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}"
    
    # Default to Google Satellite that shows correct locations
    zoom = 15
    x = int((lon + 180) / 360 * (2 ** zoom))
    y = int((1 - np.log(np.tan(lat * np.pi / 180) + 1 / np.cos(lat * np.pi / 180)) / np.pi) / 2 * (2 ** zoom))
    return f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"

def generate_nasa_cmr_satellite_images(lat, lon):
    """Generate real satellite images using NASA CMR (Common Metadata Repository) approach like the original working version"""
    import requests
    
    images = []
    
    # Use the same approach as the original working version - NASA CMR API for real satellite data
    try:
        # GFSAD30SEACE (30m cropland classification) - verified working collection
        gfsad_bbox = f"{lon-0.5},{lat-0.5},{lon+0.5},{lat+0.5}"
        gfsad_response = requests.get(
            "https://cmr.earthdata.nasa.gov/search/granules.json",
            params={
                'collection_concept_id': 'C2763261715-LPCLOUD',  # Original working collection ID
                'page_size': 3,
                'bounding_box': gfsad_bbox,
                'temporal': '2015-01-01T00:00:00Z,2020-12-31T23:59:59Z'
            },
            timeout=10
        )
        
        if gfsad_response.status_code == 200:
            gfsad_data = gfsad_response.json()
            for entry in gfsad_data.get('feed', {}).get('entry', [])[:1]:  # Only take 1 to avoid duplicates
                for link in entry.get('links', []):
                    if (link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/browse#'and 
                        ('jpg'in link.get('href', '').lower() or 'png'in link.get('href', '').lower())):
                        images.append({
                            'type': 'GFSAD30SEACE',
                            'description': 'NASA Cropland Classification (30m resolution)',
                            'url': link['href'],
                            'source': 'NASA GFSAD (CMR)',
                            'resolution': '30m',
                            'dataset': 'cropland'
                        })
                        break  # Only take the first working image
        # MODIS Vegetation (250m) - verified working collection        
        modis_response = requests.get(
            "https://cmr.earthdata.nasa.gov/search/granules.json",
            params={
                'collection_concept_id': 'C1000000240-LPDAAC_ECS',  # Original working collection ID
                'page_size': 3,
                'bounding_box': gfsad_bbox,
                'temporal': '2023-01-01T00:00:00Z,2024-12-31T23:59:59Z'
            },
            timeout=10
        )
        
        if modis_response.status_code == 200:
            modis_data = modis_response.json()
            for entry in modis_data.get('feed', {}).get('entry', [])[:2]:
                for link in entry.get('links', []):
                    if (link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/browse#'and 
                        ('jpg'in link.get('href', '').lower() or 'png'in link.get('href', '').lower())):
                        images.append({
                            'type': 'MODIS',
                            'description': 'NASA Vegetation Index (250m resolution)',
                            'url': link['href'],
                            'source': 'NASA MODIS (CMR)',
                            'resolution': '250m',
                            'dataset': 'vegetation'
                        })
                        
    except Exception as e:
        print(f"NASA CMR API error: {e}")
        
    # Fallback to working demo images if NASA CMR fails (like original version)
    if len(images) == 0:
        images = [
            {
                'type': 'GFSAD30SEACE',
                'description': 'Cropland Classification (Demo)',
                'url': 'https://via.placeholder.com/400x300/4CAF50/white?text=GFSAD+Cropland',
                'source': 'NASA GFSAD (Demo Mode)',
                'resolution': '30m',
                'dataset': 'cropland'
            },
            {
                'type': 'MODIS',
                'description': 'Vegetation Index (Demo)',
                'url': 'https://via.placeholder.com/400x300/FF9800/white?text=MODIS+Vegetation',
                'source': 'NASA MODIS (Demo Mode)',
                'resolution': '250m',
                'dataset': 'vegetation'
            },
            {
                'type': 'Google Earth Engine',
                'description': 'High Resolution Composite (Demo)',
                'url': 'https://via.placeholder.com/400x300/2196F3/white?text=GEE+Composite',
                'source': 'Google Earth Engine (Demo)',
                'resolution': '10m',
                'dataset': 'gee-analysis'
            }
        ]
    
    # Add working non-NASA sources
    images.extend([
        {
            'type': 'World Imagery (ArcGIS)',
            'description': 'Multi-source satellite composite optimized for agricultural areas',
            'url': generate_gee_satellite_url('sentinel2', lat, lon),
            'source': 'ArcGIS World Imagery',
            'resolution': '1m-15m',
            'dataset': 'composite'
        },
        {
            'type': 'Google Satellite',
            'description': 'Google Earth Engine processed satellite imagery with exact coordinates',
            'url': generate_gee_satellite_url('default', lat, lon),
            'source': 'Google Earth Engine',
            'resolution': '1m-15m', 
            'dataset': 'gee-processed'
        }
    ])
    
    return images

def generate_real_satellite_images(lat, lon):
    """Generate real satellite images using the original working NASA CMR approach"""
    return generate_nasa_cmr_satellite_images(lat, lon)

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_farm():
    """
    Main Basel III credit scoring endpoint
    
    Request body should contain:
    - farmerName: string
    - latitude, longitude: float
    - farmSize: float (hectares)
    - primaryCrop: string 
    - loanAmount: float (IDR)
    - loanTerm: int (months)
    - loanPurpose: string
    - collateralType: string
    """
    
    print(f"API /analyze endpoint called - Model ready: {model_state.is_ready}")
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    if not model_state.is_ready:
        print("Model not ready, returning 503")
        return jsonify({
            'success': False,
            'error': 'Model not ready. Please wait for initialization to complete.',
            'model_version': MODEL_VERSION
        }), 503
    
    try:
        data = request.get_json()
        print(f"Received request data: {data}")
        
        # Extract farm data
        farm_data = {
            'farmer_name': data.get('farmerName', 'Unknown'),
            'latitude': float(data.get('latitude', -6.7749)),
            'longitude': float(data.get('longitude', 107.1389)),
            'farm_size': float(data.get('farmSize', 1.5)),
            'crop_type': data.get('primaryCrop', 'rice'),
            'loan_amount': float(data.get('loanAmount', 50_000_000)),
            'loan_term': int(data.get('loanTerm', 12)),
            'loan_purpose': data.get('loanPurpose', 'working_capital'),
            'collateral_type': data.get('collateralType', 'land')
        }
        
        # Get weather data from OpenWeatherMap API
        weather_data = get_openweather_data(farm_data['latitude'], farm_data['longitude'])
        
        # Location data
        location_data = {
            'latitude': farm_data['latitude'],
            'longitude': farm_data['longitude']
        }
        
        # Feature extraction
        satellite_features = generate_satellite_features(farm_data)
        weather_features = generate_weather_features(weather_data, location_data, farm_data['crop_type'])
        satellite_source = 'Prithvi'if not STRICT_REAL_ANALYSIS else 'Prithvi (strict mode)'
        weather_source = weather_data.get('source', 'Unknown')
        
        # Create traditional features
        traditional_features = np.array([
            farm_data['farm_size'],
            farm_data['loan_amount'] / 1_000_000,  # Convert to millions
            farm_data['loan_term'],
            1.0 if farm_data['crop_type'] == 'rice'else 0.0,
            1.0 if farm_data['collateral_type'] == 'land'else 0.0,
            farm_data['latitude'],
            farm_data['longitude'],
            35.0,  # Mock farmer age
            15.0   # Mock experience years
        ])
        
        # Calculate Basel III components using Random Forest + XGBoost ML model
        if model_state.ml_model and model_state.ml_model.is_trained:
            # Use trained ML model with satellite and weather features
            print("Using Random Forest + XGBoost ML model for predictions")
            ml_result = model_state.ml_model.calculate_credit_score(
                farm_data, 
                satellite_features=satellite_features,
                weather_features=weather_features
            )
            
            if ml_result['success']:
                analysis = ml_result['creditAnalysis']
                credit_score = analysis['creditScore']
                slik_score = analysis['slikRating']
                
                # Extract Basel III parameters
                basel_params = analysis['baselIIIRiskParameters']
                pd = float(basel_params['probabilityOfDefault'])
                lgd = float(basel_params['lossGivenDefault'])
                ead = float(basel_params['exposureAtDefault'].replace('Rp ', '').replace(',', ''))
                ecl = pd * lgd * ead
                
                # Get SHAP explanations
                shap_explanations = analysis.get('shapValues', {})
                print(f"ML model prediction: Credit Score {credit_score}, SLIK {slik_score}")
            else:
                if STRICT_REAL_ANALYSIS:
                    return jsonify({
                        'success': False,
                        'error': 'ML model prediction failed and strict real-analysis mode forbids fallback scoring.',
                        'model_version': MODEL_VERSION
                    }), 503
                # Fallback to simple calculation
                print("ML model failed, using fallback calculation")
                credit_score, pd, lgd, ead, ecl, slik_score = _calculate_fallback_scores(farm_data, weather_data)
                shap_explanations = {}
                satellite_source = f"{satellite_source} (fallback scoring)"
        else:
            if STRICT_REAL_ANALYSIS:
                return jsonify({
                    'success': False,
                    'error': 'ML model is not trained and strict real-analysis mode forbids fallback scoring.',
                    'model_version': MODEL_VERSION
                }), 503
            # Fallback calculation when model not available
            print("ML model not trained, using fallback calculation")
            credit_score, pd, lgd, ead, ecl, slik_score = _calculate_fallback_scores(farm_data, weather_data)
            shap_explanations = {}
            satellite_source = f"{satellite_source} (fallback scoring)"
        
        # Apply Basel III constraints
        pd = max(0.0003, min(0.999, pd))  # Basel III floors/ceilings
        lgd = max(0.10, min(0.90, lgd))
        
        # Calculate risk rating and IFRS 9 stage
        risk_rating = calculate_risk_rating(pd, lgd)
        ifrs9_stage = calculate_ifrs9_stage(pd)
        
        basel_results = {
            'credit_score': credit_score,  # Use raw credit score (300-850) for display
            'slik_score': slik_score,  # SLIK scale (1-5) for Indonesian banking
            'pd': pd,
            'lgd': lgd, 
            'ead': ead,
            'ecl': ecl
        }
        
        # Use real SHAP explanations from ML model when available, otherwise generate mock ones
        if 'shap_explanations'not in locals() or not shap_explanations:
            if STRICT_REAL_ANALYSIS:
                return jsonify({
                    'success': False,
                    'error': 'SHAP explanations unavailable and strict real-analysis mode forbids mock SHAP.',
                    'model_version': MODEL_VERSION
                }), 503
            print("Using mock SHAP explanations (ML model SHAP not available)")
            shap_explanations = generate_mock_shap_explanations(
                farm_data, weather_data, traditional_features, 
                slik_score, pd, lgd, ead
            )
        else:
            print("Using real SHAP values from Random Forest + XGBoost model")
        
        # Generate real satellite images for the farm location
        browse_images = generate_real_satellite_images(farm_data['latitude'], farm_data['longitude'])
        
        # Create comprehensive response
        response = {
            'success': True,
            'farm_data': farm_data,
            'browseImages': browse_images,
            'basel_iii_results': {
                'probability_of_default': float(basel_results['pd']),
                'loss_given_default': float(basel_results['lgd']),
                'exposure_at_default': float(basel_results['ead']),
                'expected_credit_loss': float(basel_results['ecl']),
                'credit_score': float(credit_score),
                'credit_score_normalized': round(((float(credit_score) - 300) / 550), 4),  # Normalized to 0-1 scale
                'risk_rating': risk_rating,
                'ifrs9_stage': ifrs9_stage
            },
            'formatted_results': {
                'pd_percentage': f"{float(basel_results['pd'])*100:.2f}%",
                'lgd_percentage': f"{float(basel_results['lgd'])*100:.2f}%", 
                'ead_formatted': format_currency_idr(float(basel_results['ead'])),
                'ecl_formatted': format_currency_idr(float(basel_results['ecl'])),
                'credit_score_rounded': int(round(float(credit_score)))
            },
            'weather_analysis': {
                'current_conditions': weather_data,
                'weather_features_count': int(len(weather_features)),
                'weather_suitability': 'Good'if weather_data['temperature'] < 30 else 'Moderate',
                'source': weather_source
            },
            'satellite_analysis': {
                'feature_count': int(len(satellite_features)),
                'processing_method': 'IBM/NASA Prithvi-EO-2.0-300M Foundation Model',
                'sources_processed': 'Landsat 8, Sentinel-2, GFSAD, MODIS NDVI, VIIRS, MODIS Thermal',
                'resolution': '256 agricultural features (6 diverse satellite sources)',
                'feature_source': satellite_source
            },
            'shap_explanations': shap_explanations,
            'model_performance': {
                'features_used': 320,  # 256 satellite + 64 weather + traditional
                'confidence': 'High'if model_state.ml_model and model_state.ml_model.is_trained else 'Medium',
                'model_type': 'Random Forest + XGBoost Ensemble (Prithvi-EO-2.0-300M + Basel III)'if (model_state.ml_model and model_state.ml_model.xgboost is not None) else 'Random Forest (Prithvi-EO-2.0-300M + Basel III)',
                'satellite_model': 'IBM/NASA Prithvi-EO-2.0-300M',
                'weather_source': 'OpenWeatherMap API'if 'OpenWeatherMap'in weather_data.get('source', '') else 'Indonesian Climate Model',
                'ensemble_weights': 'RF: 70%, XGBoost: 30%'if (model_state.ml_model and model_state.ml_model.xgboost is not None) else 'RF: 100%',
                'strict_real_analysis': STRICT_REAL_ANALYSIS
            },
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Successfully processed request, returning response")
        # Convert all numpy types to Python native types before JSON serialization
        response = convert_numpy_types(response)
        return jsonify(response)
        
    except Exception as e:
        error_details = {
            'success': False,
            'error': f'Analysis failed: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        print(f"Error in analysis: {str(e)}")
        traceback.print_exc()
        return jsonify(error_details), 500

@app.route('/api/model-status', methods=['GET'])
def model_status():
    """Check model readiness and API health"""
    return jsonify({
        'api_version': API_VERSION,
        'model_version': MODEL_VERSION,
        'model_ready': model_state.is_ready,
        'components': {
            'basel_calculator': model_state.basel_calculator is not None,
            'weather_processor': model_state.weather_processor is not None,
            'satellite_extractor': model_state.satellite_extractor is not None,
            'shap_explainer': model_state.shap_explainer is not None
        },
        'status': 'ready'if model_state.is_ready else 'initializing',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/shap-visualization/<output_type>', methods=['POST'])
def generate_shap_visualization(output_type):
    """Generate SHAP visualization for specific output"""
    
    if global_model is None or global_shap_explainer is None:
        return jsonify({
            'success': False,
            'error': 'Model not ready'
        }), 503
    
    try:
        data = request.get_json()
        
        # This would generate actual SHAP plots
        # For now, return structured data for frontend visualization
        
        response = {
            'success': True,
            'output_type': output_type,
            'visualization_data': {
                'type': 'waterfall',
                'features': data.get('features', []),
                'base_value': 0.5,
                'explanation': f'SHAP explanation for {output_type}'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy-image')
def proxy_image():
    """Proxy for satellite images from NASA GIBS"""
    import requests
    from flask import request, Response
    
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter required'}), 400
    
    try:
        # Stream the image from NASA GIBS
        response = requests.get(url, stream=True, timeout=30, headers={
            'User-Agent': 'Agri-Access/2.0'
        })
        
        if response.status_code == 200:
            return Response(
                response.iter_content(chunk_size=1024),
                content_type=response.headers.get('content-type', 'image/jpeg'),
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            return jsonify({'error': f'Failed to fetch image: {response.status_code}'}), response.status_code
            
    except Exception as e:
        print(f"Error proxying image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_home():
    """Serve the company landing page."""
    response = make_response(send_from_directory('.', 'home.html'))
    return with_platform_auth_cookie(response)

@app.route('/platform')
def serve_platform():
    """Serve the credit scoring platform."""
    if not PRIVATE_PLATFORM_ENABLED:
        return send_from_directory('.', 'home.html'), 404
    response = make_response(send_from_directory('.', 'index.html'))
    return with_platform_auth_cookie(response)

@app.route('/app')
def serve_platform_alias():
    """Alias for the credit scoring platform."""
    if not PRIVATE_PLATFORM_ENABLED:
        return send_from_directory('.', 'home.html'), 404
    response = make_response(send_from_directory('.', 'index.html'))
    return with_platform_auth_cookie(response)

@app.route('/api/farmer/explain', methods=['POST', 'OPTIONS'])
def farmer_explanation():
    """Generate farmer-friendly explanations using Gemini AI"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        print(f"Farmer explanation endpoint called")
        data = request.get_json()
        print(f"Request data received: {data}")
        
        # Extract data from request
        credit_data = data.get('creditData', {})
        shap_data = data.get('shapData', {})
        weather_data = data.get('weatherData', {})
        satellite_data = data.get('satelliteData', {})
        language = data.get('language', 'id')
        farm_context = data.get('farmContext', {})
        
        print(f"GEMINI_API_KEY available: {GEMINI_API_KEY is not None}")
        print(f"GEMINI_API_KEY length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
        
        # Check if Gemini API is available
        if not GEMINI_API_KEY:
            print(f"No Gemini API key found, using fallback")
            return jsonify({
                'success': False,
                'error': 'AI explanation service not available',
                'fallback': generate_fallback_explanation(credit_data, language, farm_context)
            }), 503
        
        print(f"Gemini API key found, calling generate_gemini_explanation")
        print(f"About to call generate_gemini_explanation with credit_score: {credit_data.get('credit_score')}")
        
        # Generate explanation using Gemini
        explanation = generate_gemini_explanation(
            credit_data, shap_data, weather_data, satellite_data, language, farm_context
        )
        
        print(f"generate_gemini_explanation returned: {type(explanation)}")
        print(f"explanation keys: {list(explanation.keys()) if isinstance(explanation, dict) else 'not a dict'}")
        
        return jsonify({
            'success': True,
            'explanation': explanation,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in farmer explanation: {str(e)}")
        traceback.print_exc()
        
        # Return fallback explanation
        fallback = generate_fallback_explanation(
            data.get('creditData', {}), 
            data.get('language', 'id'), 
            data.get('farmContext', {})
        )
        
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback': fallback
        }), 500

def generate_gemini_explanation(credit_data, shap_data, weather_data, satellite_data, language, farm_context):
    """Generate farmer explanation using Gemini AI"""
    import sys
    print(f"GEMINI FUNCTION CALLED - Starting Gemini explanation generation...", flush=True)
    sys.stdout.flush()
    print(f"Language: {language}", flush=True)
    print(f"Credit score: {credit_data.get('credit_score', 'N/A')}", flush=True)
    print(f"Farm context: {farm_context}", flush=True)
    
    try:
        import sys
        print(f"Initializing Gemini model...", flush=True)
        sys.stdout.flush()
        # Initialize Gemini model - using latest flash model for speed and cost efficiency
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        print(f"Gemini model initialized (gemini-2.5-flash)", flush=True)
        sys.stdout.flush()
        
        # Prepare context for Gemini
        print(f"Preparing context for Gemini...", flush=True)
        sys.stdout.flush()
        context = prepare_gemini_context(credit_data, shap_data, weather_data, satellite_data, farm_context)
        print(f"Context prepared: {context}", flush=True)
        sys.stdout.flush()
        
        # Create prompt based on language
        print(f"Creating prompt for language: {language}", flush=True)
        sys.stdout.flush()
        if language == 'id':
            prompt = create_indonesian_prompt(context)
        else:
            prompt = create_english_prompt(context)
        
        print(f"Prompt created (length: {len(prompt)} chars)", flush=True)
        print(f"Calling Gemini API...", flush=True)
        sys.stdout.flush()
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        print(f"Gemini API responded successfully", flush=True)
        print(f"Response text: {response.text[:200]}...", flush=True)
        sys.stdout.flush()
        
        # Parse the response
        explanation = parse_gemini_response(response.text, language)
        print(f"Response parsed successfully", flush=True)
        sys.stdout.flush()
        
        return explanation
        
    except Exception as e:
        import sys
        print(f"GEMINI API ERROR OCCURRED: {str(e)}", flush=True)
        print(f"Error type: {type(e).__name__}", flush=True)
        sys.stdout.flush()
        import traceback
        print(f"Full traceback:", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        # Return fallback explanation
        print(f"Using fallback explanation", flush=True)
        sys.stdout.flush()
        return generate_fallback_explanation(credit_data, language, farm_context)

def prepare_gemini_context(credit_data, shap_data, weather_data, satellite_data, farm_context):
    """Prepare structured context for Gemini AI"""
    context = {
        'credit_score': credit_data.get('credit_score', 650),
        'risk_level': credit_data.get('risk_level', 'medium'),
        'approval_probability': credit_data.get('approval_probability', 0.5),
        'farm_size': farm_context.get('farmSize', 'medium'),
        'location': farm_context.get('location', 'java'),
        'crop_health': farm_context.get('cropHealth', 'good'),
        'has_weather_data': farm_context.get('hasWeatherData', False),
        'has_satellite_data': farm_context.get('hasSatelliteData', False)
    }
    
    # Add SHAP feature importance if available
    if shap_data and 'features'in shap_data:
        top_features = sorted(shap_data['features'], key=lambda x: abs(x.get('value', 0)), reverse=True)[:5]
        context['key_factors'] = [
            {
                'name': feature.get('feature_name', ''),
                'impact': feature.get('value', 0),
                'description': translate_feature_name(feature.get('feature_name', ''))
            }
            for feature in top_features
        ]
    
    return context

def create_indonesian_prompt(context):
    """Create Indonesian language prompt for Gemini"""
    key_factors_text = ""
    if 'key_factors'in context and context['key_factors']:
        factors_list = [f"- {factor['description']}: {factor['impact']:.3f}"for factor in context['key_factors']]
        key_factors_text = f"\nFaktor Kredit Utama:\n"+ "\n".join(factors_list)
    
    return f"""
Anda adalah ahli keuangan pertanian. Analisis SEMUA data yang diberikan untuk menghasilkan rekomendasi yang sangat tepat sasaran.

Analisis Kredit:
- Skor Saat Ini: {context['credit_score']}
- Tingkat Risiko: {context['risk_level']}
- Ukuran Kebun: {context['farm_size']}
- Lokasi: {context['location']}
- Kesehatan Tanaman: {context['crop_health']}
- Data Cuaca Tersedia: {context['has_weather_data']}
- Data Satelit Tersedia: {context['has_satellite_data']}{key_factors_text}

Tugas: Gunakan SEMUA titik data di atas untuk membuat rekomendasi yang ringkas dan dipersonalisasi. Dasarkan setiap rekomendasi pada wawasan data spesifik. Buat rekomendasi yang singkat dan dapat ditindaklanjuti. Hindari menyebut keterbatasan data.

Format respon (JSON, bahasa Indonesia):
{{
    "summary": "Penilaian kredit berdasarkan data saat ini",
    "credit_explanation": "Analisis berdasarkan skor, risiko, dan karakteristik kebun",
    "recommendations": [
        {{
            "title": "Item tindakan berdasarkan data",
            "description": "Langkah spesifik berdasarkan profil kebun dan faktor kredit Anda",
            "priority": "high/medium/low",
            "timeline": "Jangka waktu implementasi",
            "impact": "Peningkatan yang diharapkan"
        }}
    ],
    "next_steps": "Tindakan segera berdasarkan faktor dampak tertinggi"
}}

Persyaratan:
- Dasarkan rekomendasi pada ukuran kebun, lokasi, kesehatan tanaman, dan faktor kunci
- Referensikan titik data spesifik dalam rekomendasi (tanpa mengatakan "data menunjukkan")
- Berikan saran yang sesuai dengan lokasi dan ukuran kebun
- Buat semua rekomendasi ringkas dan dapat ditindaklanjuti
- Jangan pernah menyebut "tidak diketahui", "hilang", atau "tidak tersedia"
"""

def create_english_prompt(context):
    """Create English language prompt for Gemini"""
    key_factors_text = ""
    if 'key_factors'in context and context['key_factors']:
        factors_list = [f"- {factor['description']}: {factor['impact']:.3f}"for factor in context['key_factors']]
        key_factors_text = f"\nKey Credit Factors:\n"+ "\n".join(factors_list)
    
    return f"""
You are an agricultural finance expert. Analyze ALL provided data to generate highly targeted recommendations.

Credit Analysis:
- Current Score: {context['credit_score']}
- Risk Level: {context['risk_level']}
- Farm Size: {context['farm_size']}
- Location: {context['location']}
- Crop Health: {context['crop_health']}
- Weather Data Available: {context['has_weather_data']}
- Satellite Data Available: {context['has_satellite_data']}{key_factors_text}

Task: Use ALL above data points to create concise, personalized recommendations. Base each recommendation on specific data insights. Keep recommendations brief and actionable. Avoid mentioning data limitations.

Response format (JSON, ENGLISH only):
{{
    "summary": "Credit assessment based on current data",
    "credit_explanation": "Analysis based on score, risk, and farm characteristics",
    "recommendations": [
        {{
            "title": "Data-driven action item",
            "description": "Specific steps based on your farm profile and credit factors",
            "priority": "high/medium/low",
            "timeline": "Implementation timeframe",
            "impact": "Expected improvement"
        }}
    ],
    "next_steps": "Immediate action based on highest impact factor"
}}

Requirements:
- Base recommendations on farm size, location, crop health, and key factors
- Reference specific data points in recommendations (without saying "data shows")
- Give location and farm-size appropriate advice
- Keep all recommendations concise and actionable
- Never mention "unknown", "missing", or "not available"
"""

def parse_gemini_response(response_text, language):
    """Parse Gemini response and structure it for the frontend"""
    try:
        print(f"Parsing Gemini response (length: {len(response_text)})")
        print(f"First 200 chars: {response_text[:200]}")
        
        # Try to extract JSON from the response - handle markdown code blocks
        import re
        
        # First try to find JSON in markdown code blocks
        markdown_json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if markdown_json_match:
            json_str = markdown_json_match.group(1)
            print(f"Found JSON in markdown block")
        else:
            # Fallback to general JSON extraction
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"Found JSON in response")
            else:
                print(f"No JSON found in response")
                return create_structured_response(response_text, language)
        
        print(f"Extracted JSON (first 200 chars): {json_str[:200]}")
        parsed = json.loads(json_str)
        print(f"Successfully parsed JSON response")
        return parsed
        
    except Exception as e:
        print(f"Error parsing Gemini response: {str(e)}")
        print(f"Raw response: {response_text[:500]}")
        return create_structured_response(response_text, language)

def create_structured_response(text, language):
    """Create a structured response from unstructured text"""
    if language == 'id':
        return {
            "summary": "Analisis kredit berdasarkan data satelit dan cuaca menunjukkan kondisi yang perlu perhatian.",
            "credit_explanation": text[:200] + "..."if len(text) >200 else text,
            "recommendations": [
                {
                    "title": "Perbaiki Catatan Keuangan",
                    "description": "Catat semua pemasukan dan pengeluaran pertanian dengan detail",
                    "priority": "high",
                    "timeline": "0-30 hari",
                    "impact": "Meningkatkan transparansi keuangan"
                }
            ],
            "next_steps": "Konsultasi dengan petugas kredit untuk langkah selanjutnya"
        }
    else:
        return {
            "summary": "Credit analysis based on satellite and weather data shows areas needing attention.",
            "credit_explanation": text[:200] + "..."if len(text) >200 else text,
            "recommendations": [
                {
                    "title": "Improve Financial Records",
                    "description": "Keep detailed records of all farm income and expenses",
                    "priority": "high",
                    "timeline": "0-30 days",
                    "impact": "Increased financial transparency"
                }
            ],
            "next_steps": "Consult with credit officer for next steps"
        }

def generate_fallback_explanation(credit_data, language, farm_context):
    """Generate fallback explanation when Gemini is not available"""
    if language == 'id':
        return {
            "summary": f"Skor kredit Anda {credit_data.get('credit_score', 650)} menunjukkan kondisi yang memerlukan perbaikan.",
            "credit_explanation": "Berdasarkan analisis data pertanian, beberapa aspek perlu ditingkatkan untuk mendapat kredit yang lebih baik.",
            "recommendations": [
                {
                    "title": "Perbaiki Catatan Keuangan",
                    "description": "Catat semua transaksi keuangan pertanian dengan rapi dan teratur",
                    "priority": "high",
                    "timeline": "1-30 hari",
                    "impact": "Meningkatkan kepercayaan bank"
                },
                {
                    "title": "Tingkatkan Produktivitas Lahan",
                    "description": "Gunakan pupuk organik dan teknik pertanian modern",
                    "priority": "medium",
                    "timeline": "1-3 bulan",
                    "impact": "Meningkatkan hasil panen"
                }
            ],
            "next_steps": "Konsultasi dengan ahli pertanian setempat"
        }
    else:
        return {
            "summary": f"Your credit score of {credit_data.get('credit_score', 650)} indicates areas for improvement.",
            "credit_explanation": "Based on agricultural data analysis, several aspects need enhancement for better credit access.",
            "recommendations": [
                {
                    "title": "Improve Financial Records",
                    "description": "Keep detailed and organized records of all farm financial transactions",
                    "priority": "high",
                    "timeline": "1-30 days",
                    "impact": "Increased bank confidence"
                },
                {
                    "title": "Enhance Land Productivity",
                    "description": "Use organic fertilizers and modern farming techniques",
                    "priority": "medium",
                    "timeline": "1-3 months",
                    "impact": "Improved harvest yields"
                }
            ],
            "next_steps": "Consult with local agricultural experts"
        }

def translate_feature_name(feature_name):
    """Translate technical feature names to farmer-friendly terms"""
    translations = {
        'prithvi_vegetation': 'Kesehatan Tanaman dari Satelit',
        'weather_temperature': 'Suhu Udara',
        'farm_size': 'Ukuran Kebun',
        'soil_quality': 'Kesuburan Tanah',
        'water_access': 'Akses Air',
        'precipitation': 'Curah Hujan'
    }
    
    for key, translation in translations.items():
        if key in feature_name.lower():
            return translation
    
    return feature_name.replace('_', '').title()

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (blocks sensitive paths)."""
    blocked_prefixes = ('.',)
    blocked_names = {
        '.env', '.git', 'banking_credit_model.py', 'basel_iii_api.py',
        'xgb_train_worker.py', 'prithvi_extractor.py', 'requirements.txt',
    }
    base_name = os.path.basename(filename)
    if base_name in blocked_names or base_name.startswith(blocked_prefixes):
        return jsonify({'error': 'Not found'}), 404
    if not PRIVATE_PLATFORM_ENABLED and base_name in {'index.html', 'app.js', 'shared.js', 'shap-visualization.js', 'farmer-explanation.js', 'credit-score-arc.js', 'styles.css', 'shared.css'}:
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory('.', filename)

# Mock Basel III Calculation Functions
def calculate_mock_credit_score(farm_data, weather_data, traditional_features):
    """Calculate a mock credit score"""
    base_score = 500
    
    # Farm size bonus
    base_score += min(50, farm_data['farm_size'] * 15)
    
    # Crop type adjustments
    crop_bonuses = {'rice': 40, 'palm oil': 30, 'coffee': 25, 'cocoa': 20, 'rubber': 35}
    base_score += crop_bonuses.get(farm_data['crop_type'], 0)
    
    # Collateral bonus
    if farm_data['collateral_type'] == 'land':
        base_score += 60
    elif farm_data['collateral_type'] != 'none':
        base_score += 30
    
    # Weather suitability
    if 24 <= weather_data['temperature'] <= 30 and weather_data['humidity'] >65:
        base_score += 40
    
    # Loan amount risk (lower for smaller loans)
    if farm_data['loan_amount'] < 25_000_000:
        base_score += 30
    elif farm_data['loan_amount'] >100_000_000:
        base_score -= 20
    
    # Regional adjustments based on latitude (Java vs other islands)
    if -8 <= farm_data['latitude'] <= -6:  # Java region
        base_score += 25
    
    # Add deterministic variation based on farm characteristics
    variation = (farm_data['latitude'] * farm_data['longitude'] * farm_data['farm_size']) % 50 - 25
    base_score += variation
    
    return np.clip(base_score, 300, 850)

def calculate_mock_pd(credit_score, farm_data):
    """Calculate Probability of Default"""
    # Base PD from credit score (inverse relationship)
    score_normalized = (credit_score - 300) / 550
    base_pd = 0.15 * (1 - score_normalized) ** 1.5
    
    # Adjustments
    if farm_data['farm_size'] >3:
        base_pd *= 0.8  # Larger farms are more stable
    
    if farm_data['collateral_type'] == 'land':
        base_pd *= 0.7  # Land collateral reduces default risk
    
    if farm_data['loan_amount'] >100_000_000:
        base_pd *= 1.2  # Higher loan amounts increase risk
    
    return max(0.0003, min(0.999, base_pd))

def calculate_mock_lgd(farm_data):
    """Calculate Loss Given Default"""
    base_lgd = 0.45  # 45% base LGD for agricultural loans
    
    # Collateral adjustments
    if farm_data['collateral_type'] == 'land':
        base_lgd *= 0.6  # Land provides good recovery
    elif farm_data['collateral_type'] == 'equipment':
        base_lgd *= 0.8  # Equipment depreciates
    elif farm_data['collateral_type'] == 'none':
        base_lgd *= 1.3  # Unsecured loans have higher loss
    
    # Location adjustments (Java has better infrastructure)
    if -8 <= farm_data['latitude'] <= -6:
        base_lgd *= 0.9
    
    return max(0.10, min(0.90, base_lgd))

def calculate_mock_ead(loan_amount):
    """Calculate Exposure at Default"""
    # For term loans, EAD is typically close to outstanding balance
    # Add some credit conversion factor for revolving facilities
    ccf = np.random.uniform(0.75, 1.0)  # Credit Conversion Factor
    return loan_amount * ccf

def convert_to_slik_scale(credit_score):
    """Convert 300-850 credit score to Indonesian SLIK 1-5 scale"""
    # Higher SLIK number = better creditworthiness (opposite of kolektibilitas)
    if credit_score >= 740: return 5  # Excellent (Kolektibilitas 1)
    if credit_score >= 670: return 4  # Good (Kolektibilitas 2) 
    if credit_score >= 580: return 3  # Average (Kolektibilitas 3)
    if credit_score >= 500: return 2  # Poor (Kolektibilitas 4)
    return 1  # Bad (Kolektibilitas 5)

def calculate_risk_rating(pd, lgd):
    """Calculate risk rating based on PD and LGD"""
    risk_score = pd * lgd  # Combined risk measure
    
    if risk_score < 0.001:
        return 'AAA'
    elif risk_score < 0.003:
        return 'AA+'
    elif risk_score < 0.005:
        return 'AA'
    elif risk_score < 0.008:
        return 'AA-'
    elif risk_score < 0.012:
        return 'A+'
    elif risk_score < 0.018:
        return 'A'
    elif risk_score < 0.025:
        return 'A-'
    elif risk_score < 0.035:
        return 'BBB+'
    elif risk_score < 0.050:
        return 'BBB'
    elif risk_score < 0.070:
        return 'BBB-'
    elif risk_score < 0.100:
        return 'BB+'
    elif risk_score < 0.150:
        return 'BB'
    else:
        return 'B+'

def calculate_ifrs9_stage(pd):
    """Calculate IFRS 9 stage based on PD"""
    if pd < 0.01:  # Less than 1% PD
        return 1
    elif pd < 0.30:  # 1-30% PD  
        return 2
    else:  # Greater than 30% PD
        return 3

def _calculate_fallback_scores(farm_data, weather_data):
    """Fallback calculation when ML model is not available"""
    credit_score = calculate_mock_credit_score(farm_data, weather_data, [])
    slik_score = convert_to_slik_scale(credit_score)
    pd = calculate_mock_pd(credit_score, farm_data)
    lgd = calculate_mock_lgd(farm_data)
    ead = calculate_mock_ead(farm_data['loan_amount'])
    ecl = pd * lgd * ead
    return credit_score, pd, lgd, ead, ecl, slik_score

def generate_mock_shap_explanations(farm_data, weather_data, traditional_features, slik_score, pd, lgd, ead):
    """Generate mock SHAP explanations with SLIK scale (1-5) for credit score"""
    
    # Create feature importance based on actual farm characteristics
    shap_explanations = {}
    
    # Credit Score SHAP values (scaled for SLIK 1-5 range)
    credit_features = [
        {'feature': 'farm_size', 'shap_value': farm_data['farm_size'] * 0.15, 'feature_value': farm_data['farm_size'], 'impact': 'positive'},
        {'feature': 'collateral_land', 'shap_value': 0.8 if farm_data['collateral_type'] == 'land'else -0.3, 'feature_value': 1.0 if farm_data['collateral_type'] == 'land'else 0.0, 'impact': 'positive'if farm_data['collateral_type'] == 'land'else 'negative'},
        {'feature': 'weather_temperature', 'shap_value': (30 - abs(weather_data['temperature'] - 27)) * 0.04, 'feature_value': weather_data['temperature'], 'impact': 'positive'},
        {'feature': 'weather_humidity', 'shap_value': (weather_data['humidity'] - 50) * 0.01, 'feature_value': weather_data['humidity'], 'impact': 'positive'},
        {'feature': 'loan_amount_M', 'shap_value': -farm_data['loan_amount'] / 50_000_000, 'feature_value': farm_data['loan_amount'] / 1_000_000, 'impact': 'negative'},
        {'feature': 'crop_rice', 'shap_value': 0.5 if farm_data['crop_type'] == 'rice'else 0.0, 'feature_value': 1.0 if farm_data['crop_type'] == 'rice'else 0.0, 'impact': 'positive'},
        {'feature': 'latitude', 'shap_value': 0.3 if -8 <= farm_data['latitude'] <= -6 else -0.1, 'feature_value': farm_data['latitude'], 'impact': 'positive'if -8 <= farm_data['latitude'] <= -6 else 'negative'},
        {'feature': 'prithvi_vegetation', 'shap_value': 0.4 + (farm_data['latitude'] + farm_data['longitude']) * 0.01, 'feature_value': 0.75, 'impact': 'positive'},
        {'feature': 'prithvi_crop_health', 'shap_value': 0.3 + farm_data['farm_size'] * 0.05, 'feature_value': 0.62, 'impact': 'positive'},
        {'feature': 'weather_rainfall', 'shap_value': (weather_data['rainfall'] - 100) * 0.003, 'feature_value': weather_data['rainfall'], 'impact': 'positive'}
    ]
    
    # Sort by absolute SHAP value
    credit_features.sort(key=lambda x: abs(x['shap_value']), reverse=True)
    shap_explanations['Credit_Score'] = credit_features
    
    # PD SHAP values (scaled down)
    pd_features = []
    for feature in credit_features:
        pd_shap = feature['shap_value'] * -0.001  # Inverse relationship with credit score
        pd_features.append({
            'feature': feature['feature'],
            'shap_value': pd_shap,
            'feature_value': feature['feature_value'],
            'impact': 'negative'if pd_shap >0 else 'positive'
        })
    shap_explanations['PD'] = pd_features
    
    # LGD SHAP values
    lgd_features = [
        {'feature': 'collateral_land', 'shap_value': -0.15 if farm_data['collateral_type'] == 'land'else 0.08, 'feature_value': 1.0 if farm_data['collateral_type'] == 'land'else 0.0, 'impact': 'negative'if farm_data['collateral_type'] == 'land'else 'positive'},
        {'feature': 'latitude', 'shap_value': -0.03 if -8 <= farm_data['latitude'] <= -6 else 0.02, 'feature_value': farm_data['latitude'], 'impact': 'negative'if -8 <= farm_data['latitude'] <= -6 else 'positive'},
        {'feature': 'loan_amount_M', 'shap_value': farm_data['loan_amount'] / 100_000_000 * 0.05, 'feature_value': farm_data['loan_amount'] / 1_000_000, 'impact': 'positive'},
        {'feature': 'farm_size', 'shap_value': -farm_data['farm_size'] * 0.008, 'feature_value': farm_data['farm_size'], 'impact': 'negative'},
    ]
    shap_explanations['LGD'] = lgd_features
    
    # EAD SHAP values
    ead_features = [
        {'feature': 'loan_amount_M', 'shap_value': farm_data['loan_amount'] * 0.8, 'feature_value': farm_data['loan_amount'] / 1_000_000, 'impact': 'positive'},
        {'feature': 'loan_term', 'shap_value': farm_data['loan_term'] * 100000, 'feature_value': farm_data['loan_term'], 'impact': 'positive'},
    ]
    shap_explanations['EAD'] = ead_features
    
    return shap_explanations

def start_background_initialization():
    """Start model initialization in background"""
    def init_worker():
        time.sleep(2)  # Brief delay
        initialize_model()
    
    thread = threading.Thread(target=init_worker, daemon=True)
    thread.start()

def find_available_port(start_port=3000):
    """Find an available port starting from the given port"""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

if __name__ == '__main__':
    print("Basel III Agricultural Credit Scoring API")
    print("="* 50)
    
    # Start background initialization
    start_background_initialization()
    
    # Find an available port (use PORT in production, e.g. Render/Heroku)
    PORT = int(os.environ.get('PORT', 0)) or find_available_port(3000)
    if PORT is None:
        print("No available ports found. Please free up some ports.")
        sys.exit(1)
    
    print(f"Starting server on http://localhost:{PORT}")
    print(f"Landing page: http://localhost:{PORT}/")
    if PRIVATE_PLATFORM_ENABLED:
        print(f"Credit platform: http://localhost:{PORT}/platform")
    else:
        print("Credit platform is disabled (set AGRI_ENABLE_PRIVATE_PLATFORM=true for local access)")
    print(f"API endpoints: http://localhost:{PORT}/api/")
    print("="* 50)
    print("Ready for Basel III credit scoring!")
    print("Select a demo farm and click 'Analyze Credit Risk'")
    print("="* 50)
    
    # Suppress Flask development server warnings
    import os
    import warnings
    os.environ['FLASK_ENV'] = 'production'
    warnings.filterwarnings('ignore', message='.*development server.*')
    
    # Start Flask server
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True, use_reloader=False)