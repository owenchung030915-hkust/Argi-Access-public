// Shared JavaScript functions for both mobile and desktop interfaces



// Common API endpoint
const API_BASE = '/api';

// Common demo data
const DEMO_LOCATIONS = {
    siti: {
        name: 'Ibu Siti Nurhasanah',
        lat: -6.7749,
        lon: 107.1389,
        size: 1.5,
        crop: 'rice'
    },
    budi: {
        name: 'Pak Budi Santoso',
        lat: -2.5489,
        lon: 99.6401,
        size: 3.2,
        crop: 'palm oil'
    },
    ratna: {
        name: 'Ibu Ratna Sari',
        lat: -7.6145,
        lon: 109.3425,
        size: 0.8,
        crop: 'coffee'
    }
};

// Common validation functions
function validateCoordinates(lat, lon) {
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lon);

    if (isNaN(latitude) || isNaN(longitude)) {
        return { valid: false, message: 'Coordinates must be numbers' };
    }

    if (Math.abs(latitude) > 90) {
        return { valid: false, message: 'Latitude must be between -90 and 90' };
    }

    if (Math.abs(longitude) > 180) {
        return { valid: false, message: 'Longitude must be between -180 and 180' };
    }

    return { valid: true };
}

function validateFarmSize(size) {
    const farmSize = parseFloat(size);

    if (isNaN(farmSize) || farmSize <= 0) {
        return { valid: false, message: 'Farm size must be a positive number' };
    }

    if (farmSize > 1000) {
        return { valid: false, message: 'Farm size seems unusually large (>1000 hectares)' };
    }

    return { valid: true };
}

function validateFarmerName(name) {
    if (!name || name.trim().length < 2) {
        return { valid: false, message: 'Please enter a valid farmer name' };
    }

    return { valid: true };
}

// Common API functions
async function analyzeCredit(farmData) {
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(farmData)
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Credit analysis error:', error);
        throw error;
    }
}

// Common utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

function getCreditRating(score) {
    if (score >= 750) return 'Sangat Baik';
    if (score >= 650) return 'Baik - Layak Kredit';
    if (score >= 550) return 'Cukup';
    if (score >= 450) return 'Perlu Ditingkatkan';
    return 'Kurang Baik';
}

function getRiskLevel(score) {
    if (score >= 750) return 'excellent';
    if (score >= 650) return 'good';
    if (score >= 550) return 'fair';
    if (score >= 450) return 'poor';
    return 'high';
}

// Common event handlers
function handleError(error, userMessage = 'Terjadi kesalahan. Mohon coba lagi.') {
    console.error('Application error:', error);

    // Show user-friendly error message
    if (typeof showNotification === 'function') {
        showNotification(userMessage, 'error');
    } else {
        alert(userMessage);
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Geolocation helper
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation not supported'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            position => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                });
            },
            error => {
                let message = 'Unable to get location';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        message = 'Location access denied';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = 'Location unavailable';
                        break;
                    case error.TIMEOUT:
                        message = 'Location request timeout';
                        break;
                }
                reject(new Error(message));
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 5 minutes
            }
        );
    });
}

// Local storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(`agri-access-${key}`, JSON.stringify(data));
        return true;
    } catch (error) {
        console.warn('Failed to save to localStorage:', error);
        return false;
    }
}

function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(`agri-access-${key}`);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.warn('Failed to load from localStorage:', error);
        return null;
    }
}

function clearLocalStorage(key) {
    try {
        localStorage.removeItem(`agri-access-${key}`);
        return true;
    } catch (error) {
        console.warn('Failed to clear localStorage:', error);
        return false;
    }
}

// Interface switching functions removed - mobile view deprecated

// Demo location loader
function loadDemoLocation(location) {
    const demo = DEMO_LOCATIONS[location];
    if (!demo) {
        console.warn('Unknown demo location:', location);
        return;
    }

    // Update form fields
    const farmerNameField = document.getElementById('farmerName');
    const latitudeField = document.getElementById('latitude');
    const longitudeField = document.getElementById('longitude');
    const farmSizeField = document.getElementById('farmSize');
    const primaryCropField = document.getElementById('primaryCrop');

    if (farmerNameField) farmerNameField.value = demo.name;
    if (latitudeField) latitudeField.value = demo.lat;
    if (longitudeField) longitudeField.value = demo.lon;
    if (farmSizeField) farmSizeField.value = demo.size;
    if (primaryCropField) primaryCropField.value = demo.crop;

    // Update map if it exists
    if (typeof window.map !== 'undefined' && window.map) {
        window.map.setView([demo.lat, demo.lon], 12);

        // Update marker if it exists
        if (typeof window.marker !== 'undefined' && window.marker) {
            window.marker.setLatLng([demo.lat, demo.lon]);
        }
    }

    console.log(`Loaded demo location: ${demo.name}`);
}

// Export functions for module systems (if available)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DEMO_LOCATIONS,
        validateCoordinates,
        validateFarmSize,
        validateFarmerName,
        analyzeCredit,
        formatCurrency,
        formatNumber,
        getCreditRating,
        getRiskLevel,
        handleError,
        debounce,
        getCurrentLocation,
        saveToLocalStorage,
        loadFromLocalStorage,
        clearLocalStorage,
        loadDemoLocation
    };
}