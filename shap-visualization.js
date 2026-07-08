/**
 * SHAP Visualization Component
 * 
 * Interactive explainable AI visualization for Basel III credit scoring
 * 
 * Features:
 * - Waterfall chart visualization
 * - Multi-output support (PD, LGD, EAD, Credit Score)
 * - Feature importance analysis by category
 * - Interactive tooltips and explanations
 * 
 * @author Agri-Access Platform
 * @version 1.0.0
 */

class SHAPVisualization {
    /**
     * Initialize SHAP visualization component
     * @param {string} containerId - DOM element ID for the container
     * @param {Object} options - Configuration options
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container element with ID '${containerId}' not found`);
        }

        // Default configuration
        this.options = {
            chartType: 'waterfall', // waterfall only
            maxFeatures: 10,
            colors: {
                positive: '#4CAF50',
                negative: '#FF4D4F',
                neutral: '#E0E0E0',
                text: '#333',
                background: '#FAFAFA'
            },
            responsive: true,
            animationDuration: 800,
            showValues: true,
            showTooltips: true,
            ...options
        };
        
        // Component state
        this.data = null;
        this.currentOutput = 'Credit_Score';
        this.chartContainer = null;
        this.tooltip = null;
        
        this.init();
    }
    
    init() {
        this.createContainer();
        this.createControls();
        this.createChartContainer();
    }
    
    createContainer() {
        this.container.className = 'shap-visualization-container';
        this.container.innerHTML = '';
        
        // Add CSS styles
        const style = document.createElement('style');
        style.textContent = `
            .shap-visualization-container {
                font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
                background: #FAFAFA;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .shap-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #E0E0E0;
            }
            
            .shap-title {
                font-size: 1.3em;
                font-weight: 600;
                color: #333;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .shap-controls {
                display: flex;
                gap: 10px;
                align-items: center;
            }
            
            .shap-control-button {
                padding: 6px 12px;
                border: 1px solid #DDD;
                background: white;
                color: #666;
                font-size: 12px;
                font-weight: 500;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .shap-control-button:hover {
                background: #F5F5F5;
                border-color: #BBB;
            }
            
            .shap-control-button.active {
                background: #2196F3;
                color: white;
                border-color: #2196F3;
            }
            
            .shap-output-selector {
                padding: 6px 10px;
                border: 1px solid #DDD;
                border-radius: 4px;
                font-size: 12px;
                background: white;
                color: #666;
            }
            
            .shap-chart-container {
                position: relative;
                min-height: 300px;
            }
            
            .shap-waterfall {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .shap-feature-row {
                display: flex;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #F0F0F0;
            }
            
            .shap-feature-row:last-child {
                border-bottom: none;
            }
            
            .shap-feature-name {
                flex: 0 0 200px;
                font-size: 13px;
                font-weight: 500;
                color: #555;
                padding-right: 15px;
            }
            
            .shap-feature-bar-container {
                flex: 1;
                position: relative;
                height: 20px;
                background: #F5F5F5;
                border-radius: 10px;
                overflow: hidden;
            }
            
            .shap-feature-bar {
                height: 100%;
                transition: width 0.8s ease;
                border-radius: 10px;
                position: relative;
            }
            
            .shap-feature-value {
                flex: 0 0 80px;
                text-align: right;
                font-size: 12px;
                font-weight: 600;
                padding-left: 10px;
            }
            
            .shap-positive {
                background: linear-gradient(90deg, #4CAF50, #66BB6A);
                color: white;
            }
            
            .shap-negative {
                background: linear-gradient(90deg, #FF4D4F, #FF7A7A);
                color: white;
            }
            
            .shap-baseline {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                margin: 15px 0;
                border-top: 2px solid #E0E0E0;
                border-bottom: 2px solid #E0E0E0;
                background: #F8F9FA;
                border-radius: 4px;
                padding: 15px;
            }
            
            .shap-baseline-label {
                font-weight: 600;
                color: #333;
            }
            
            .shap-baseline-value {
                font-weight: 700;
                font-size: 1.1em;
                color: #2196F3;
            }
            
            .shap-prediction {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: linear-gradient(135deg, #2196F3, #1976D2);
                color: white;
                border-radius: 6px;
                margin-top: 15px;
            }
            
            .shap-prediction-label {
                font-weight: 600;
            }
            
            .shap-prediction-value {
                font-weight: 700;
                font-size: 1.3em;
            }
            
            .shap-tooltip {
                position: absolute;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                pointer-events: none;
                z-index: 1000;
                opacity: 0;
                transition: opacity 0.3s ease;
                max-width: 200px;
                white-space: pre-wrap;
            }
            
            .shap-explanation {
                margin-top: 20px;
                padding: 15px;
                background: white;
                border-radius: 6px;
                border-left: 4px solid #2196F3;
            }
            
            .shap-explanation h4 {
                margin: 0 0 10px 0;
                color: #333;
                font-size: 14px;
                font-weight: 600;
            }
            
            .shap-explanation p {
                margin: 0;
                font-size: 13px;
                line-height: 1.5;
                color: #666;
            }
            
            @media (max-width: 768px) {
                .shap-visualization-container {
                    padding: 15px;
                }
                
                .shap-header {
                    flex-direction: column;
                    gap: 15px;
                    align-items: stretch;
                }
                
                .shap-controls {
                    justify-content: center;
                    flex-wrap: wrap;
                }
                
                .shap-feature-name {
                    flex: 0 0 150px;
                    font-size: 12px;
                }
                
                .shap-feature-value {
                    flex: 0 0 60px;
                    font-size: 11px;
                }
            }
        `;
        
        if (!document.getElementById('shap-visualization-styles')) {
            style.id = 'shap-visualization-styles';
            document.head.appendChild(style);
        }
    }
    
    createControls() {
        const header = document.createElement('div');
        header.className = 'shap-header';
        
        const title = document.createElement('h3');
        title.className = 'shap-title';
        title.innerHTML = ' <span>Feature Importance Analysis</span>';
        
        const controls = document.createElement('div');
        controls.className = 'shap-controls';
        
        // Waterfall chart only (removed bar chart and force plot options)
        
        // Output selector
        const selector = document.createElement('select');
        selector.className = 'shap-output-selector';
        selector.onchange = (e) =>this.setOutput(e.target.value);
        
        const outputs = ['PD', 'LGD', 'EAD', 'Credit_Score'];
        outputs.forEach(output => {
            const option = document.createElement('option');
            option.value = output;
            option.textContent = output;
            selector.appendChild(option);
        });
        
        controls.appendChild(selector);
        
        header.appendChild(title);
        header.appendChild(controls);
        this.container.appendChild(header);
    }
    
    createChartContainer() {
        const chartContainer = document.createElement('div');
        chartContainer.className = 'shap-chart-container';
        chartContainer.id = `${this.container.id}-chart`;
        
        this.container.appendChild(chartContainer);
        this.chartContainer = chartContainer;
        
        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'shap-tooltip';
        this.container.appendChild(tooltip);
        this.tooltip = tooltip;
    }
    
    setData(shapData, output = 'Credit_Score') {
        // Set SHAP data for visualization
        this.data = shapData;
        this.currentOutput = output;
        this.render();
    }
    
    setChartType(chartType) {
        // Change chart type
        this.options.chartType = chartType;
        
        // Update button states
        this.container.querySelectorAll('.shap-control-button').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        this.render();
    }
    
    setOutput(output) {
        // Change output variable
        this.currentOutput = output;
        this.render();
    }
    
    render() {
        // Render the current visualization
        if (!this.data || !this.currentOutput) {
            this.chartContainer.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No data available</p>';
            return;
        }
        
        const outputData = this.data[this.currentOutput];
        if (!outputData || !outputData.length) {
            this.chartContainer.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No data for selected output</p>';
            return;
        }
        
        // Always render waterfall chart
        this.renderWaterfall(outputData);
    }
    
    renderWaterfall(data) {
        // Render waterfall chart showing feature contributions
        const container = this.chartContainer;
        container.innerHTML = '';
        
        const waterfallDiv = document.createElement('div');
        waterfallDiv.className = 'shap-waterfall';
        
        // Sort features by absolute SHAP value
        const sortedFeatures = [...data]
            .slice(0, this.options.maxFeatures)
            .sort((a, b) =>Math.abs(b.shap_value) - Math.abs(a.shap_value));
        
        // Calculate max absolute value for scaling
        const maxAbsValue = Math.max(...sortedFeatures.map(f =>Math.abs(f.shap_value)));
        
        // Add baseline
        const baseline = document.createElement('div');
        baseline.className = 'shap-baseline';
        baseline.innerHTML = `
            <span class="shap-baseline-label">Model Baseline</span>
            <span class="shap-baseline-value">0.00</span>
        `;
        waterfallDiv.appendChild(baseline);
        
        // Add feature rows
        sortedFeatures.forEach((feature, index) => {
            const row = document.createElement('div');
            row.className = 'shap-feature-row';
            
            const featureName = document.createElement('div');
            featureName.className = 'shap-feature-name';
            featureName.textContent = this.formatFeatureName(feature.feature);
            
            const barContainer = document.createElement('div');
            barContainer.className = 'shap-feature-bar-container';
            
            const bar = document.createElement('div');
            bar.className = `shap-feature-bar ${feature.shap_value >= 0 ? 'shap-positive' : 'shap-negative'}`;
            
            const width = Math.abs(feature.shap_value) / maxAbsValue * 100;
            bar.style.width = '0%'; // Start at 0 for animation
            
            // Animate after a delay
            setTimeout(() => {
                bar.style.width = `${width}%`;
            }, index * 100);
            
            const value = document.createElement('div');
            value.className = 'shap-feature-value';
            value.style.color = feature.shap_value >= 0 ? '#4CAF50' : '#FF4D4F';
            value.textContent = feature.shap_value >= 0 ? `+${feature.shap_value.toFixed(3)}` : feature.shap_value.toFixed(3);
            
            // Add hover effects
            row.addEventListener('mouseenter', (e) => {
                this.showTooltip(e, feature);
                bar.style.filter = 'brightness(1.1)';
            });
            
            row.addEventListener('mouseleave', () => {
                this.hideTooltip();
                bar.style.filter = 'none';
            });
            
            row.addEventListener('mousemove', (e) => {
                this.updateTooltipPosition(e);
            });
            
            barContainer.appendChild(bar);
            row.appendChild(featureName);
            row.appendChild(barContainer);
            row.appendChild(value);
            
            waterfallDiv.appendChild(row);
        });
        
        // Add prediction result
        const prediction = document.createElement('div');
        prediction.className = 'shap-prediction';
        
        const totalContribution = sortedFeatures.reduce((sum, f) =>sum + f.shap_value, 0);
        prediction.innerHTML = `
            <span class="shap-prediction-label">Model Prediction</span>
            <span class="shap-prediction-value">${(totalContribution).toFixed(3)}</span>
        `;
        waterfallDiv.appendChild(prediction);
        
        container.appendChild(waterfallDiv);
        
        // Add explanation
        this.addExplanation(container, this.currentOutput, sortedFeatures.slice(0, 3));
    }
    
    // Removed bar chart and force plot methods
    
    formatFeatureName(feature) {
        // Format feature names for display
        const nameMap = {
            'farm_size': 'Farm Size',
            'loan_amount_millions': 'Loan Amount',
            'loan_term': 'Loan Term',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'is_rice': 'Rice Crop',
            'has_land_collateral': 'Land Collateral',
            'farmer_age': 'Farmer Age',
            'experience_years': 'Experience Years',
            'weather_temperature': 'Temperature',
            'weather_humidity': 'Humidity',
            'weather_rainfall': 'Rainfall',
            'satellite_ndvi': 'NDVI',
            'satellite_evi': 'EVI'
        };
        
        return nameMap[feature] || feature.replace(/_/g, ' ').replace(/\b\w/g, l =>l.toUpperCase());
    }
    
    showTooltip(event, feature) {
        // Show tooltip with feature details
        const tooltip = this.tooltip;
        tooltip.innerHTML = `
            <strong>${this.formatFeatureName(feature.feature)}</strong>SHAP Value: ${feature.shap_value.toFixed(4)}
            Feature Value: ${feature.feature_value.toFixed(3)}
            Impact: ${feature.impact}
        `;
        tooltip.style.opacity = '1';
        this.updateTooltipPosition(event);
    }
    
    hideTooltip() {
        // Hide tooltip
        this.tooltip.style.opacity = '0';
    }
    
    updateTooltipPosition(event) {
        // Update tooltip position
        const rect = this.container.getBoundingClientRect();
        this.tooltip.style.left = (event.clientX - rect.left + 10) + 'px';
        this.tooltip.style.top = (event.clientY - rect.top - 30) + 'px';
    }
    
    addExplanation(container, output, topFeatures) {
        // Add explanation text
        const explanation = document.createElement('div');
        explanation.className = 'shap-explanation';
        
        const outputLabels = {
            'PD': 'Probability of Default',
            'LGD': 'Loss Given Default', 
            'EAD': 'Exposure at Default',
            'Credit_Score': 'Credit Score'
        };
        
        const outputLabel = outputLabels[output] || output;
        
        const topFeaturesList = topFeatures
            .map(f => `${this.formatFeatureName(f.feature)} (${f.shap_value >= 0 ? '+' : ''}${f.shap_value.toFixed(3)})`)
            .join(', ');
        
        explanation.innerHTML = `
            <h4> ${outputLabel} Analysis</h4>
            <p>This visualization shows how each feature contributes to the ${outputLabel.toLowerCase()} prediction. 
            Positive values (green) increase the prediction, while negative values (red) decrease it.</p>
            <p><strong>Top contributing features:</strong> ${topFeaturesList}</p>
        `;
        
        container.appendChild(explanation);
    }
    
    // Public API methods
    updateData(shapData, output = null) {
        // Update visualization with new data
        this.setData(shapData, output || this.currentOutput || 'Credit_Score');
    }
    
    exportImage() {
        // Export visualization as image
        // Implementation for exporting as PNG/SVG
        console.log('Export functionality to be implemented');
    }
    
    getInsights() {
        // Get key insights from current visualization
        if (!this.data || !this.currentOutput) return null;
        
        const outputData = this.data[this.currentOutput];
        if (!outputData || !outputData.length) return null;
        
        const topPositive = outputData
            .filter(f =>f.shap_value >0)
            .sort((a, b) =>b.shap_value - a.shap_value)
            .slice(0, 3);
            
        const topNegative = outputData
            .filter(f =>f.shap_value < 0)
            .sort((a, b) =>a.shap_value - b.shap_value)
            .slice(0, 3);
        
        return {
            output: this.currentOutput,
            top_positive_features: topPositive,
            top_negative_features: topNegative,
            total_features: outputData.length
        };
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SHAPVisualization;
}

// Global assignment for direct script inclusion
window.SHAPVisualization = SHAPVisualization;