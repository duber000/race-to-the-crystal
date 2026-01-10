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
   */
  subscribe(onUpdate) {
    if (!this.config || !this.config.mercure_enabled) {
      console.warn("Mercure not enabled");
      return;
    }

    this.onUpdateCallback = onUpdate;

    // Build Mercure subscription URL
    const hubUrl = new URL(this.config.mercure_hub_url);
    hubUrl.searchParams.append("topic", this.config.mercure_topic);

    console.log(`Subscribing to Mercure: ${hubUrl}`);

    // Create EventSource connection
    this.eventSource = new EventSource(hubUrl);

    this.eventSource.onopen = () => {
      this.connected = true;
      console.log("✓ Mercure EventSource connected");
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("✓ Mercure Update Received:", data);

        // Call the update callback
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

      // Auto-reconnect after a delay
      setTimeout(() => {
        if (!this.connected) {
          console.log("Attempting to reconnect to Mercure...");
          this.subscribe(onUpdate);
        }
      }, 5000);
    };
  }

  /**
   * Close the Mercure connection.
   */
  disconnect() {
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
