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

    /* ══════════════════════════════════════════════════════════
       Phase 2 — Image OCR
       ══════════════════════════════════════════════════════════ */

    const imageInput            = document.getElementById('imageInput');
    const chooseImageBtn        = document.getElementById('chooseImageBtn');
    const imageFilename         = document.getElementById('imageFilename');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview          = document.getElementById('imagePreview');
    const extractBtn            = document.getElementById('extractBtn');
    const ocrStatus             = document.getElementById('ocrStatus');
    const confidenceBadge       = document.getElementById('confidenceBadge');
    const ocrWarning            = document.getElementById('ocrWarning');
    const extractedText         = document.getElementById('extractedText');
    const ocrTranslateBtn       = document.getElementById('ocrTranslateBtn');
    const ocrStatusTranslate    = document.getElementById('ocrStatusTranslate');
    const ocrOutputArea         = document.getElementById('ocrOutputArea');
    const ocrTranslationText    = document.getElementById('ocrTranslationText');
    const ocrModelInfo          = document.getElementById('ocrModelInfo');

    // Mirrors MAX_IMAGE_BYTES on the backend (15 MB) for a fast client-side check.
    const MAX_IMAGE_BYTES = 15 * 1024 * 1024;
    const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic'];

    // Track the active object URL so we can revoke it when a new image is chosen.
    let previewObjectUrl = null;

    // ── Event listeners ──
    chooseImageBtn.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', handleImageSelect);
    extractBtn.addEventListener('click', submitOCR);
    ocrTranslateBtn.addEventListener('click', submitOCRTranslation);
    extractedText.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            submitOCRTranslation();
        }
    });

    /**
     * Show an inline message in the filename area near the choose button.
     * @param {string} message - Text to display.
     * @param {boolean} isError - Whether to style the message as an error.
     */
    function showImageMessage(message, isError) {
        imageFilename.textContent = message;
        imageFilename.classList.toggle('error', Boolean(isError));
    }

    /**
     * Reset all OCR-related output: confidence badge, warning, extracted text,
     * translation, and disable the dependent controls.
     */
    function clearOCROutput() {
        confidenceBadge.hidden = true;
        confidenceBadge.textContent = '';
        confidenceBadge.classList.remove('conf-good', 'conf-fair', 'conf-poor', 'conf-low');
        ocrWarning.hidden = true;
        ocrWarning.textContent = '';
        extractedText.value = '';
        extractedText.disabled = true;
        ocrTranslateBtn.disabled = true;
        ocrOutputArea.hidden = true;
        ocrTranslationText.textContent = '';
        ocrTranslationText.classList.remove('error');
        ocrModelInfo.textContent = '';
    }

    /**
     * Validate the chosen file, show a preview, and prime the Extract button.
     */
    function handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // Client-side type check.
        if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
            showImageMessage('Unsupported file type. Use JPEG, PNG, WEBP, or HEIC.', true);
            extractBtn.disabled = true;
            return;
        }

        // Client-side size check.
        if (file.size > MAX_IMAGE_BYTES) {
            showImageMessage('Image too large. Maximum size is 15 MB.', true);
            extractBtn.disabled = true;
            return;
        }

        // Valid file — show its name.
        showImageMessage(file.name, false);

        // Build a preview, replacing any prior object URL.
        if (previewObjectUrl) {
            URL.revokeObjectURL(previewObjectUrl);
        }
        previewObjectUrl = URL.createObjectURL(file);
        imagePreview.src = previewObjectUrl;
        imagePreviewContainer.hidden = false;

        // Enable extraction and clear any earlier results.
        extractBtn.disabled = false;
        clearOCROutput();
    }

    /**
     * Upload the selected image to /ocr, then populate the editable text area
     * and confidence indicator with the result.
     */
    async function submitOCR() {
        const file = imageInput.files[0];
        if (!file) {
            return;
        }

        extractBtn.disabled = true;
        ocrStatus.hidden = false;
        clearOCROutput();

        try {
            const formData = new FormData();
            // Field name "image" matches the UploadFile parameter in main.py.
            formData.append('image', file);

            // Do NOT set Content-Type — the browser adds the multipart boundary.
            const response = await fetch('/ocr', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                extractedText.value = data.extracted_text;
                extractedText.disabled = false;
                ocrTranslateBtn.disabled = false;

                // Confidence badge: map label → CSS class.
                const labelToClass = {
                    'Good': 'conf-good',
                    'Fair': 'conf-fair',
                    'Poor': 'conf-poor',
                    'Low — review carefully': 'conf-low',
                };
                const cls = labelToClass[data.confidence_label];
                if (cls) {
                    confidenceBadge.classList.add(cls);
                }
                const scoreText = data.confidence >= 0
                    ? ` (${data.confidence}%)`
                    : '';
                confidenceBadge.textContent = `${data.confidence_label}${scoreText}`;
                confidenceBadge.hidden = false;

                // Optional low-confidence warning.
                if (data.warning) {
                    ocrWarning.textContent = data.warning;
                    ocrWarning.hidden = false;
                } else {
                    ocrWarning.hidden = true;
                }
            } else {
                // API-level error (422, 503, 500).
                const message = data.error || data.detail || 'Text extraction failed.';
                showImageMessage(message, true);
                confidenceBadge.hidden = true;
            }
        } catch (err) {
            showImageMessage('Could not reach the server. Is the app running?', true);
            confidenceBadge.hidden = true;
        } finally {
            extractBtn.disabled = false;
            ocrStatus.hidden = true;
        }
    }

    /**
     * Translate the (possibly edited) extracted text via the Phase 1 /translate
     * endpoint and show the English result.
     */
    async function submitOCRTranslation() {
        const text = extractedText.value.trim();
        if (!text) {
            return;
        }

        ocrTranslateBtn.disabled = true;
        ocrStatusTranslate.hidden = false;
        ocrOutputArea.hidden = true;
        ocrTranslationText.textContent = '';
        ocrModelInfo.textContent = '';

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();

            if (response.ok) {
                ocrTranslationText.textContent = data.translation;
                ocrTranslationText.classList.remove('error');
                ocrModelInfo.textContent = `Model: ${data.model}`;
            } else {
                const message = data.error || data.detail || 'Translation failed.';
                ocrTranslationText.textContent = message;
                ocrTranslationText.classList.add('error');
                ocrModelInfo.textContent = '';
            }

            ocrOutputArea.hidden = false;
        } catch (err) {
            ocrTranslationText.textContent = 'Could not reach the server. Is the app running?';
            ocrTranslationText.classList.add('error');
            ocrModelInfo.textContent = '';
            ocrOutputArea.hidden = false;
        } finally {
            ocrTranslateBtn.disabled = false;
            ocrStatusTranslate.hidden = true;
        }
    }
});
