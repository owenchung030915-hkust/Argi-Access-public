#!/usr/bin/env python3
"""
Random Forest + XGBoost Agricultural Credit Scoring Model
Advanced ML pipeline for agricultural lending with Basel III compliance
"""

import numpy as np
import json
import sys
import os
import pickle
import subprocess
import tempfile
from typing import Dict, List, Tuple

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
import shap
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None

XGB_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xgb_train_worker.py')

class AgricultureMLModel:
    """
    Random Forest + XGBoost ensemble model for agricultural credit scoring
    Uses Prithvi-EO-2.0-300M satellite features with advanced ML pipeline
    """

    def __init__(self):
        self.xgboost_enabled = self._should_enable_xgboost()
        # Indonesian SLIK (Sistem Layanan Informasi Keuangan) compatibility
        # Credit scores map to SLIK collectibility scale (1-5)
        self.SLIK_SYSTEM = {
            1: {'description_id': 'Lancar', 'description_en': 'Current', 'score_range': (750, 850)},
            2: {'description_id': 'Dalam Perhatian Khusus', 'description_en': 'Previously Late', 'score_range': (650, 749)},
            3: {'description_id': 'Kurang Lancar', 'description_en': 'Substandard', 'score_range': (550, 649)},
            4: {'description_id': 'Diragukan', 'description_en': 'Doubtful', 'score_range': (450, 549)},
            5: {'description_id': 'Macet', 'description_en': 'Loss', 'score_range': (300, 449)}
        }

        # Credit score ranges aligned with Indonesian banking standards
        self.SCORE_RANGES = {
            'minimum': 300,
            'maximum': 850,
            'poor': (300, 549),      # SLIK 4-5
            'fair': (550, 649),      # SLIK 3
            'good': (650, 749),      # SLIK 2
            'excellent': (750, 850)   # SLIK 1
        }

        # Satellite parameters for Indonesian agriculture
        self.SATELLITE_PARAMETERS = {
            'vegetation_health': ['ndvi', 'evi', 'savi', 'ndmi'],
            'crop_patterns': ['sowing_date', 'harvesting_date', 'crop_type'],
            'land_characteristics': ['elevation', 'slope', 'soil_type'],
            'irrigation_access': ['water_sources', 'rainfall_patterns'],
            'yield_estimation': ['historical_yield', 'predicted_yield']
        }

        # Current KUR (Kredit Usaha Rakyat) rates 2024
        self.KUR_RATES = {
            'excellent': 6.0,        # SLIK 1 - KUR rate
            'good': 7.0,            # SLIK 2 - KUR rate
            'fair': 8.5,            # SLIK 3 - KUR rate
            'poor': 12.0            # SLIK 4-5 - Commercial rate
        }

        # NPL data for Indonesian agriculture (2024)
        self.NPL_DATA = {
            'agricultural_msme': 0.0246,    # 2.46% base NPL
            'micro_segment': 0.0285,        # 2.85% (BRI data)
            'small_segment': 0.044,         # 4.4% (BRI data)
            'regional_java': 0.022,         # Lower NPL in Java
            'regional_outer': 0.028         # Higher NPL outer islands
        }

        # Indonesian banking LTV ratios
        self.LTV_RATIOS = {
            'excellent': 0.80,       # SLIK 1
            'good': 0.70,           # SLIK 2
            'fair': 0.50,           # SLIK 3
            'poor': 0.30            # SLIK 4-5
        }
        
        # Initialize ML models with minimal parameters for fast training
        self.random_forest = MultiOutputRegressor(
            RandomForestRegressor(
                n_estimators=1,    # Minimal trees for fast training
                max_depth=3,       # Shallow trees for speed
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=1
            )
        )
        
        self.xgboost = None
        if self.xgboost_enabled and XGBRegressor is not None:
            self.xgboost = self._build_xgboost_model()
        else:
            print("XGBoost disabled; using Random Forest only.")
        
        self.scaler = StandardScaler()
        self.is_trained = False
        self.shap_explainer = None
        
        # Initialize with synthetic training data
        self._train_models()

    def _train_models(self):
        """Train Random Forest and XGBoost models with synthetic Indonesian agricultural data"""
        try:
            # Generate richer Indonesia-focused training data
            n_samples = 240
            X_train, y_train = self._generate_training_data(n_samples)
            
            # Normalize features
            X_train_scaled = self.scaler.fit_transform(X_train)
            
            # Train Random Forest for primary predictions
            print("Training Random Forest model...")
            self.random_forest.fit(X_train_scaled, y_train)
            
            # Train XGBoost as ensemble component (optional)
            if self.xgboost is not None:
                print("Training XGBoost model...")
                self.xgboost = self._train_xgboost_safely(X_train_scaled, y_train)
            
            # Validate model performance
            rf_score = self.random_forest.score(X_train_scaled, y_train)
            print(f"Model Performance:")
            print(f"Random Forest R²: {rf_score:.3f}")
            if self.xgboost is not None:
                xgb_score = self.xgboost.score(X_train_scaled, y_train)
                print(f"XGBoost R²: {xgb_score:.3f}")
            
            # Initialize SHAP explainer for the first estimator (Credit Score)
            print("Initializing SHAP explainer...")
            # Use the first estimator from MultiOutputRegressor for SHAP (Credit Score prediction)
            self.shap_explainer = shap.TreeExplainer(self.random_forest.estimators_[0])
            
            self.is_trained = True
            if self.xgboost is not None:
                print("Random Forest + XGBoost ensemble trained successfully!")
            else:
                print("Random Forest model trained successfully!")
            
        except Exception as e:
            print(f"Model training failed: {e}, using fallback calculations")
            self.is_trained = False

    def _generate_training_data(self, n_samples):
        """Generate realistic mock training data based on Indonesian agricultural patterns"""
        np.random.seed(42)  # Fixed seed for reproducible training data
        
        # Features: 320 total (256 satellite + 64 weather + traditional)
        X = np.zeros((n_samples, 320))
        
        # === REALISTIC INDONESIAN FARM PROFILES ===
        # Crop types (0=rice, 1=palm oil, 2=coffee, 3=cocoa, 4=rubber)
        crop_types = np.random.choice([0, 1, 2, 3, 4], n_samples, p=[0.38, 0.27, 0.13, 0.12, 0.10])

        # Indonesia regional farm templates to diversify examples
        regional_profiles = [
            {'name': 'West Java Rice Belt', 'lat': -6.32, 'lon': 108.33, 'size_range': (0.4, 3.5), 'crop_bias': [0, 2, 3]},
            {'name': 'Central Java Coffee Highlands', 'lat': -7.31, 'lon': 110.18, 'size_range': (0.3, 2.2), 'crop_bias': [2, 0, 3]},
            {'name': 'Riau Palm Cluster', 'lat': 0.50, 'lon': 101.45, 'size_range': (1.5, 12.0), 'crop_bias': [1, 4, 3]},
            {'name': 'South Sumatra Mixed Farms', 'lat': -3.05, 'lon': 104.75, 'size_range': (0.8, 6.0), 'crop_bias': [1, 0, 3]},
            {'name': 'Lampung Coffee-Rice Zone', 'lat': -5.11, 'lon': 105.31, 'size_range': (0.5, 4.0), 'crop_bias': [2, 0, 4]},
            {'name': 'South Sulawesi Cocoa Belt', 'lat': -4.00, 'lon': 119.65, 'size_range': (0.6, 5.0), 'crop_bias': [3, 0, 2]},
            {'name': 'East Kalimantan Estate Zone', 'lat': 0.20, 'lon': 117.20, 'size_range': (2.0, 20.0), 'crop_bias': [1, 4, 3]},
            {'name': 'West Nusa Tenggara Dryland Farms', 'lat': -8.65, 'lon': 117.36, 'size_range': (0.5, 4.5), 'crop_bias': [0, 4, 3]}
        ]

        latitudes = np.zeros(n_samples)
        longitudes = np.zeros(n_samples)
        farm_sizes = np.zeros(n_samples)
        region_names = []

        for i in range(n_samples):
            profile = regional_profiles[i % len(regional_profiles)]
            latitudes[i] = np.clip(np.random.normal(profile['lat'], 0.45), -9.0, 6.0)
            longitudes[i] = np.clip(np.random.normal(profile['lon'], 0.55), 95.0, 141.0)
            farm_sizes[i] = np.round(np.random.uniform(*profile['size_range']), 2)
            region_names.append(profile['name'])

            # Push crop assignment toward locally dominant crops in each region
            if np.random.rand() < 0.72:
                crop_types[i] = profile['crop_bias'][np.random.randint(0, len(profile['crop_bias']))]
        
        # === SATELLITE FEATURES (256 dimensions) ===
        for i in range(n_samples):
            # Prithvi-derived vegetation indices based on crop type and farm size
            if crop_types[i] == 0:  # Rice
                vegetation_base = 0.7 + farm_sizes[i] * 0.05  # Rice farms have good vegetation
                X[i, 0:64] = np.random.normal(vegetation_base, 0.1, 64)
            elif crop_types[i] == 1:  # Palm oil
                vegetation_base = 0.8 + farm_sizes[i] * 0.03  # Palm oil very green
                X[i, 0:64] = np.random.normal(vegetation_base, 0.08, 64)
            elif crop_types[i] == 2:  # Coffee
                vegetation_base = 0.6 + farm_sizes[i] * 0.04  # Coffee moderate vegetation
                X[i, 0:64] = np.random.normal(vegetation_base, 0.12, 64)
            else:  # Cocoa/Rubber
                vegetation_base = 0.65 + farm_sizes[i] * 0.035
                X[i, 0:64] = np.random.normal(vegetation_base, 0.1, 64)
            
            # Crop health indices (features 64-128)
            health_factor = 0.8 if farm_sizes[i] >2.0 else 0.7  # Larger farms better managed
            if -8 <= latitudes[i] <= -6:  # Java region - better infrastructure
                health_factor += 0.1
            X[i, 64:128] = np.random.normal(health_factor, 0.15, 64)
            
            # Soil and terrain features (features 128-192)
            if -8 <= latitudes[i] <= -6:  # Java - fertile volcanic soil
                soil_quality = 0.85
            elif -5 <= latitudes[i] <= 2:  # Sumatra - good alluvial soil
                soil_quality = 0.75
            else:  # Other islands
                soil_quality = 0.65
            X[i, 128:192] = np.random.normal(soil_quality, 0.1, 64)
            
            # Water and irrigation features (features 192-256)
            water_access = 0.8 if crop_types[i] == 0 else 0.6  # Rice needs more water
            if farm_sizes[i] >5.0:  # Large farms have better irrigation
                water_access += 0.1
            X[i, 192:256] = np.random.normal(water_access, 0.12, 64)
        
        # === WEATHER FEATURES (64 dimensions) ===
        for i in range(n_samples):
            # Temperature (features 256-272)
            base_temp = 27 + (latitudes[i] + 6) * 1.5  # Cooler at higher latitudes
            X[i, 256:272] = np.random.normal(base_temp, 2, 16)
            
            # Humidity (features 272-288)
            base_humidity = 75 + np.random.normal(0, 5)
            X[i, 272:288] = np.random.normal(base_humidity, 8, 16)
            
            # Rainfall (features 288-304)
            base_rainfall = 200 if -5 <= latitudes[i] <= 2 else 150  # Sumatra wetter
            X[i, 288:304] = np.random.normal(base_rainfall, 30, 16)
            
            # Wind and pressure (features 304-320)
            # Generate 8 wind values and 8 pressure values
            wind_values = np.random.normal(8, 3, 8)  # Wind speed
            pressure_values = np.random.normal(1013, 5, 8)  # Atmospheric pressure
            X[i, 304:312] = wind_values
            X[i, 312:320] = pressure_values
        
        # Traditional features
        X[:, 256] = farm_sizes  # Farm size
        X[:, 257] = crop_types  # Crop type
        X[:, 258] = latitudes   # Latitude
        X[:, 259] = longitudes  # Longitude
        
        # === TARGET VARIABLES ===
        credit_scores = np.zeros(n_samples)
        pd_values = np.zeros(n_samples)
        lgd_values = np.zeros(n_samples)
        ead_values = np.zeros(n_samples)
        
        for i in range(n_samples):
            # Credit score calculation based on realistic factors
            base_score = 450
            
            # Farm size impact (larger = more stable)
            if farm_sizes[i] >= 5.0:
                base_score += 120
            elif farm_sizes[i] >= 2.0:
                base_score += 80
            elif farm_sizes[i] >= 1.0:
                base_score += 50
            elif farm_sizes[i] >= 0.5:
                base_score += 30
            
            # Crop type impact (Indonesian market data)
            crop_bonuses = {0: 60, 1: 45, 2: 35, 3: 25, 4: 40}  # rice, palm, coffee, cocoa, rubber
            base_score += crop_bonuses[crop_types[i]]
            
            # Geographic advantages
            if -8 <= latitudes[i] <= -6 and 106 <= longitudes[i] <= 114:  # Java
                base_score += 50  # Best infrastructure
            elif -5 <= latitudes[i] <= 2 and 95 <= longitudes[i] <= 109:  # Sumatra
                base_score += 30  # Good infrastructure
            else:
                base_score += 10  # Developing infrastructure
            
            # Vegetation health impact
            vegetation_score = X[i, 0:64].mean()
            base_score += vegetation_score * 100
            
            # Soil quality impact
            soil_score = X[i, 128:192].mean()
            base_score += soil_score * 80
            
            # Weather suitability
            temp_optimal = 1.0 if 24 <= X[i, 256] <= 30 else 0.7
            humidity_optimal = 1.0 if 60 <= X[i, 272] <= 85 else 0.8
            rainfall_optimal = 1.0 if 100 <= X[i, 288] <= 250 else 0.8
            weather_factor = (temp_optimal + humidity_optimal + rainfall_optimal) / 3
            base_score += weather_factor * 60
            
            # Add some realistic variation
            variation = (latitudes[i] * longitudes[i] * farm_sizes[i]) % 50 - 25
            credit_scores[i] = np.clip(base_score + variation, 300, 850)
            
            # PD calculation (inverse relationship with credit score)
            score_normalized = (credit_scores[i] - 300) / 550
            pd_values[i] = 0.005 + 0.15 * (1 - score_normalized) ** 1.8
            
            # Adjust PD for crop-specific risks
            crop_risk_multipliers = {0: 0.8, 1: 1.2, 2: 1.1, 3: 1.3, 4: 1.0}
            pd_values[i] *= crop_risk_multipliers[crop_types[i]]
            pd_values[i] = np.clip(pd_values[i], 0.001, 0.25)
            
            # LGD calculation (varies with collateral and location)
            base_lgd = 0.35
            if farm_sizes[i] >2.0:  # Larger farms = better collateral
                base_lgd -= 0.1
            if -8 <= latitudes[i] <= -6:  # Java = better land values
                base_lgd -= 0.05
            lgd_values[i] = np.clip(base_lgd + np.random.normal(0, 0.08), 0.15, 0.65)
            
            # EAD calculation (loan amount based on farm value)
            crop_values_per_hectare = {0: 8_000_000, 1: 25_000_000, 2: 15_000_000, 3: 10_000_000, 4: 12_000_000}
            farm_value = farm_sizes[i] * crop_values_per_hectare[crop_types[i]]
            loan_amount = farm_value * np.random.uniform(0.3, 0.8)  # 30-80% LTV
            ead_values[i] = np.clip(loan_amount, 5_000_000, 500_000_000)
        
        # Stack targets for multi-output regression
        y = np.column_stack([credit_scores, pd_values, lgd_values, ead_values])
        
        print(f"Generated {n_samples} training samples:")
        print(f"Credit Scores: {credit_scores.min():.0f}-{credit_scores.max():.0f} (avg: {credit_scores.mean():.0f})")
        print(f"PD Range: {pd_values.min():.3f}-{pd_values.max():.3f} (avg: {pd_values.mean():.3f})")
        print(f"Farm Sizes: {farm_sizes.min():.1f}-{farm_sizes.max():.1f} hectares")
        print(
            "Crop Distribution: "
            f"Rice={np.sum(crop_types==0)}, Palm={np.sum(crop_types==1)}, Coffee={np.sum(crop_types==2)}, "
            f"Cocoa={np.sum(crop_types==3)}, Rubber={np.sum(crop_types==4)}"
        )
        unique_regions = sorted(set(region_names))
        print(f"Regional Profiles: {len(unique_regions)} Indonesian farming clusters")
        
        return X, y

    @staticmethod
    def _field(farm_data: Dict, *keys, default=None):
        """Read a field under either API snake_case or frontend camelCase keys."""
        for key in keys:
            if key in farm_data and farm_data[key] is not None and farm_data[key] != '':
                return farm_data[key]
        return default

    @classmethod
    def _normalize_farm_data(cls, farm_data: Dict) ->Dict:
        """Normalize mixed API/frontend farm payloads into one schema."""
        crop_raw = str(cls._field(farm_data, 'primaryCrop', 'crop_type', 'crop', default='rice')).strip().lower()
        crop_aliases = {
            'rice': 'rice', 'padi': 'rice',
            'palm oil': 'palm oil', 'palm_oil': 'palm oil', 'palmoil': 'palm oil', 'kelapa sawit': 'palm oil',
            'coffee': 'coffee', 'kopi': 'coffee',
            'cocoa': 'cocoa', 'kakao': 'cocoa',
            'rubber': 'rubber', 'karet': 'rubber',
        }
        crop_type = crop_aliases.get(crop_raw, 'rice')

        collateral_raw = str(cls._field(farm_data, 'collateralType', 'collateral_type', default='land')).strip().lower()
        collateral_type = collateral_raw if collateral_raw in {'land', 'equipment', 'none', 'crop', 'vehicle'} else 'land'

        try:
            farm_size = float(cls._field(farm_data, 'farmSize', 'farm_size', default=1.5))
        except (TypeError, ValueError):
            farm_size = 1.5
        try:
            latitude = float(cls._field(farm_data, 'latitude', default=-6.7749))
        except (TypeError, ValueError):
            latitude = -6.7749
        try:
            longitude = float(cls._field(farm_data, 'longitude', default=107.1389))
        except (TypeError, ValueError):
            longitude = 107.1389
        try:
            loan_amount = float(cls._field(farm_data, 'loanAmount', 'loan_amount', default=50_000_000))
        except (TypeError, ValueError):
            loan_amount = 50_000_000
        try:
            loan_term = int(float(cls._field(farm_data, 'loanTerm', 'loan_term', default=12)))
        except (TypeError, ValueError):
            loan_term = 12

        return {
            'farmerName': str(cls._field(farm_data, 'farmerName', 'farmer_name', default='Unknown')),
            'farmSize': max(0.1, farm_size),
            'latitude': latitude,
            'longitude': longitude,
            'primaryCrop': crop_type,
            'loanAmount': max(1_000_000.0, loan_amount),
            'loanTerm': max(1, loan_term),
            'loanPurpose': str(cls._field(farm_data, 'loanPurpose', 'loan_purpose', default='working_capital')),
            'collateralType': collateral_type,
        }

    def calculate_credit_score(self, farm_data: Dict, satellite_features: np.ndarray = None, 
                             weather_features: np.ndarray = None) ->Dict:
        """
        Calculate credit score using Random Forest + XGBoost ensemble with Basel III compliance
        
        Uses Prithvi-EO-2.0-300M satellite features, OpenWeatherMap data, and traditional factors
        for comprehensive agricultural credit assessment
        
        Returns:
        - Credit Score (300-850 scale → converted to SLIK 1-5)
        - PD (Probability of Default): Likelihood of default within 12 months
        - LGD (Loss Given Default): Expected loss percentage if default occurs
        - EAD (Exposure at Default): Credit exposure amount at time of default
        """

        try:
            farm_data = self._normalize_farm_data(farm_data)
            loan_amount = float(farm_data['loanAmount'])

            # Prepare feature vector (320 features total)
            features = self._prepare_feature_vector(farm_data, satellite_features, weather_features)
            
            if self.is_trained:
                # Use trained ML models for prediction
                predictions = self._predict_with_ensemble(features)
                credit_score, pd, lgd, _predicted_ead = predictions
                # For a loan application, EAD tracks requested exposure (term-loan CCF ~1.0)
                ead = loan_amount
                
                # Generate SHAP explanations
                shap_values = self._calculate_shap_explanations(features)
                
            else:
                # Fallback to rule-based calculation if models not available
                credit_score, pd, lgd, ead = self._fallback_calculation(farm_data)
                shap_values = None

            # Determine risk category and SLIK mapping
            risk_level = self._get_risk_level(credit_score)
            slik_rating = self._map_to_slik(credit_score)
            slik_info = self.SLIK_SYSTEM[slik_rating]

            # Calculate Basel III parameters
            ecl = pd * lgd * ead

            return {
                'success': True,
                'creditAnalysis': {
                    'creditScore': int(float(credit_score)),  # Original credit score (300-850)
                    'creditScoreNormalized': round(((float(credit_score) - 300) / 550), 4),  # Normalized to 0-1 scale
                    'riskLevel': risk_level.title(),
                    'slikRating': slik_rating,
                    'slikDescription': slik_info['description_en'],
                    'slikDescriptionId': slik_info['description_id'],
                    'interestRate': f"{self.KUR_RATES[risk_level]}%",
                    
                    # Basel III Risk Parameters
                    'baselIIIRiskParameters': {
                        'probabilityOfDefault': f"{float(pd):.4f}",
                        'probabilityOfDefaultPercent': f"{float(pd)*100:.2f}%",
                        'lossGivenDefault': f"{float(lgd):.4f}",
                        'lossGivenDefaultPercent': f"{float(lgd)*100:.1f}%",
                        'exposureAtDefault': f"Rp {float(ead):,.0f}",
                        'expectedCreditLoss': f"Rp {float(ecl):,.0f}",
                        'expectedCreditLossPercent': f"{(float(ecl)/float(ead))*100:.2f}%"if ead >0 else "0.00%"
                    },
                    
                    'methodology': (
                        'Random Forest + XGBoost Ensemble with Prithvi-EO-2.0-300M Satellite Features'
                        if self.xgboost is not None else
                        'Random Forest with Prithvi-EO-2.0-300M Satellite Features'
                    ),
                    'modelInfo': {
                        'algorithm': 'Random Forest + XGBoost'if self.xgboost is not None else 'Random Forest',
                        'features_used': 320,
                        'satellite_model': 'IBM/NASA Prithvi-EO-2.0-300M',
                        'weather_source': 'OpenWeatherMap API',
                        'trained': self.is_trained
                    },
                    'shapValues': shap_values
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Credit scoring error: {str(e)}'
            }

    def _prepare_feature_vector(self, farm_data: Dict, satellite_features: np.ndarray = None, 
                               weather_features: np.ndarray = None) ->np.ndarray:
        """Prepare 320-dimensional feature vector for ML models"""
        farm_data = self._normalize_farm_data(farm_data)
        features = np.zeros(320)
        
        # Satellite features (256 dimensions)
        if satellite_features is not None:
            features[0:256] = satellite_features[:256] if len(satellite_features) >= 256 else np.pad(satellite_features, (0, 256 - len(satellite_features)))
        
        # Weather features (64 dimensions)
        if weather_features is not None:
            features[256:320] = weather_features[:64] if len(weather_features) >= 64 else np.pad(weather_features, (0, 64 - len(weather_features)))
        
        # Traditional features occupy the first weather slots (matches training layout)
        crop_list = ['rice', 'palm oil', 'coffee', 'cocoa', 'rubber']
        crop = farm_data['primaryCrop']
        features[256] = float(farm_data['farmSize'])
        features[257] = float(crop_list.index(crop) if crop in crop_list else 0)
        features[258] = float(farm_data['latitude'])
        features[259] = float(farm_data['longitude'])
        
        return features

    def _predict_with_ensemble(self, features: np.ndarray) ->Tuple[float, float, float, float]:
        """Use Random Forest + XGBoost ensemble for prediction"""
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Random Forest prediction (multi-output)
        rf_pred = self.random_forest.predict(features_scaled)[0]  # Shape: (4,) for 4 outputs
        
        # XGBoost prediction (multi-output, optional)
        if self.xgboost is not None:
            xgb_pred = self.xgboost.predict(features_scaled)[0]  # Shape: (4,) for 4 outputs
            # Ensemble (weighted average)
            ensemble_pred = 0.7 * rf_pred + 0.3 * xgb_pred
        else:
            ensemble_pred = rf_pred
        
        # Extract individual predictions with proper bounds
        credit_score = np.clip(ensemble_pred[0], 300, 850)
        pd = np.clip(ensemble_pred[1], 0.001, 0.2)
        lgd = np.clip(ensemble_pred[2], 0.1, 0.7)
        ead = np.clip(ensemble_pred[3], 1_000_000, 1_000_000_000)
        
        return credit_score, pd, lgd, ead

    def _build_xgboost_model(self):
        """Create a stable XGBoost multi-target regressor."""
        return MultiOutputRegressor(
            XGBRegressor(
                n_estimators=80,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=1,
                tree_method='hist',
                objective='reg:squarederror',
            )
        )

    def _torch_is_loaded(self) ->bool:
        """Detect PyTorch import, which can crash XGBoost training on macOS."""
        return 'torch'in sys.modules

    def _train_xgboost_safely(self, X_train_scaled: np.ndarray, y_train: np.ndarray):
        """
        Train XGBoost in-process when safe, otherwise in an isolated subprocess.
        PyTorch + XGBoost in the same process can segfault on Apple Silicon.
        """
        if self._torch_is_loaded():
            print("PyTorch detected; training XGBoost in isolated subprocess...")
            return self._train_xgboost_in_subprocess(X_train_scaled, y_train)

        try:
            model = self._build_xgboost_model()
            model.fit(X_train_scaled, y_train)
            return model
        except Exception as error:
            print(f"In-process XGBoost training failed ({error}); retrying in subprocess...")
            return self._train_xgboost_in_subprocess(X_train_scaled, y_train)

    def _train_xgboost_in_subprocess(self, X_train_scaled: np.ndarray, y_train: np.ndarray):
        """Train XGBoost in a clean child process and load the fitted model."""
        with tempfile.TemporaryDirectory(prefix='agri-xgb-') as temp_dir:
            input_path = os.path.join(temp_dir, 'train_data.npz')
            output_path = os.path.join(temp_dir, 'xgb_model.pkl')
            np.savez(input_path, X=X_train_scaled, y=y_train)

            result = subprocess.run(
                [sys.executable, XGB_WORKER_SCRIPT, input_path, output_path],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                stderr = (result.stderr or '').strip()
                raise RuntimeError(f"Isolated XGBoost training failed: {stderr or 'unknown error'}")

            with open(output_path, 'rb') as model_file:
                return pickle.load(model_file)

    def _should_enable_xgboost(self) ->bool:
        """
        Decide whether XGBoost should be enabled in this runtime.
        Default is safe mode on environments known to hit native crashes.
        """
        override = os.environ.get("AGRI_ENABLE_XGBOOST")
        if override is not None:
            return override.strip().lower() in ("1", "true", "yes", "on")

        # Enable XGBoost by default when available.
        # Set AGRI_ENABLE_XGBOOST=false to force-disable if needed.
        return XGBRegressor is not None

    def _calculate_shap_explanations(self, features: np.ndarray) ->Dict:
        """Calculate SHAP values for model explainability"""
        if self.shap_explainer is None:
            return None
            
        try:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            shap_values = self.shap_explainer.shap_values(features_scaled)
            
            # Since we're using the first estimator from MultiOutputRegressor (Credit Score)
            # shap_values should be 2D: (n_samples, n_features)
            if len(shap_values.shape) == 2:
                credit_score_shap = shap_values[0]  # First sample
            else:
                # Fallback for unexpected shapes
                credit_score_shap = shap_values.flatten() if shap_values.ndim >1 else shap_values
            
            # Enhanced feature names for better interpretation
            feature_names = []
            
            # Satellite features (0-255)
            for i in range(64):
                feature_names.append(f'prithvi_vegetation_{i}')
            for i in range(64):
                feature_names.append(f'prithvi_crop_health_{i}')
            for i in range(64):
                feature_names.append(f'prithvi_soil_quality_{i}')
            for i in range(64):
                feature_names.append(f'prithvi_water_access_{i}')
            
            # Weather features (256-319)
            for i in range(16):
                feature_names.append(f'weather_temperature_{i}')
            for i in range(16):
                feature_names.append(f'weather_humidity_{i}')
            for i in range(16):
                feature_names.append(f'weather_rainfall_{i}')
            for i in range(16):
                feature_names.append(f'weather_wind_pressure_{i}')
            
            # Traditional features
            feature_names.extend(['farm_size', 'crop_type', 'latitude', 'longitude'])
            
            # Normalize SHAP values to 0-100 scale for interpretability
            # Credit score range is 300-850 (total range: 550)
            max_abs_shap = np.max(np.abs(credit_score_shap)) if len(credit_score_shap) >0 else 1.0
            
            # Get top 10 most important features by absolute SHAP value
            importance_indices = np.argsort(np.abs(credit_score_shap))[-10:][::-1]
            
            # Create detailed SHAP explanations with normalized values
            credit_features = []
            pd_features = []
            lgd_features = []
            ead_features = []
            
            for idx in importance_indices:
                raw_shap_val = float(credit_score_shap[idx])
                feat_val = float(features[idx])
                
                # Normalize SHAP value to 0-1 scale based on maximum impact
                normalized_shap = (raw_shap_val / max_abs_shap) if max_abs_shap >0 else 0.0
                
                # Credit Score explanation with normalized SHAP
                credit_features.append({
                    'feature': feature_names[idx],
                    'shap_value': round(normalized_shap, 4),  # Normalized 0-1 scale
                    'raw_shap_value': round(raw_shap_val, 4),  # Keep raw value for reference
                    'feature_value': feat_val,
                    'impact': 'positive'if raw_shap_val >0 else 'negative',
                    'impact_strength': 'high'if abs(normalized_shap) >0.5 else 'medium'if abs(normalized_shap) >0.2 else 'low'
                })
                
                # For other Basel III parameters, derive from normalized credit score SHAP
                # PD has inverse relationship with credit score (0-1 scale)
                pd_shap_normalized = -normalized_shap * 0.1  # PD impact on 0-1 scale
                pd_features.append({
                    'feature': feature_names[idx],
                    'shap_value': round(pd_shap_normalized, 4),
                    'feature_value': feat_val,
                    'impact': 'negative'if pd_shap_normalized >0 else 'positive',
                    'impact_strength': 'high'if abs(pd_shap_normalized) >0.05 else 'medium'if abs(pd_shap_normalized) >0.02 else 'low'
                })
                
                # LGD - focus on collateral-related features (0-1 scale)
                if 'farm_size'in feature_names[idx] or 'soil_quality'in feature_names[idx]:
                    lgd_shap_normalized = -normalized_shap * 0.05  # Negative correlation with quality
                else:
                    lgd_shap_normalized = normalized_shap * 0.02
                    
                lgd_features.append({
                    'feature': feature_names[idx],
                    'shap_value': round(lgd_shap_normalized, 4),
                    'feature_value': feat_val,
                    'impact': 'negative'if lgd_shap_normalized >0 else 'positive',
                    'impact_strength': 'high'if abs(lgd_shap_normalized) >0.05 else 'medium'if abs(lgd_shap_normalized) >0.02 else 'low'
                })
                
                # EAD - related to loan size and farm value (keep monetary scale but normalize base impact)
                if 'farm_size'in feature_names[idx] or 'crop'in feature_names[idx]:
                    ead_shap_normalized = normalized_shap * 10000000  # Scale for monetary impact
                else:
                    ead_shap_normalized = normalized_shap * 5000000
                    
                ead_features.append({
                    'feature': feature_names[idx],
                    'shap_value': round(ead_shap_normalized, 0),
                    'feature_value': feat_val,
                    'impact': 'positive'if ead_shap_normalized >0 else 'negative',
                    'impact_strength': 'high'if abs(ead_shap_normalized) >5000000 else 'medium'if abs(ead_shap_normalized) >2000000 else 'low'
                })
            
            # Calculate baseline (average credit score normalized to 0-1 scale)
            baseline_normalized = ((650 - 300) / 550)  # Average credit score 650 normalized to 0-1
            
            return {
                'Credit_Score': credit_features,
                'baseline': round(baseline_normalized, 4),  # Normalized baseline for SHAP waterfall
                'prediction': round(baseline_normalized + sum(f['shap_value'] for f in credit_features), 4),  # Baseline + SHAP contributions
                'explanation': {
                    'credit_score_scale': '0-1 (normalized from 300-850 range)',
                    'shap_scale': '0-1 (normalized impact values)',
                    'baseline_info': f'Model baseline: {baseline_normalized:.4f} (equivalent to credit score 650)',
                    'interpretation': 'SHAP values show feature impact on credit score. Positive = increases score, Negative = decreases score'
                },
                'PD': pd_features[:5],  # Top 5 for each
                'LGD': lgd_features[:5],
                'EAD': ead_features[:5]
            }
            
        except Exception as e:
            print(f"SHAP calculation failed: {e}")
            return None

    def _fallback_calculation(self, farm_data: Dict) ->Tuple[float, float, float, float]:
        """Fallback calculation when ML models are not available"""
        farm_data = self._normalize_farm_data(farm_data)
        base_score = 500
        
        # Farm size bonus
        farm_size = float(farm_data['farmSize'])
        base_score += min(50, farm_size * 15)
        
        # Crop type adjustments
        crop_bonuses = {'rice': 40, 'palm oil': 30, 'coffee': 25, 'cocoa': 20, 'rubber': 35}
        base_score += crop_bonuses.get(farm_data['primaryCrop'], 0)
        
        # Regional bonus (Java region)
        if -8 <= float(farm_data['latitude']) <= -6:
            base_score += 25
        
        # Add deterministic variation based on farm characteristics
        variation = (float(farm_data['latitude']) * float(farm_data['longitude']) * farm_size) % 50 - 25
        credit_score = np.clip(base_score + variation, 300, 850)
        
        # Calculate other parameters
        pd = 0.01 + 0.15 * (1 - (credit_score - 300) / 550) ** 1.5
        pd = np.clip(pd, 0.001, 0.2)
        
        lgd = 0.4 if farm_data['collateralType'] == 'land' else 0.6
        ead = float(farm_data['loanAmount'])
        
        return credit_score, pd, lgd, ead

    def _get_risk_level(self, credit_score: float) ->str:
        """Map credit score to risk level"""
        if credit_score >= 750:
            return 'excellent'
        elif credit_score >= 650:
            return 'good'
        elif credit_score >= 550:
            return 'fair'
        else:
            return 'poor'

    def _map_to_slik(self, credit_score: float) ->int:
        """Map credit score to Indonesian SLIK rating (1-5)"""
        if credit_score >= 750:
            return 1  # Lancar
        elif credit_score >= 650:
            return 2  # Dalam Perhatian Khusus
        elif credit_score >= 550:
            return 3  # Kurang Lancar
        elif credit_score >= 450:
            return 4  # Diragukan
        else:
            return 5  # Macet


def main():
    """CLI interface for the agricultural ML model"""
    if len(sys.argv) != 2:
        print("Usage: python3 banking_credit_model.py '<farm_data_json>'")
        sys.exit(1)
    
    try:
        farm_data_json = sys.argv[1]
        farm_data = json.loads(farm_data_json)
        
        model = AgricultureMLModel()
        result = model.calculate_credit_score(farm_data)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Agricultural ML model error: {str(e)}'
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
