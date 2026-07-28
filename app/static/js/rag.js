/**
 * Enterprise RAG Chat Module
 * Enterprise Document Intelligence Platform
 */

import { apiFetch } from './api.js';
import { setButtonLoading } from './utils.js';

let activeSessionId = null;

/**
 * Send user message to RAG Chat engine endpoint `/api/v1/chat`.
 */
export async function sendRagMessage() {
    const input = document.getElementById('rag-input');
    const sendBtn = document.getElementById('btn-send-rag');
    const chatBox = document.getElementById('chat-box');

    if (!input || !chatBox) return;

    const userText = input.value.trim();
    if (!userText) return;

    // Append User Message Bubble
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-bubble user-bubble';
    userDiv.innerText = userText;
    chatBox.appendChild(userDiv);
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    const restoreButton = setButtonLoading(sendBtn, 'Thinking...');

    try {
        const payload = {
            question: userText,
            top_k: 3,
            session_id: activeSessionId
        };

        const response = await apiFetch('/api/v1/chat', {
            method: 'POST',
            body: payload
        });

        const resData = response.data || response;
        if (resData.session_id) {
            activeSessionId = resData.session_id;
        }

        const aiDiv = document.createElement('div');
        aiDiv.className = 'chat-bubble ai-bubble';

        const answerText = resData.answer || JSON.stringify(resData, null, 2);
        aiDiv.innerText = answerText;

        // Render Citations if available
        if (resData.citations && resData.citations.length > 0) {
            const citationsDiv = document.createElement('div');
            citationsDiv.className = 'citation-box';
            const citationsText = resData.citations.map(c => 
                `📌 ${c.document_name || c.document_id} (Page ${c.page_number || 1}) - Score: ${c.score ? c.score.toFixed(3) : 'N/A'}`
            ).join('<br>');
            citationsDiv.innerHTML = `<strong>Citations:</strong><br>${citationsText}`;
            aiDiv.appendChild(citationsDiv);
        }

        chatBox.appendChild(aiDiv);
    } catch (error) {
        const errDiv = document.createElement('div');
        errDiv.className = 'chat-bubble ai-bubble';
        errDiv.innerText = `❌ [RAG ERROR] Unable to generate answer: ${error.message}`;
        chatBox.appendChild(errDiv);
    } finally {
        restoreButton();
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

/**
 * Initialize RAG chat event listeners.
 */
export function initRagModule() {
    const sendBtn = document.getElementById('btn-send-rag');
    const input = document.getElementById('rag-input');

    if (sendBtn) {
        sendBtn.addEventListener('click', sendRagMessage);
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                sendRagMessage();
            }
        });
    }
}
