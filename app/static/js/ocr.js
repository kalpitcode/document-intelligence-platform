/**
 * Document Ingestion & OCR Processing Module
 * Enterprise Document Intelligence Platform
 */

import { apiFetch } from './api.js';
import { writeConsole } from './utils.js';

/**
 * Handle document file selection and upload to backend API.
 * @param {File} file 
 */
export async function uploadAndProcessDocument(file) {
    const consoleBox = document.getElementById('ocr-console');
    if (!file) return;

    writeConsole(consoleBox, `Initiating upload for document '${file.name}' (${(file.size / 1024).toFixed(1)} KB)...`);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('visibility', 'Private');

    try {
        // Step 1: Upload document to /api/v1/documents/upload
        writeConsole(consoleBox, `[STEP 1/2] Uploading binary stream to /api/v1/documents/upload...`, true);
        const uploadRes = await apiFetch('/api/v1/documents/upload', {
            method: 'POST',
            body: formData
        });

        const docData = uploadRes.data || uploadRes;
        const documentId = docData.id;
        writeConsole(consoleBox, `✅ Upload successful! Document ID: ${documentId}`, true);

        // Step 2: Trigger async processing pipeline
        writeConsole(consoleBox, `[STEP 2/2] Triggering OCR & layout parsing via /api/v1/documents/${documentId}/process...`, true);
        const processRes = await apiFetch(`/api/v1/documents/${documentId}/process`, {
            method: 'POST'
        });

        writeConsole(consoleBox, `✅ Processing pipeline status: ${JSON.stringify(processRes, null, 2)}`, true);
    } catch (error) {
        writeConsole(consoleBox, `❌ [OCR ERROR] Upload/Processing failed: ${error.message}`, true);
    }
}

/**
 * Initialize Document OCR event listeners.
 */
export function initOcrModule() {
    const dropzone = document.getElementById('dropzone-ocr');
    const fileInput = document.getElementById('ocr-file-input');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (event) => {
            const files = event.target.files;
            if (files && files.length > 0) {
                uploadAndProcessDocument(files[0]);
            }
        });

        // Drag and drop handlers
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#2563eb';
        });

        dropzone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#3b82f6';
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#3b82f6';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                uploadAndProcessDocument(e.dataTransfer.files[0]);
            }
        });
    }
}
