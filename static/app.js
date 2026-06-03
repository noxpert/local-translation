'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const input      = document.getElementById('hungarianInput');
    const btn        = document.getElementById('translateBtn');
    const statusArea = document.getElementById('statusArea');
    const outputArea = document.getElementById('outputArea');
    const outputText = document.getElementById('translationText');
    const modelInfo  = document.getElementById('modelInfo');

    // Submit on button click
    btn.addEventListener('click', submitTranslation);

    // Submit on Ctrl+Enter inside the textarea
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            submitTranslation();
        }
    });

    // Clear output whenever the user edits the input after a result is shown
    input.addEventListener('input', () => {
        if (!outputArea.hidden) {
            clearOutput();
        }
    });

    /**
     * Hide the output area and clear its contents.
     * Called when the user modifies the input after a result has been shown.
     */
    function clearOutput() {
        outputArea.hidden = true;
        outputText.textContent = '';
        outputText.classList.remove('error');
        modelInfo.textContent = '';
    }

    /**
     * Read the textarea, validate it, call the /translate endpoint,
     * and display the result or error.
     */
    async function submitTranslation() {
        const text = input.value.trim();

        if (!text) {
            input.focus();
            return;
        }

        // Show loading state
        btn.disabled = true;
        statusArea.hidden = false;
        clearOutput();

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();

            if (response.ok) {
                // Success — show translation
                outputText.textContent = data.translation;
                outputText.classList.remove('error');
                modelInfo.textContent = `Model: ${data.model}`;
            } else {
                // API-level error (503, 500, 422, etc.)
                const message = data.error || data.detail || 'Translation failed. Please try again.';
                outputText.textContent = message;
                outputText.classList.add('error');
            }

            outputArea.hidden = false;
        } catch (err) {
            // Network or parse error
            outputText.textContent = 'Could not reach the server. Is the app running?';
            outputText.classList.add('error');
            outputArea.hidden = false;
        } finally {
            // Always restore the button and hide the spinner
            statusArea.hidden = true;
            btn.disabled = false;
        }
    }
});
