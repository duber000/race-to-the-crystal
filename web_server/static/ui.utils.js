// ==========================================================================
// UI Utilities - Extracted common UI patterns from UIManager
// ==========================================================================

/**
 * UI Utilities - Common UI patterns extracted from UIManager
 */
class UIUtils {
  /**
   * Show a temporary message element that auto-removes after a delay
   * @param {string} containerId - ID of container element (defaults to body)
   * @param {string} className - CSS class for the message element
   * @param {string} message - Text content to display
   * @param {number} delayMs - Delay in milliseconds before auto-removal (0 for no auto-remove)
   * @returns {HTMLElement} The created message element
   */
  static showTemporaryMessage(containerId, className, message, delayMs = 3000) {
    const container = containerId ? document.getElementById(containerId) : document.body;
    if (!container) return null;

    const messageEl = document.createElement("div");
    messageEl.className = className;
    messageEl.textContent = message;
    container.appendChild(messageEl);

    if (delayMs > 0) {
      setTimeout(() => {
        if (messageEl.parentNode) {
          messageEl.parentNode.removeChild(messageEl);
        }
      }, delayMs);
    }

    return messageEl;
  }

  /**
   * Set element visibility by ID
   * @param {string} elementId - ID of the element
   * @param {boolean} hidden - Whether the element should be hidden
   * @returns {boolean} True if element was found and modified
   */
  static setHiddenById(elementId, hidden) {
    const element = document.getElementById(elementId);
    if (!element) return false;
    element.classList.toggle("hidden", hidden);
    return true;
  }

  /**
   * Toggle element visibility by ID
   * @param {string} elementId - ID of the element
   * @returns {boolean} True if element was found and toggled
   */
  static toggleHiddenById(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return false;
    element.classList.toggle("hidden");
    return true;
  }

  /**
   * Check if element is hidden by ID
   * @param {string} elementId - ID of the element
   * @returns {boolean} True if element is hidden or false if not found/not hidden
   */
  static isHiddenById(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return false;
    return element.classList.contains("hidden");
  }

  /**
   * Setup a button with click handler and optional enter key support
   * @param {string} buttonId - ID of the button element
   * @param {Function} clickHandler - Function to call on click
   * @param {string} inputId - Optional ID of input field to listen for Enter key
   * @returns {Object} Object with cleanup functions
   */
  static setupButton(buttonId, clickHandler, inputId = null) {
    const button = document.getElementById(buttonId);
    if (!button || !clickHandler) return null;

    const handleClick = () => clickHandler();
    button.addEventListener("click", handleClick);

    let inputHandler = null;
    if (inputId) {
      const input = document.getElementById(inputId);
      if (input) {
        inputHandler = (e) => {
          if (e.key === "Enter") {
            button.click();
          }
        };
        input.addEventListener("keypress", inputHandler);
      }
    }

    return {
      cleanup: () => {
        button.removeEventListener("click", handleClick);
        if (inputHandler) {
          const input = document.getElementById(inputId);
          if (input) {
            input.removeEventListener("keypress", inputHandler);
          }
        }
      }
    };
  }

  /**
   * Setup a form with submit and cancel buttons
   * @param {Object} config - Configuration object
   * @param {string} config.formSectionId - ID of the form section to show/hide
   * @param {string} config.showButtonId - ID of button that shows the form
   * @param {string} config.hideButtonId - ID of button that hides the form
   * @param {string} config.confirmButtonId - ID of button that confirms form submission
   * @param {Function} config.submitHandler - Function to call on form submission
   * @param {Array} config.validations - Array of validation functions
   * @returns {Object} Object with cleanup functions
   */
  static setupForm(config) {
    const {
      formSectionId,
      showButtonId,
      hideButtonId,
      confirmButtonId,
      submitHandler,
      validations = []
    } = config;

    const formSection = document.getElementById(formSectionId);
    const showButton = document.getElementById(showButtonId);
    const hideButton = document.getElementById(hideButtonId);
    const confirmButton = document.getElementById(confirmButtonId);

    if (!(formSection && showButton && hideButton && confirmButton && submitHandler)) {
      return null;
    }

    const showForm = () => {
      formSection.classList.remove("hidden");
      showButton.classList.add("hidden");
      // Focus first input if available
      const firstInput = formSection.querySelector("input, select, textarea");
      if (firstInput) firstInput.focus();
    };

    const hideForm = () => {
      formSection.classList.add("hidden");
      showButton.classList.remove("hidden");
    };

    const handleSubmit = () => {
      // Run validations
      for (const validation of validations) {
        const validationResult = validation();
        if (validationResult !== true) {
          // Assume validation returns error string or false
          const errorMsg = typeof validationResult === "string" 
            ? validationResult 
            : "Validation failed";
          // TODO: Show error to user
          console.warn("Form validation failed:", errorMsg);
          return;
        }
      }
      
      hideForm();
      submitHandler();
    };

    showButton.addEventListener("click", showForm);
    hideButton.addEventListener("click", hideForm);
    confirmButton.addEventListener("click", handleSubmit);

    // Allow Enter key in form to submit
    const formInputs = formSection.querySelectorAll("input");
    formInputs.forEach(input => {
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          confirmButton.click();
        }
      });
    });

    return {
      cleanup: () => {
        showButton.removeEventListener("click", showForm);
        hideButton.removeEventListener("click", hideForm);
        confirmButton.removeEventListener("click", handleSubmit);
        formInputs.forEach(input => {
          input.removeEventListener("keypress", () => {});
        });
      }
    };
  }

  /**
   * Create a standardized error message element
   * @param {string} message - Error message text
   * @param {string} type - Type of error ('connection', 'lobby', 'action')
   * @returns {HTMLElement} The created error element
   */
  static createErrorElement(message, type = "action") {
    const errorDiv = document.createElement("div");
    let className = "action-error";
    
    switch (type) {
      case "connection":
        className = "connection-error";
        break;
      case "lobby":
        className = "lobby-error";
        break;
      case "action":
      default:
        className = "action-error";
        break;
    }
    
    errorDiv.className = className;
    errorDiv.textContent = message;
    return errorDiv;
  }
}

export { UIUtils };