/**
 * DeviceCapabilities - Device detection and adaptive configuration
 *
 * Detects device type and provides appropriate configurations for
 * both desktop and mobile browsers.
 *
 * Usage:
 *   const device = new DeviceCapabilities();
 *   if (device.isMobile()) { ... }
 *   const cameraConfig = device.getCameraConfig();
 */
class DeviceCapabilities {
    constructor() {
        this.deviceType = this.detectDeviceType();
        this.touchSupport = this.detectTouchSupport();
        this.screenSize = this.getScreenSize();
        this.performanceProfile = this.detectPerformanceProfile();

        console.log(`[DeviceCapabilities] Type: ${this.deviceType}, Touch: ${this.touchSupport}, Performance: ${this.performanceProfile}`);
    }

    /**
     * Detect device type from user agent
     * @returns {string} 'mobile', 'tablet', or 'desktop'
     */
    detectDeviceType() {
        const ua = navigator.userAgent;

        if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
            return 'tablet';
        }
        if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/i.test(ua)) {
            return 'mobile';
        }
        return 'desktop';
    }

    /**
     * Detect if device supports touch input
     * @returns {boolean}
     */
    detectTouchSupport() {
        return (
            'ontouchstart' in window ||
            navigator.maxTouchPoints > 0 ||
            navigator.msMaxTouchPoints > 0
        );
    }

    /**
     * Get current screen dimensions and breakpoint info
     * @returns {object}
     */
    getScreenSize() {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            isSmall: window.innerWidth < 768,
            isMedium: window.innerWidth >= 768 && window.innerWidth < 1024,
            isLarge: window.innerWidth >= 1024
        };
    }

    /**
     * Detect device performance profile based on hardware
     * @returns {string} 'low', 'medium', or 'high'
     */
    detectPerformanceProfile() {
        // Heuristic: mobile devices typically have fewer cores and slower GPUs
        const cores = navigator.hardwareConcurrency || 4;
        const isMobile = this.deviceType !== 'desktop';

        if (isMobile || cores <= 4) {
            return 'low'; // Reduce quality settings
        } else if (cores <= 8) {
            return 'medium';
        }
        return 'high';
    }

    /**
     * Check if device is mobile or tablet
     * @returns {boolean}
     */
    isMobile() {
        return this.deviceType === 'mobile' || this.deviceType === 'tablet';
    }

    /**
     * Check if device is desktop
     * @returns {boolean}
     */
    isDesktop() {
        return this.deviceType === 'desktop';
    }

    /**
     * Check if device has touch support
     * @returns {boolean}
     */
    hasTouch() {
        return this.touchSupport;
    }

    /**
     * Check if performance optimizations should be applied
     * @returns {boolean}
     */
    shouldOptimizePerformance() {
        return this.performanceProfile === 'low';
    }

    /**
     * Get camera configuration based on device type
     * @returns {object} Camera configuration parameters
     */
    getCameraConfig() {
        if (this.isMobile()) {
            return {
                // Higher sensitivity values = less sensitive (more drag needed)
                panningSensibility: 1000,
                wheelPrecision: 100,
                pinchPrecision: 50,
                inertia: 0.7,
                angularSensibility: 3000,
                touchAngularSensibility: 5000,
                touchMoveSensibility: 100
            };
        }

        // Desktop configuration
        return {
            panningSensibility: 50,
            wheelPrecision: 5,
            pinchPrecision: 0, // Disabled on desktop
            inertia: 0.9,
            angularSensibility: 2000,
            touchAngularSensibility: 2000,
            touchMoveSensibility: 50
        };
    }

    /**
     * Get UI scaling factor based on device and screen size
     * @returns {number} Scale multiplier (1.0 = normal)
     */
    getUIScale() {
        if (this.isMobile()) {
            // Scale up on small mobile screens for better touch targets
            return this.screenSize.isSmall ? 1.2 : 1.0;
        }
        return 1.0;
    }

    /**
     * Get rendering quality settings based on performance profile
     * @returns {object} Rendering configuration
     */
    getRenderingConfig() {
        switch (this.performanceProfile) {
            case 'low':
                return {
                    hardwareScaling: 1.5,
                    shadowsEnabled: false,
                    particleMaxCount: 500,
                    meshTessellation: 12,
                    antialiasing: false
                };
            case 'medium':
                return {
                    hardwareScaling: 1.0,
                    shadowsEnabled: false,
                    particleMaxCount: 1000,
                    meshTessellation: 24,
                    antialiasing: true
                };
            case 'high':
                return {
                    hardwareScaling: 1.0,
                    shadowsEnabled: false, // Game doesn't use shadows currently
                    particleMaxCount: 2000,
                    meshTessellation: 32,
                    antialiasing: true
                };
            default:
                return this.getRenderingConfig(); // Fallback to medium
        }
    }

    /**
     * Check if device supports vibration API
     * @returns {boolean}
     */
    hasVibration() {
        return 'vibrate' in navigator;
    }

    /**
     * Trigger haptic feedback if supported
     * @param {number} duration - Vibration duration in milliseconds
     */
    vibrate(duration = 50) {
        if (this.hasVibration()) {
            navigator.vibrate(duration);
        }
    }

    /**
     * Log device capabilities summary
     */
    logCapabilities() {
        console.log('[DeviceCapabilities] Summary:');
        console.log('  Device Type:', this.deviceType);
        console.log('  Touch Support:', this.touchSupport);
        console.log('  Screen:', `${this.screenSize.width}x${this.screenSize.height}`);
        console.log('  Performance Profile:', this.performanceProfile);
        console.log('  Hardware Cores:', navigator.hardwareConcurrency || 'unknown');
        console.log('  Vibration Support:', this.hasVibration());
    }
}
