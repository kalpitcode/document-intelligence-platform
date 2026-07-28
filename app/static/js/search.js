/**
 * Hybrid Vector Search Module
 * Enterprise Document Intelligence Platform
 */

import { apiFetch } from './api.js';
import { setButtonLoading, writeConsole } from './utils.js';

/**
 * Execute Hybrid Vector Search over backend `/api/v1/search`.
 */
export async function runSearch() {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('btn-run-search');
    const consoleBox = document.getElementById('search-console');

    const query = searchInput ? searchInput.value.trim() : '';
    if (!query) {
        writeConsole(consoleBox, '⚠️ Please enter a search query before executing.', false);
        return;
    }

    writeConsole(consoleBox, `Executing RRF Hybrid Search query: "${query}"...`, false);
    const restoreButton = setButtonLoading(searchBtn, 'Searching...');

    try {
        const payload = {
            query: query,
            query_type: 'hybrid',
            top_k: 3
        };

        const response = await apiFetch('/api/v1/search', {
            method: 'POST',
            body: payload
        });

        if (consoleBox) {
            consoleBox.innerText = JSON.stringify(response, null, 2);
        }
    } catch (error) {
        writeConsole(consoleBox, `❌ [SEARCH ERROR] Query execution failed: ${error.message}`, false);
    } finally {
        restoreButton();
    }
}

/**
 * Initialize search event listeners and preset chips.
 */
export function initSearchModule() {
    const searchBtn = document.getElementById('btn-run-search');
    const searchInput = document.getElementById('search-input');
    const chips = document.querySelectorAll('#tab-search .chip');

    if (searchBtn) {
        searchBtn.addEventListener('click', runSearch);
    }

    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                runSearch();
            }
        });
    }

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const presetQuery = chip.getAttribute('data-query');
            if (presetQuery && searchInput) {
                searchInput.value = presetQuery;
                runSearch();
            }
        });
    });
}
