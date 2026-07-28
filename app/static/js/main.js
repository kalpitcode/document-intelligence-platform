/**
 * Main Application Bootstrap Module
 * Enterprise Document Intelligence Platform
 */

import { initTabs } from './tabs.js';
import { initHealthModule } from './health.js';
import { initOcrModule } from './ocr.js';
import { initSearchModule } from './search.js';
import { initRagModule } from './rag.js';
import { initWorkflowModule } from './workflow.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SYSTEM] Initializing Enterprise AI Document Intelligence Platform Frontend...');
    
    initTabs();
    initHealthModule();
    initOcrModule();
    initSearchModule();
    initRagModule();
    initWorkflowModule();

    console.log('[SYSTEM] All feature modules initialized successfully.');
});
