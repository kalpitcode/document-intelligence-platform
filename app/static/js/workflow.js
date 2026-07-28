/**
 * Distributed DAG Workflows Module
 * Enterprise Document Intelligence Platform
 */

import { apiFetch } from './api.js';
import { setButtonLoading, writeConsole } from './utils.js';

/**
 * Trigger real DAG workflow execution over backend `/api/v1/workflows`.
 */
export async function runWorkflow() {
    const workflowBtn = document.getElementById('btn-run-workflow');
    const consoleBox = document.getElementById('workflow-console');

    writeConsole(consoleBox, 'Querying active workflow templates from /api/v1/workflows...', false);
    const restoreButton = setButtonLoading(workflowBtn, 'Executing...');

    try {
        // Step 1: List templates
        const templatesRes = await apiFetch('/api/v1/workflows');
        const templates = templatesRes.data?.items || templatesRes.items || [];

        if (templates.length === 0) {
            writeConsole(consoleBox, 'ℹ️ No pre-registered active workflow templates found in database. Response:\n' + JSON.stringify(templatesRes, null, 2), false);
            return;
        }

        const targetTemplate = templates[0];
        writeConsole(consoleBox, `Found workflow template '${targetTemplate.name}' (ID: ${targetTemplate.id}). Triggering execution...`, true);

        // Step 2: Execute template
        const executeRes = await apiFetch(`/api/v1/workflows/${targetTemplate.id}/execute`, {
            method: 'POST',
            body: {
                inputs: { pipeline: 'standard_ingestion' },
                run_async: true
            }
        });

        writeConsole(consoleBox, `✅ DAG Workflow execution triggered successfully!\n` + JSON.stringify(executeRes, null, 2), true);
    } catch (error) {
        writeConsole(consoleBox, `❌ [WORKFLOW ERROR] Execution failed: ${error.message}`, false);
    } finally {
        restoreButton();
    }
}

/**
 * Initialize Workflow module listeners.
 */
export function initWorkflowModule() {
    const workflowBtn = document.getElementById('btn-run-workflow');
    if (workflowBtn) {
        workflowBtn.addEventListener('click', runWorkflow);
    }
}
