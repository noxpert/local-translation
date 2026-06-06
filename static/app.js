'use strict';

document.addEventListener('DOMContentLoaded', () => {

    /* ══════════════════════════════════════════════════════════
       Mode toggle
       ══════════════════════════════════════════════════════════ */

    const modeToggleBtn = document.getElementById('modeToggleBtn');
    const modeSubtitle  = document.getElementById('modeSubtitle');
    const phase1Section = document.getElementById('phase1');
    const phase2Section = document.getElementById('phase2');
    const phaseDivider  = document.querySelector('hr.phase-divider');

    let currentMode = 'phase1';

    function switchMode() {
        if (currentMode === 'phase1') {
            phase1Section.classList.add('hidden');
            phase2Section.classList.remove('hidden');
            modeToggleBtn.textContent = 'Switch to Typed Translation';
            modeSubtitle.textContent  = 'Mode: Image OCR';
            currentMode = 'phase2';
        } else {
            phase2Section.classList.add('hidden');
            phase1Section.classList.remove('hidden');
            modeToggleBtn.textContent = 'Switch to Image Translation';
            modeSubtitle.textContent  = 'Mode: Typed Text';
            currentMode = 'phase1';
        }
        if (phaseDivider) phaseDivider.classList.add('hidden');
    }

    modeToggleBtn.addEventListener('click', switchMode);

    // Apply the server-configured default mode (APP_DEFAULT_MODE in .env).
    fetch('/config')
        .then((r) => r.json())
        .then((cfg) => { if (cfg.default_mode === 'image') switchMode(); })
        .catch(() => {});

    /* ══════════════════════════════════════════════════════════
       Phase 1 — Typed text translation
       ══════════════════════════════════════════════════════════ */

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

    // ── Element references ──
    const imageInput            = document.getElementById('imageInput');
    const chooseImageBtn        = document.getElementById('chooseImageBtn');
    const webcamBtn             = document.getElementById('webcamBtn');
    const imageFilename         = document.getElementById('imageFilename');
    const webcamSection         = document.getElementById('webcamSection');
    const webcamVideo           = document.getElementById('webcamVideo');
    const captureBtn            = document.getElementById('captureBtn');
    const closeWebcamBtn        = document.getElementById('closeWebcamBtn');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const editCanvas            = document.getElementById('editCanvas');
    const rotateLeftBtn         = document.getElementById('rotateLeftBtn');
    const rotateRightBtn        = document.getElementById('rotateRightBtn');
    const cropToggleBtn         = document.getElementById('cropToggleBtn');
    const applyCropBtn          = document.getElementById('applyCropBtn');
    const cancelCropBtn         = document.getElementById('cancelCropBtn');
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

    const MAX_IMAGE_BYTES  = 15 * 1024 * 1024;
    const ALLOWED_TYPES    = ['image/jpeg', 'image/png', 'image/webp', 'image/heic'];

    // ── State ──
    let webcamStream   = null;  // active MediaStream while webcam is open
    let isCropping     = false;
    let cropStart      = null;  // canvas-pixel coords of drag start
    let cropRect       = null;  // { x, y, w, h } in canvas pixels
    let savedImageData = null;  // clean ImageData snapshot taken on enterCropMode()

    // ── Event wiring ──
    chooseImageBtn.addEventListener('click', () => imageInput.click());
    webcamBtn.addEventListener('click', openWebcam);
    imageInput.addEventListener('change', handleImageSelect);
    captureBtn.addEventListener('click', captureFromWebcam);
    closeWebcamBtn.addEventListener('click', stopWebcam);
    rotateLeftBtn.addEventListener('click', () => rotateCanvas(-90));
    rotateRightBtn.addEventListener('click', () => rotateCanvas(90));
    cropToggleBtn.addEventListener('click', enterCropMode);
    applyCropBtn.addEventListener('click', applyCrop);
    cancelCropBtn.addEventListener('click', exitCropMode);
    extractBtn.addEventListener('click', submitOCR);
    ocrTranslateBtn.addEventListener('click', submitOCRTranslation);
    editCanvas.addEventListener('mousedown', onCropMouseDown);
    editCanvas.addEventListener('mousemove', onCropMouseMove);
    editCanvas.addEventListener('mouseup',   onCropMouseUp);
    editCanvas.addEventListener('mouseleave', onCropMouseUp);
    extractedText.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            submitOCRTranslation();
        }
    });

    // ── Helpers ──

    function showImageMessage(message, isError) {
        imageFilename.textContent = message;
        imageFilename.classList.toggle('error', Boolean(isError));
    }

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

    /** Draw an image URL into editCanvas, then show the preview and tools. */
    function loadImageToCanvas(url, label) {
        const img = new Image();
        img.onload = () => {
            editCanvas.width  = img.naturalWidth;
            editCanvas.height = img.naturalHeight;
            editCanvas.getContext('2d').drawImage(img, 0, 0);
            URL.revokeObjectURL(url);
            imagePreviewContainer.hidden = false;
            extractBtn.disabled = false;
            clearOCROutput();
        };
        img.src = url;
        showImageMessage(label, false);
    }

    /** Wrap canvas.toBlob in a Promise for use with await. */
    function canvasToBlob() {
        return new Promise((resolve) => editCanvas.toBlob(resolve, 'image/jpeg', 0.92));
    }

    /**
     * Map a mouse event's client coordinates to canvas pixel coordinates,
     * accounting for any CSS scaling applied to the canvas element.
     */
    function clientToCanvas(e) {
        const r = editCanvas.getBoundingClientRect();
        return {
            x: Math.round((e.clientX - r.left) * editCanvas.width  / r.width),
            y: Math.round((e.clientY - r.top)  * editCanvas.height / r.height),
        };
    }

    // ── File selection ──

    function handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!ALLOWED_TYPES.includes(file.type)) {
            showImageMessage('Unsupported file type. Use JPEG, PNG, WEBP, or HEIC.', true);
            extractBtn.disabled = true;
            return;
        }
        if (file.size > MAX_IMAGE_BYTES) {
            showImageMessage('Image too large. Maximum size is 15 MB.', true);
            extractBtn.disabled = true;
            return;
        }

        loadImageToCanvas(URL.createObjectURL(file), file.name);
    }

    // ── Webcam ──

    async function openWebcam() {
        try {
            webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            webcamVideo.srcObject = webcamStream;
            webcamSection.hidden = false;
            chooseImageBtn.disabled = true;
            webcamBtn.disabled = true;
        } catch (err) {
            showImageMessage('Camera unavailable: ' + err.message, true);
        }
    }

    function stopWebcam() {
        if (webcamStream) {
            webcamStream.getTracks().forEach((t) => t.stop());
            webcamStream = null;
        }
        webcamVideo.srcObject = null;
        webcamSection.hidden = true;
        chooseImageBtn.disabled = false;
        webcamBtn.disabled = false;
    }

    function captureFromWebcam() {
        if (!webcamStream) return;
        editCanvas.width  = webcamVideo.videoWidth;
        editCanvas.height = webcamVideo.videoHeight;
        editCanvas.getContext('2d').drawImage(webcamVideo, 0, 0);
        stopWebcam();
        imagePreviewContainer.hidden = false;
        extractBtn.disabled = false;
        showImageMessage('Webcam capture', false);
        clearOCROutput();
    }

    // ── Rotation ──

    function rotateCanvas(degrees) {
        const dataUrl = editCanvas.toDataURL();
        const img = new Image();
        img.onload = () => {
            const rad  = degrees * Math.PI / 180;
            const is90 = Math.abs(degrees) % 180 !== 0;
            const newW = is90 ? editCanvas.height : editCanvas.width;
            const newH = is90 ? editCanvas.width  : editCanvas.height;
            const tmp  = document.createElement('canvas');
            tmp.width  = newW;
            tmp.height = newH;
            const ctx  = tmp.getContext('2d');
            ctx.translate(newW / 2, newH / 2);
            ctx.rotate(rad);
            ctx.drawImage(img, -editCanvas.width / 2, -editCanvas.height / 2);
            editCanvas.width  = newW;
            editCanvas.height = newH;
            editCanvas.getContext('2d').drawImage(tmp, 0, 0);
        };
        img.src = dataUrl;
    }

    // ── Crop ──

    function enterCropMode() {
        isCropping     = true;
        cropStart      = null;
        cropRect       = null;
        savedImageData = editCanvas.getContext('2d')
            .getImageData(0, 0, editCanvas.width, editCanvas.height);
        editCanvas.style.cursor  = 'crosshair';
        cropToggleBtn.hidden     = true;
        applyCropBtn.hidden      = false;
        cancelCropBtn.hidden     = false;
        rotateLeftBtn.disabled   = true;
        rotateRightBtn.disabled  = true;
    }

    function exitCropMode() {
        if (savedImageData) {
            // Restore the clean image (cancelling any in-progress drag overlay).
            editCanvas.getContext('2d').putImageData(savedImageData, 0, 0);
            savedImageData = null;
        }
        isCropping               = false;
        cropStart                = null;
        cropRect                 = null;
        editCanvas.style.cursor  = '';
        cropToggleBtn.hidden     = false;
        applyCropBtn.hidden      = true;
        cancelCropBtn.hidden     = true;
        rotateLeftBtn.disabled   = false;
        rotateRightBtn.disabled  = false;
    }

    function renderCropOverlay() {
        if (!savedImageData || !cropRect || cropRect.w < 2 || cropRect.h < 2) return;
        const { x, y, w, h } = cropRect;
        const ctx = editCanvas.getContext('2d');
        // Restore clean image, then draw the dimmed overlay + bright selection.
        ctx.putImageData(savedImageData, 0, 0);
        ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
        ctx.fillRect(0, 0, editCanvas.width, editCanvas.height);
        // Punch through to the original image inside the selection.
        ctx.putImageData(savedImageData, 0, 0, x, y, w, h);
        // Selection border — scale lineWidth to stay 1 CSS pixel wide.
        const scale = editCanvas.width / editCanvas.getBoundingClientRect().width;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth   = Math.max(1, scale);
        ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    }

    function onCropMouseDown(e) {
        if (!isCropping) return;
        cropStart = clientToCanvas(e);
        cropRect  = null;
        e.preventDefault();
    }

    function onCropMouseMove(e) {
        if (!isCropping || !cropStart) return;
        const pos = clientToCanvas(e);
        cropRect = {
            x: Math.min(cropStart.x, pos.x),
            y: Math.min(cropStart.y, pos.y),
            w: Math.abs(pos.x - cropStart.x),
            h: Math.abs(pos.y - cropStart.y),
        };
        renderCropOverlay();
    }

    function onCropMouseUp(e) {
        if (!isCropping || !cropStart) return;
        cropStart = null;
        e.preventDefault();
    }

    function applyCrop() {
        if (!cropRect || cropRect.w < 10 || cropRect.h < 10) {
            exitCropMode();
            return;
        }
        const { x, y, w, h } = cropRect;
        const ctx = editCanvas.getContext('2d');

        // Restore the clean image before extracting the region.
        ctx.putImageData(savedImageData, 0, 0);
        savedImageData = null; // prevent exitCropMode() from restoring over our result

        const cropped = document.createElement('canvas');
        cropped.width  = w;
        cropped.height = h;
        cropped.getContext('2d').drawImage(editCanvas, x, y, w, h, 0, 0, w, h);

        editCanvas.width  = w;
        editCanvas.height = h;
        ctx.drawImage(cropped, 0, 0);

        exitCropMode();
    }

    // ── OCR submission ──

    async function submitOCR() {
        extractBtn.disabled = true;
        ocrStatus.hidden    = false;
        clearOCROutput();

        const blob = await canvasToBlob();
        if (!blob) {
            showImageMessage('Failed to process image.', true);
            extractBtn.disabled = false;
            ocrStatus.hidden    = true;
            return;
        }

        try {
            const formData = new FormData();
            formData.append('image', blob, 'image.jpg');
            const response = await fetch('/ocr', { method: 'POST', body: formData });
            const data = await response.json();

            if (response.ok) {
                extractedText.value      = data.extracted_text;
                extractedText.disabled   = false;
                ocrTranslateBtn.disabled = false;

                const labelToClass = {
                    'Good':                   'conf-good',
                    'Fair':                   'conf-fair',
                    'Poor':                   'conf-poor',
                    'Low — review carefully': 'conf-low',
                };
                const cls = labelToClass[data.confidence_label];
                if (cls) confidenceBadge.classList.add(cls);
                confidenceBadge.textContent = data.confidence >= 0
                    ? `${data.confidence_label} (${data.confidence}%)`
                    : data.confidence_label;
                confidenceBadge.hidden = false;

                if (data.warning) {
                    ocrWarning.textContent = data.warning;
                    ocrWarning.hidden = false;
                }
            } else {
                showImageMessage(data.error || data.detail || 'Text extraction failed.', true);
            }
        } catch (err) {
            showImageMessage('Could not reach the server. Is the app running?', true);
        } finally {
            extractBtn.disabled = false;
            ocrStatus.hidden    = true;
        }
    }

    // ── Translation of extracted text ──

    async function submitOCRTranslation() {
        const text = extractedText.value.trim();
        if (!text) return;

        ocrTranslateBtn.disabled  = true;
        ocrStatusTranslate.hidden = false;
        ocrOutputArea.hidden      = true;
        ocrTranslationText.textContent = '';
        ocrModelInfo.textContent  = '';

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
                ocrTranslationText.textContent = data.error || data.detail || 'Translation failed.';
                ocrTranslationText.classList.add('error');
            }
            ocrOutputArea.hidden = false;
        } catch (err) {
            ocrTranslationText.textContent = 'Could not reach the server. Is the app running?';
            ocrTranslationText.classList.add('error');
            ocrOutputArea.hidden = false;
        } finally {
            ocrTranslateBtn.disabled  = false;
            ocrStatusTranslate.hidden = true;
        }
    }
});
