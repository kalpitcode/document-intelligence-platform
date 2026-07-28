/**
 * System Health Diagnostics Module
 * Enterprise Document Intelligence Platform
 */

import { apiFetch } from './api.js';
import { setButtonLoading, writeConsole } from './utils.js';

/**
 * Query live component health diagnostic probe from backend `/api/v1/health`.
 */
export async function fetchHealth() {
    const consoleBox = document.getElementById('health-console');
    const refreshBtn = document.getElementById('btn-refresh-health');
    
    writeConsole(consoleBox, 'Querying live system health probe from /api/v1/health...');

    const restoreButton = setButtonLoading(refreshBtn, 'Checking...');

    try {
        const response = await apiFetch('/api/v1/health');
        
        // Render JSON response payload cleanly
        if (consoleBox) {
            consoleBox.innerText = JSON.stringify(response, null, 2);
        }
    } catch (error) {
        writeConsole(
            consoleBox, 
            `[HEALTH ERROR] Failed to fetch health diagnostic: ${error.message}`, 
            false
        );
    } finally {
        restoreButton();
    }
}

/**
 * Initialize Health check module listeners.
 */
export function initHealthModule() {
    const refreshBtn = document.getElementById('btn-refresh-health');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchHealth);
    }

    // Initial load check
    fetchHealth();
}
