/**
 * Centralized API Communication Module
 * Enterprise Document Intelligence Platform
 */

/**
 * Execute HTTP request to backend FastAPI REST API endpoints with standardized error handling.
 * 
 * @param {string} endpoint - API relative URI (e.g. '/api/v1/health')
 * @param {object} options - Fetch options object (method, headers, body)
 * @returns {Promise<any>} Parsed JSON response payload
 */
export async function apiFetch(endpoint, options = {}) {
    const defaultHeaders = {
        'Accept': 'application/json'
    };

    // If sending JSON body, set Content-Type
    if (options.body && !(options.body instanceof FormData) && typeof options.body === 'object') {
        defaultHeaders['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };

    try {
        const response = await fetch(endpoint, config);
        const data = await response.json().catch(() => ({
            success: false,
            message: `Server returned status ${response.status} (${response.statusText})`
        }));

        if (!response.ok) {
            const errorMessage = data.detail 
                ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
                : (data.message || `Request failed with HTTP status ${response.status}`);
            throw new Error(errorMessage);
        }

        return data;
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Network error: Unable to connect to backend server');
        }
        throw error;
    }
}
