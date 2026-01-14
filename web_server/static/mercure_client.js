/**
 * Mercure EventSource client for real-time game state updates.
 *
 * This module provides an alternative to WebSocket for receiving real-time
 * game state updates using Server-Sent Events (SSE) via Mercure.
 *
 * Usage:
 *   const mercure = new MercureClient();
 *   await mercure.init();
 *   mercure.subscribe((update) => {
 *       console.log('Game state updated:', update);
 *   });
 */

class MercureClient {
  constructor() {
    this.eventSource = null;
    this.config = null;
    this.connected = false;
    this.onUpdateCallback = null;
    this.eventHandlers = new Map(); // Type-specific event handlers
    this.lastEventId = null; // For resuming from last event
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 30000; // 30 seconds max
    this.lastMessageTime = null;
    this.silenceTimer = null;
    this.onFallbackCallback = null; // Called when SSE fails
  }

  /**
   * Initialize Mercure client by fetching configuration from server.
   */
  async init() {
    try {
      const response = await fetch("/api/config");
      this.config = await response.json();

      console.log("✓ Mercure config loaded:", this.config);

      if (!this.config.mercure_enabled) {
        console.warn("⚠ Mercure is disabled - falling back to WebSocket");
        return false;
      }

      return true;
    } catch (error) {
      console.error("Failed to load Mercure config:", error);
      return false;
    }
  }

  /**
   * Connect to Mercure hub and subscribe to game state updates.
   *
   * @param {Function} onUpdate - Callback function called when state updates arrive
   * @param {Function} onFallback - Optional callback when SSE fails (triggers WebSocket fallback)
   */
  subscribe(onUpdate, onFallback = null) {
    if (!this.config || !this.config.mercure_enabled) {
      console.warn("Mercure not enabled");
      return;
    }

    this.onUpdateCallback = onUpdate;
    this.onFallbackCallback = onFallback;

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
          // After 4 failed attempts, trigger fallback
          if (this.reconnectAttempts >= 4 && this.onFallbackCallback) {
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
   *
   * @param {string} messageType - Message type (e.g., 'TOKEN_MOVED', 'COMBAT_RESULT')
   * @param {Function} handler - Handler function
   */
  on(messageType, handler) {
    this.eventHandlers.set(messageType, handler);
  }

  /**
   * Start silence detection timer (30-second timeout).
   * If no messages received for 30 seconds, trigger fallback.
   */
  _startSilenceDetection() {
    this._stopSilenceDetection(); // Clear existing timer

    this.silenceTimer = setInterval(() => {
      const timeSinceLastMessage = Date.now() - this.lastMessageTime;

      if (timeSinceLastMessage > 30000) {
        console.warn("⚠ SSE silent for 30+ seconds - triggering fallback");
        this._stopSilenceDetection();

        if (this.onFallbackCallback) {
          this.onFallbackCallback();
        }
      }
    }, 5000); // Check every 5 seconds
  }

  /**
   * Stop silence detection timer.
   */
  _stopSilenceDetection() {
    if (this.silenceTimer) {
      clearInterval(this.silenceTimer);
      this.silenceTimer = null;
    }
  }

  /**
   * Close the Mercure connection.
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
