/**
 * Credit Score Arc Visualization Component
 * 
 * Features:
 * - Semicircular arc with SLIK-compatible score segments
 * - Smooth animations and responsive design
 * - Indonesian banking score categories
 * - Interactive tooltips and accessibility
 * 
 * @author Agri-Access Platform
 * @version 1.0.0
 */

class CreditScoreArc {
    /**
     * Initialize the credit score arc component
     * @param {string} containerId - DOM element ID to render the component
     * @param {Object} options - Configuration options
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container element with ID '${containerId}' not found`);
        }

        // Default configuration with SLIK-compatible English banking categories (1-5 scale)
        this.options = {
            radius: 150,
            strokeWidth: 15,
            scoreRange: { min: 1, max: 5 },
            segments: [
                { name: 'Poor', min: 1, max: 1, color: '#FF4D4F', percentage: 20 },
                { name: 'Fair', min: 2, max: 2, color: '#FF9800', percentage: 20 },
                { name: 'Good', min: 3, max: 3, color: '#FFC107', percentage: 20 },
                { name: 'Very Good', min: 4, max: 4, color: '#8BC34A', percentage: 20 },
                { name: 'Excellent', min: 5, max: 5, color: '#4CAF50', percentage: 20 }
            ],
            backgroundColor: '#E0E0E0',
            animationDuration: 1000,
            responsive: true,
            ...options
        };
        
        // Component state
        this.currentScore = 0;
        this.svg = null;
        this.scoreText = null;
        this.statusText = null;
        this.pointer = null;
        
        this.init();
    }
    
    init() {
        this.createContainer();
        this.createSVG();
        this.createSegments();
        this.createPointer();
        this.createScoreDisplay();
        this.setupResponsive();
    }
    
    createContainer() {
        this.container.className = 'credit-score-arc-container';
        this.container.innerHTML = '';
        
        // Add CSS styles
        const style = document.createElement('style');
        style.textContent = `
            .credit-score-arc-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 20px;
            }
            
            .credit-score-arc-svg {
                overflow: visible;
            }
            
            .credit-score-display {
                position: absolute;
                bottom: -40%;
                left: 50%;
                transform: translateX(-50%);
                text-align: center;
                pointer-events: none;
                background: none;
                border: none;
                padding: 40px 0 40px 0;
                margin-bottom: 30px;
                box-shadow: none;
            }
            
            .credit-score-number {
                font-size: 2.5em;
                font-weight: 700;
                color: #333;
                line-height: 1;
                margin-bottom: 5px;
            }
            
            .credit-score-status {
                font-size: 1em;
                font-weight: 500;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .arc-segment {
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .arc-segment:hover {
                filter: brightness(1.1);
                stroke-width: 18;
            }
            
            .arc-pointer {
                transition: all 1s cubic-bezier(0.4, 0, 0.2, 1);
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            }
            
            .arc-labels {
                font-size: 12px;
                font-weight: 600;
                fill: #666;
                text-anchor: middle;
                pointer-events: none;
            }
            
            .segment-tooltip {
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
            }
            
            @media (max-width: 768px) {
                .credit-score-arc-container {
                    padding: 15px;
                }
                
                .credit-score-number {
                    font-size: 2em;
                }
                
                .credit-score-status {
                    font-size: 0.9em;
                }
            }
            
            @media (max-width: 480px) {
                .credit-score-number {
                    font-size: 1.8em;
                }
                
                .credit-score-status {
                    font-size: 0.8em;
                }
            }
        `;
        
        if (!document.getElementById('credit-score-arc-styles')) {
            style.id = 'credit-score-arc-styles';
            document.head.appendChild(style);
        }
    }
    
    createSVG() {
        const size = this.options.radius * 2 + 40;
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', size);
        this.svg.setAttribute('height', size * 0.6);
        this.svg.setAttribute('viewBox', `0 0 ${size} ${size * 0.6}`);
        this.svg.setAttribute('class', 'credit-score-arc-svg');
        
        this.container.appendChild(this.svg);
    }
    
    createSegments() {
        const centerX = this.svg.getAttribute('width') / 2;
        const centerY = this.options.radius + 20;
        const radius = this.options.radius;
        
        // Create background arc (rotated: start from bottom, go clockwise)
        const backgroundArc = this.createArcPath(centerX, centerY, radius, 270, 90);
        const backgroundPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        backgroundPath.setAttribute('d', backgroundArc);
        backgroundPath.setAttribute('fill', 'none');
        backgroundPath.setAttribute('stroke', this.options.backgroundColor);
        backgroundPath.setAttribute('stroke-width', this.options.strokeWidth);
        backgroundPath.setAttribute('stroke-linecap', 'round');
        this.svg.appendChild(backgroundPath);
        
        // Create colored segments (starting from 270 degrees, going clockwise)
        let currentAngle = 270;
        
        this.options.segments.forEach((segment, index) => {
            const segmentAngle = (segment.percentage / 100) * 180;
            
            const segmentArc = this.createArcPath(centerX, centerY, radius, currentAngle, currentAngle + segmentAngle);
            const segmentPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            segmentPath.setAttribute('d', segmentArc);
            segmentPath.setAttribute('fill', 'none');
            segmentPath.setAttribute('stroke', segment.color);
            segmentPath.setAttribute('stroke-width', this.options.strokeWidth);
            segmentPath.setAttribute('stroke-linecap', 'round');
            segmentPath.setAttribute('class', 'arc-segment');
            segmentPath.dataset.segment = segment.name;
            segmentPath.dataset.range = `${segment.min}-${segment.max}`;
            
            // Add hover effects
            this.addSegmentInteractions(segmentPath, segment);
            
            this.svg.appendChild(segmentPath);
            
            // Add segment labels
            const labelAngle = currentAngle + segmentAngle / 2;
            const labelRadius = radius + 35;
            const labelX = centerX + labelRadius * Math.cos((labelAngle - 90) * Math.PI / 180);
            const labelY = centerY + labelRadius * Math.sin((labelAngle - 90) * Math.PI / 180);
            
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', labelX);
            label.setAttribute('y', labelY);
            label.setAttribute('class', 'arc-labels');
            label.style.fill = segment.color;
            label.textContent = segment.name;
            this.svg.appendChild(label);
            
            currentAngle += segmentAngle;
        });
    }
    
    createPointer() {
        const centerX = this.svg.getAttribute('width') / 2;
        const centerY = this.options.radius + 20;
        const radius = this.options.radius;
        
        // Create pointer group
        const pointerGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        pointerGroup.setAttribute('class', 'arc-pointer');
        
        // Pointer line
        const pointerLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        pointerLine.setAttribute('x1', centerX);
        pointerLine.setAttribute('y1', centerY);
        pointerLine.setAttribute('x2', centerX);
        pointerLine.setAttribute('y2', centerY - radius + 10);
        pointerLine.setAttribute('stroke', '#333');
        pointerLine.setAttribute('stroke-width', 3);
        pointerLine.setAttribute('stroke-linecap', 'round');
        
        // Pointer circle (center dot)
        const pointerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        pointerCircle.setAttribute('cx', centerX);
        pointerCircle.setAttribute('cy', centerY);
        pointerCircle.setAttribute('r', 6);
        pointerCircle.setAttribute('fill', '#333');
        
        // Pointer tip (triangle)
        const pointerTip = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        const tipX = centerX;
        const tipY = centerY - radius + 10;
        pointerTip.setAttribute('points', `${tipX},${tipY} ${tipX-5},${tipY+10} ${tipX+5},${tipY+10}`);
        pointerTip.setAttribute('fill', '#333');
        
        pointerGroup.appendChild(pointerLine);
        pointerGroup.appendChild(pointerCircle);
        pointerGroup.appendChild(pointerTip);
        
        this.pointer = pointerGroup;
        this.svg.appendChild(pointerGroup);
    }
    
    createScoreDisplay() {
        const scoreDisplay = document.createElement('div');
        scoreDisplay.className = 'credit-score-display';
        
        this.scoreText = document.createElement('div');
        this.scoreText.className = 'credit-score-number';
        this.scoreText.textContent = '---';
        
        this.statusText = document.createElement('div');
        this.statusText.className = 'credit-score-status';
        this.statusText.textContent = 'Credit Score';
        
        scoreDisplay.appendChild(this.scoreText);
        scoreDisplay.appendChild(this.statusText);
        
        this.container.appendChild(scoreDisplay);
    }
    
    createArcPath(centerX, centerY, radius, startAngle, endAngle) {
        const start = this.polarToCartesian(centerX, centerY, radius, endAngle);
        const end = this.polarToCartesian(centerX, centerY, radius, startAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
        
        return [
            "M", start.x, start.y,
            "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y
        ].join(" ");
    }
    
    polarToCartesian(centerX, centerY, radius, angleInDegrees) {
        const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
        return {
            x: centerX + (radius * Math.cos(angleInRadians)),
            y: centerY + (radius * Math.sin(angleInRadians))
        };
    }
    
    addSegmentInteractions(segmentPath, segment) {
        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'segment-tooltip';
        tooltip.innerHTML = `<strong>${segment.name}</strong><br>${segment.min}–${segment.max}`;
        this.container.appendChild(tooltip);
        
        segmentPath.addEventListener('mouseenter', (e) => {
            tooltip.style.opacity = '1';
            segmentPath.style.filter = 'brightness(1.1) drop-shadow(0 0 8px rgba(0,0,0,0.3))';
        });
        
        segmentPath.addEventListener('mouseleave', (e) => {
            tooltip.style.opacity = '0';
            segmentPath.style.filter = 'none';
        });
        
        segmentPath.addEventListener('mousemove', (e) => {
            const rect = this.container.getBoundingClientRect();
            tooltip.style.left = (e.clientX - rect.left + 10) + 'px';
            tooltip.style.top = (e.clientY - rect.top - 30) + 'px';
        });
    }
    
    updateScore(score, animated = true) {
        if (score < this.options.scoreRange.min || score > this.options.scoreRange.max) {
            console.warn(`Score ${score} is outside valid range ${this.options.scoreRange.min}-${this.options.scoreRange.max}`);
            return;
        }
        
        this.currentScore = score;
        
        // Update score text as integer for SLIK scale
        this.scoreText.textContent = Math.round(score).toString();
        
        // Update status text based on segment
        const segment = this.getSegmentForScore(score);
        this.statusText.textContent = segment.name;
        this.statusText.style.color = segment.color;
        
        // Update pointer position
        const angle = this.scoreToAngle(score);
        const centerX = this.svg.getAttribute('width') / 2;
        const centerY = this.options.radius + 20;
        
        if (animated) {
            this.animatePointer(angle, centerX, centerY);
        } else {
            this.setPointerPosition(angle, centerX, centerY);
        }
    }
    
    scoreToAngle(score) {
        const range = this.options.scoreRange.max - this.options.scoreRange.min;
        const normalized = (score - this.options.scoreRange.min) / range;
        return 270 + (normalized * 180); // Start from 270 degrees (bottom)
    }
    
    getSegmentForScore(score) {
        return this.options.segments.find(segment => 
            score >= segment.min && score <= segment.max
        ) || this.options.segments[0];
    }
    
    animatePointer(targetAngle, centerX, centerY) {
        const startTime = performance.now();
        const duration = this.options.animationDuration;
        const currentAngle = this.getCurrentPointerAngle() || 0;
        const angleChange = targetAngle - currentAngle;
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (cubic-bezier)
            const easedProgress = progress * progress * (3 - 2 * progress);
            
            const angle = currentAngle + (angleChange * easedProgress);
            this.setPointerPosition(angle, centerX, centerY);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    setPointerPosition(angle, centerX, centerY) {
        const radius = this.options.radius;
        const endPoint = this.polarToCartesian(centerX, centerY, radius - 10, angle);
        
        // Update pointer line
        const pointerLine = this.pointer.querySelector('line');
        pointerLine.setAttribute('x2', endPoint.x);
        pointerLine.setAttribute('y2', endPoint.y);
        
        // Update pointer tip
        const pointerTip = this.pointer.querySelector('polygon');
        const tipPoints = [
            `${endPoint.x},${endPoint.y}`,
            `${endPoint.x - 5 * Math.cos((angle - 60) * Math.PI / 180)},${endPoint.y - 5 * Math.sin((angle - 60) * Math.PI / 180)}`,
            `${endPoint.x - 5 * Math.cos((angle + 60) * Math.PI / 180)},${endPoint.y - 5 * Math.sin((angle + 60) * Math.PI / 180)}`
        ].join(' ');
        pointerTip.setAttribute('points', tipPoints);
    }
    
    getCurrentPointerAngle() {
        // Calculate current pointer angle from position
        const pointerLine = this.pointer.querySelector('line');
        const x1 = parseFloat(pointerLine.getAttribute('x1'));
        const y1 = parseFloat(pointerLine.getAttribute('y1'));
        const x2 = parseFloat(pointerLine.getAttribute('x2'));
        const y2 = parseFloat(pointerLine.getAttribute('y2'));
        
        const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI + 90;
        return angle < 0 ? angle + 360 : angle;
    }
    
    setupResponsive() {
        if (!this.options.responsive) return;
        
        // Throttle resize handling to prevent ResizeObserver loops
        let resizeTimeout;
        const resizeObserver = new ResizeObserver(() => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                requestAnimationFrame(() => {
                    this.handleResize();
                });
            }, 100);
        });
        
        resizeObserver.observe(this.container);
    }
    
    handleResize() {
        const containerWidth = this.container.clientWidth;
        let newRadius = this.options.radius;
        
        if (containerWidth < 480) {
            newRadius = 100;
        } else if (containerWidth < 768) {
            newRadius = 125;
        }
        
        if (newRadius !== this.options.radius) {
            this.options.radius = newRadius;
            this.init();
            if (this.currentScore > 0) {
                this.updateScore(this.currentScore, false);
            }
        }
    }
    
    // Public API methods
    setScore(score, animated = true) {
        this.updateScore(score, animated);
    }
    
    getScore() {
        return this.currentScore;
    }
    
    setOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        this.init();
        if (this.currentScore > 0) {
            this.updateScore(this.currentScore, false);
        }
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CreditScoreArc;
}

// Global assignment for direct script inclusion
window.CreditScoreArc = CreditScoreArc;