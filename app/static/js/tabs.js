/**
 * Navigation & Tab Switcher Module
 * Enterprise Document Intelligence Platform
 */

/**
 * Initialize tab switching event listeners across the dashboard.
 */
export function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTabId = button.getAttribute('data-tab');
            if (!targetTabId) return;

            // Update active states on buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update active states on tab content sections
            tabContents.forEach(content => content.classList.remove('active'));
            const targetContent = document.getElementById(`tab-${targetTabId}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}
