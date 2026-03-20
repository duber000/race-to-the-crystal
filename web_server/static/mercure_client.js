/**
 * Mercure EventSource client for real-time game state updates.
 *
 * This module provides an alternative to WebSocket for receiving real-time
 * game state updates using Server-Sent Events (SSE) via Mercure.
 *
 * @example
 * const mercure = new MercureClient();
 * await mercure.init();
 * mercure.subscribe((update) => {
 *     console.log('Game state updated:', update);
 * });
 */
class MercureClient {
  /**
   * Create a Mercure client instance.
   */
  constructor() {
    this.eventSource = null;
    this.config = null;
    this.connected = false;
    this.onUpdateCallback = null;
    this.eventHandlers = new Map(); // Type-specific event handlers
    this.lastEventId = null; // For resuming from last event
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = TIMEOUT_CONFIG.RECONNECT_MAX_DELAY_MS;
    this.lastMessageTime = null;
    this.silenceTimer = null;
    this.onFallbackCallback = null; // Called when SSE fails
    this.onErrorCallback = null; // Called on errors
  }

  /**
   * Initialize Mercure client by fetching configuration from server.
   * @returns {Promise<boolean>} Success status
   */
  async init() {
    try {
      const response = await fetch("/api/config");
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch config`);
      }
      
      const data = await response.json();
      
      // Validate required config fields
      if (!data.mercure_hub_url || !data.mercure_topic) {
        throw new Error("Invalid config: missing mercure_hub_url or mercure_topic");
      }
      
      this.config = data;
      console.log("✓ Mercure config loaded:", this.config);

      if (!this.config.mercure_enabled) {
        console.warn("⚠ Mercure is disabled - falling back to WebSocket");
        return false;
      }

      return true;
    } catch (error) {
      console.error("Failed to load Mercure config:", error.message || error);
      if (this.onErrorCallback) {
        this.onErrorCallback("Mercure config failed: " + (error.message || error));
      }
      return false;
    }
  }

  /**
   * Update the Mercure topic to subscribe to.
   * Call this before subscribe() to set the correct topic (e.g., with game_id).
   * @param {string} topic - The topic URL to subscribe to
   */
  setTopic(topic) {
    if (this.config) {
      this.config.mercure_topic = topic;
      console.log(`Updated Mercure topic to: ${topic}`);
    }
  }

  /**
   * Subscribe to Mercure events
   * @param {Function} onUpdate - Callback for state updates
   * @param {Function} onFallback - Callback when SSE fails (triggers WebSocket fallback)
   * @param {Function} onError - Optional callback for error notifications
   */
  subscribe(onUpdate, onFallback = null, onError = null) {
    if (!this.config || !this.config.mercure_enabled) {
      console.warn("Mercure not enabled");
      return;
    }

    this.onUpdateCallback = onUpdate;
    this.onFallbackCallback = onFallback;
    this.onErrorCallback = onError;

    // Build Mercure subscription URL
    const hubUrl = new URL(this.config.mercure_hub_url);
    hubUrl.searchParams.append("topic", this.config.mercure_topic);

    // Resume from last event if available (prevents missed updates)
    if (this.lastEventId) {
      hubUrl.searchParams.append("Last-Event-ID", this.lastEventId);
      console.log(`Resuming from event ID: ${this.lastEventId}`);
    }

    console.log(`Subscribing to Mercure: ${hubUrl}`);

    // Create EventSource connection
    this.eventSource = new EventSource(hubUrl);

    this.eventSource.onopen = () => {
      this.connected = true;
      this.reconnectAttempts = 0; // Reset on successful connection
      this.lastMessageTime = Date.now();
      console.log("✓ Mercure EventSource connected");
      console.log("✓ Using SSE for state updates");

      // Start silence detection (30-second timeout)
      this._startSilenceDetection();
    };

    this.eventSource.onmessage = (event) => {
      try {
        // Update last message time and event ID
        this.lastMessageTime = Date.now();
        if (event.lastEventId) {
          this.lastEventId = event.lastEventId;
        }

        const data = JSON.parse(event.data);
        console.log("✓ Mercure Update Received:", data);

        // Route to type-specific handler if available
        const messageType = data.type;
        if (messageType && this.eventHandlers.has(messageType)) {
          this.eventHandlers.get(messageType)(data);
        }

        // Call the general update callback
        if (this.onUpdateCallback) {
          this.onUpdateCallback(data);
        }
      } catch (error) {
        console.error("Error parsing Mercure message:", error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error("Mercure connection error:", error);
      this.connected = false;
      this._stopSilenceDetection();

      // Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
      const delay = Math.min(
        1000 * Math.pow(2, this.reconnectAttempts),
        this.maxReconnectDelay
      );
      this.reconnectAttempts++;

      console.log(
        `Attempting to reconnect to Mercure in ${delay / 1000}s (attempt ${this.reconnectAttempts})...`
      );

      setTimeout(() => {
        if (!this.connected) {
      // After max attempts failed, trigger fallback
      if (this.reconnectAttempts >= TIMEOUT_CONFIG.RECONNECT_MAX_ATTEMPTS && this.onFallbackCallback) {
            console.warn("⚠ SSE reconnection failed - triggering WebSocket fallback");
            this.onFallbackCallback();
          } else {
            this.subscribe(onUpdate, onFallback);
          }
        }
      }, delay);
    };
  }

  /**
   * Register a handler for a specific message type.
   * Enables event-driven animations and updates.
   * @param {string} messageType - Message type (e.g., 'TOKEN_MOVED', 'COMBAT_RESULT')
   * @param {Function} handler - Handler function called with message data
   */
  on(messageType, handler) {
    this.eventHandlers.set(messageType, handler);
  }

  /**
   * Start silence detection timer (30-second timeout).
   * If no messages received for 30 seconds, trigger fallback.
   * @private
   */
  _startSilenceDetection() {
    this._stopSilenceDetection(); // Clear existing timer

    this.silenceTimer = setInterval(() => {
      const timeSinceLastMessage = Date.now() - this.lastMessageTime;

      if (timeSinceLastMessage > TIMEOUT_CONFIG.SSE_SILENCE_MS) {
        console.warn("⚠ SSE silent for 30+ seconds - triggering fallback");
        this._stopSilenceDetection();

        if (this.onFallbackCallback) {
          this.onFallbackCallback();
        }
      }
    }, TIMEOUT_CONFIG.SSE_CHECK_INTERVAL_MS); // Check every 5 seconds
  }

  /**
   * Stop silence detection timer.
   * @private
   */
  _stopSilenceDetection() {
    if (this.silenceTimer) {
      clearInterval(this.silenceTimer);
      this.silenceTimer = null;
    }
  }

  /**
   * Close the Mercure connection and clean up resources.
   */
  disconnect() {
    this._stopSilenceDetection();

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.connected = false;
      console.log("Mercure disconnected");
    }
  }

  /**
   * Check if Mercure is connected.
   * @returns {boolean} True if connected
   */
  isConnected() {
    return this.connected;
  }
}

/**
 * Example integration with existing game client:
 *
 * // Initialize Mercure client
 * const mercure = new MercureClient();
 * const mercureReady = await mercure.init();
 *
 * if (mercureReady) {
 *     // Subscribe to updates
 *     mercure.subscribe((update) => {
 *         if (update.type === 'state_update') {
 *             updateGameState(update.state);
 *
 *             // Handle action-specific updates
 *             if (update.last_action) {
 *                 console.log(`Last action: ${update.last_action}`);
 *             }
 *         }
 *     });
 * } else {
 *     // Fall back to WebSocket
 *     connectWebSocket();
 * }
 */

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = MercureClient;
}
