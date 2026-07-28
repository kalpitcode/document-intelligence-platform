/**
 * Utility Helpers Module
 * Enterprise Document Intelligence Platform
 */

/**
 * Format timestamp string for console logging.
 * @returns {string} HH:MM:SS format string
 */
export function getTimestamp() {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
}

/**
 * Append or set log text in a console container element.
 * @param {string|HTMLElement} elementOrId 
 * @param {string} message 
 * @param {boolean} append 
 */
export function writeConsole(elementOrId, message, append = false) {
    const container = typeof elementOrId === 'string' 
        ? document.getElementById(elementOrId) 
        : elementOrId;
        
    if (!container) return;

    const formattedMessage = `[${getTimestamp()}] ${message}`;

    if (append) {
        container.innerText += `\n${formattedMessage}`;
    } else {
        container.innerText = formattedMessage;
    }
    
    container.scrollTop = container.scrollHeight;
}

/**
 * Display spinner loading indicator on a button.
 * @param {HTMLButtonElement} button 
 * @param {string} loadingText 
 * @returns {function} Restore function
 */
export function setButtonLoading(button, loadingText = 'Processing...') {
    if (!button) return () => {};

    const originalContent = button.innerHTML;
    const originalDisabled = button.disabled;

    button.disabled = true;
    button.innerHTML = `<span class="spinner-sm"></span> ${loadingText}`;

    return function restore() {
        button.disabled = originalDisabled;
        button.innerHTML = originalContent;
    };
}
