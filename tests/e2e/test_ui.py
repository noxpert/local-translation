"""Playwright E2E tests for the Hungarian Reading Assistant UI.

All calls to /translate and /ocr are intercepted via page.route() so no
running Ollama instance is required. The live app server (including real
Tesseract) is started by the session-scoped fixture in conftest.py.
"""

import io
import json

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Page, expect

# ── Mock response payloads ────────────────────────────────────────────────────

MOCK_TRANSLATION = {
    "translation": "Good morning, I wish you!",
    "model": "test-model",
    "source_text": "Jó reggelt kívánok!",
}

MOCK_OCR_GOOD = {
    "extracted_text": "Jó reggelt kívánok!",
    "confidence": 93.5,
    "confidence_label": "Good",
    "warning": None,
}

MOCK_OCR_LOW = {
    "extracted_text": "blurry unreadable text",
    "confidence": 55.0,
    "confidence_label": "Low — review carefully",
    "warning": "OCR confidence is low. Review the text carefully before translating.",
}

MOCK_TRANSLATE_ERROR = {
    "error": "Ollama is not reachable or timed out at http://localhost:11434",
    "detail": "",
}

MOCK_OCR_ERROR = {
    "error": "Tesseract is not installed or not on PATH. Run: brew install tesseract",
    "detail": "",
}


def _mock_png() -> bytes:
    """Tiny PNG for file-upload tests — no disk file needed."""
    img = Image.new("RGB", (300, 80), "white")
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((10, 20), "Hello Test", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _route_translate(page: Page, payload: dict = MOCK_TRANSLATION, status: int = 200):
    page.route(
        "**/translate",
        lambda r: r.fulfill(
            status=status,
            content_type="application/json",
            body=json.dumps(payload),
        ),
    )


def _route_ocr(page: Page, payload: dict = MOCK_OCR_GOOD, status: int = 200):
    page.route(
        "**/ocr",
        lambda r: r.fulfill(
            status=status,
            content_type="application/json",
            body=json.dumps(payload),
        ),
    )


# ── Mode toggle ───────────────────────────────────────────────────────────────


def test_default_mode_is_text(app_page: Page):
    expect(app_page.locator("#phase1")).to_be_visible()
    expect(app_page.locator("#phase2")).to_be_hidden()


def test_toggle_switches_to_image_mode(app_page: Page):
    app_page.click("#modeToggleBtn")
    expect(app_page.locator("#phase2")).to_be_visible()
    expect(app_page.locator("#phase1")).to_be_hidden()
    expect(app_page.locator("#modeSubtitle")).to_have_text("Mode: Image OCR")


def test_toggle_back_restores_text_mode(app_page: Page):
    app_page.click("#modeToggleBtn")  # → image
    app_page.click("#modeToggleBtn")  # → text
    expect(app_page.locator("#phase1")).to_be_visible()
    expect(app_page.locator("#phase2")).to_be_hidden()
    expect(app_page.locator("#modeSubtitle")).to_have_text("Mode: Typed Text")


def test_toggle_preserves_typed_text(app_page: Page):
    app_page.fill("#hungarianInput", "Jó reggelt!")
    app_page.click("#modeToggleBtn")  # → image
    app_page.click("#modeToggleBtn")  # → text
    expect(app_page.locator("#hungarianInput")).to_have_value("Jó reggelt!")


# ── Typed-text translation ────────────────────────────────────────────────────


def test_translate_button_produces_result(app_page: Page):
    _route_translate(app_page)
    app_page.fill("#hungarianInput", "Jó reggelt kívánok!")
    app_page.click("#translateBtn")
    expect(app_page.locator("#translationText")).to_contain_text(
        MOCK_TRANSLATION["translation"]
    )


def test_translate_keyboard_shortcut(app_page: Page):
    _route_translate(app_page)
    app_page.fill("#hungarianInput", "Jó reggelt kívánok!")
    app_page.locator("#hungarianInput").press("Control+Enter")
    expect(app_page.locator("#translationText")).to_be_visible()
    expect(app_page.locator("#translationText")).to_contain_text(
        MOCK_TRANSLATION["translation"]
    )


def test_translate_button_disabled_during_request(app_page: Page):
    # Use a slow route so we can observe the disabled state mid-flight.
    def slow_route(route):
        app_page.wait_for_timeout(200)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(MOCK_TRANSLATION),
        )

    app_page.route("**/translate", slow_route)
    app_page.fill("#hungarianInput", "Jó reggelt!")
    app_page.click("#translateBtn")
    # Button should be disabled while the request is in flight.
    expect(app_page.locator("#translateBtn")).to_be_disabled()
    # After the response arrives it should re-enable.
    expect(app_page.locator("#translateBtn")).to_be_enabled()


def test_translate_spinner_appears_and_disappears(app_page: Page):
    _route_translate(app_page)
    app_page.fill("#hungarianInput", "Helló!")
    # Spinner hidden before click.
    expect(app_page.locator("#statusArea")).to_be_hidden()
    app_page.click("#translateBtn")
    # After response, spinner is hidden again.
    expect(app_page.locator("#statusArea")).to_be_hidden()
    expect(app_page.locator("#outputArea")).to_be_visible()


def test_translate_output_clears_on_input_edit(app_page: Page):
    _route_translate(app_page)
    app_page.fill("#hungarianInput", "Jó reggelt!")
    app_page.click("#translateBtn")
    expect(app_page.locator("#outputArea")).to_be_visible()
    # Editing the input should clear the result.
    app_page.fill("#hungarianInput", "Más szöveg")
    expect(app_page.locator("#outputArea")).to_be_hidden()


def test_translate_error_response_is_styled_as_error(app_page: Page):
    _route_translate(app_page, payload=MOCK_TRANSLATE_ERROR, status=503)
    app_page.fill("#hungarianInput", "Helló!")
    app_page.click("#translateBtn")
    error_el = app_page.locator("#translationText")
    expect(error_el).to_be_visible()
    expect(error_el).to_have_class("error")
    expect(error_el).to_contain_text("Ollama")


def test_translate_model_name_shown_in_footer(app_page: Page):
    _route_translate(app_page)
    app_page.fill("#hungarianInput", "Jó reggelt!")
    app_page.click("#translateBtn")
    expect(app_page.locator("#modelInfo")).to_contain_text("test-model")


# ── Image OCR mode ────────────────────────────────────────────────────────────


def _switch_to_image(page: Page):
    page.click("#modeToggleBtn")
    expect(page.locator("#phase2")).to_be_visible()


def _upload_image(page: Page):
    page.locator("#imageInput").set_input_files(
        files=[{"name": "test.png", "mimeType": "image/png", "buffer": _mock_png()}]
    )


def test_extract_button_disabled_before_image(app_page: Page):
    _switch_to_image(app_page)
    expect(app_page.locator("#extractBtn")).to_be_disabled()


def test_choose_image_enables_extract_button(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    expect(app_page.locator("#imagePreviewContainer")).to_be_visible()
    expect(app_page.locator("#extractBtn")).to_be_enabled()


def test_ocr_extract_shows_confidence_badge(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    expect(app_page.locator("#confidenceBadge")).to_be_visible()
    expect(app_page.locator("#confidenceBadge")).to_contain_text("Good")
    expect(app_page.locator("#confidenceBadge")).to_contain_text("93.5%")


def test_ocr_extract_populates_editable_textarea(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    text_area = app_page.locator("#extractedText")
    expect(text_area).to_be_enabled()
    expect(text_area).to_have_value(MOCK_OCR_GOOD["extracted_text"])


def test_ocr_low_confidence_shows_warning(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page, payload=MOCK_OCR_LOW)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    expect(app_page.locator("#ocrWarning")).to_be_visible()
    expect(app_page.locator("#ocrWarning")).to_contain_text("Review")


def test_ocr_extract_spinner_appears_and_disappears(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _upload_image(app_page)
    expect(app_page.locator("#ocrStatus")).to_be_hidden()
    app_page.click("#extractBtn")
    expect(app_page.locator("#ocrStatus")).to_be_hidden()
    expect(app_page.locator("#confidenceBadge")).to_be_visible()


def test_ocr_translate_button_enabled_after_extraction(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _upload_image(app_page)
    expect(app_page.locator("#ocrTranslateBtn")).to_be_disabled()
    app_page.click("#extractBtn")
    expect(app_page.locator("#ocrTranslateBtn")).to_be_enabled()


def test_ocr_full_flow_extract_then_translate(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _route_translate(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    expect(app_page.locator("#ocrTranslateBtn")).to_be_enabled()
    app_page.click("#ocrTranslateBtn")
    expect(app_page.locator("#ocrOutputArea")).to_be_visible()
    expect(app_page.locator("#ocrTranslationText")).to_contain_text(
        MOCK_TRANSLATION["translation"]
    )


def test_ocr_translate_spinner_appears_and_disappears(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _route_translate(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    expect(app_page.locator("#ocrStatusTranslate")).to_be_hidden()
    app_page.click("#ocrTranslateBtn")
    expect(app_page.locator("#ocrStatusTranslate")).to_be_hidden()
    expect(app_page.locator("#ocrOutputArea")).to_be_visible()


def test_ocr_translate_keyboard_shortcut(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _route_translate(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    # Wait for OCR to complete and enable the textarea before pressing the shortcut.
    expect(app_page.locator("#extractedText")).to_be_enabled()
    app_page.locator("#extractedText").press("Control+Enter")
    expect(app_page.locator("#ocrOutputArea")).to_be_visible()


def test_ocr_second_translation_replaces_first(app_page: Page):
    """Re-translating clears the previous result and shows the new one."""
    _switch_to_image(app_page)
    _route_ocr(app_page)
    _upload_image(app_page)
    app_page.click("#extractBtn")

    first = {**MOCK_TRANSLATION, "translation": "First result"}
    app_page.route(
        "**/translate",
        lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(first),
        ),
    )
    app_page.click("#ocrTranslateBtn")
    expect(app_page.locator("#ocrTranslationText")).to_contain_text("First result")

    second = {**MOCK_TRANSLATION, "translation": "Second result"}
    app_page.route(
        "**/translate",
        lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(second),
        ),
    )
    app_page.click("#ocrTranslateBtn")
    expect(app_page.locator("#ocrTranslationText")).to_contain_text("Second result")
    expect(app_page.locator("#ocrTranslationText")).not_to_contain_text("First result")


def test_ocr_error_response_is_shown(app_page: Page):
    _switch_to_image(app_page)
    _route_ocr(app_page, payload=MOCK_OCR_ERROR, status=503)
    _upload_image(app_page)
    app_page.click("#extractBtn")
    expect(app_page.locator("#imageFilename")).to_contain_text("Tesseract")


# ── Image editing toolbar ─────────────────────────────────────────────────────


def test_edit_toolbar_hidden_before_image(app_page: Page):
    _switch_to_image(app_page)
    expect(app_page.locator("#imagePreviewContainer")).to_be_hidden()


def test_edit_toolbar_visible_after_image_loaded(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    expect(app_page.locator("#imageEditToolbar")).to_be_visible()
    expect(app_page.locator("#rotateLeftBtn")).to_be_visible()
    expect(app_page.locator("#rotateRightBtn")).to_be_visible()
    expect(app_page.locator("#cropToggleBtn")).to_be_visible()


def test_crop_mode_shows_apply_and_cancel(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    expect(app_page.locator("#applyCropBtn")).to_be_hidden()
    expect(app_page.locator("#cancelCropBtn")).to_be_hidden()
    app_page.click("#cropToggleBtn")
    expect(app_page.locator("#applyCropBtn")).to_be_visible()
    expect(app_page.locator("#cancelCropBtn")).to_be_visible()
    expect(app_page.locator("#cropToggleBtn")).to_be_hidden()


def test_crop_cancel_restores_toolbar(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    app_page.click("#cropToggleBtn")
    app_page.click("#cancelCropBtn")
    expect(app_page.locator("#cropToggleBtn")).to_be_visible()
    expect(app_page.locator("#applyCropBtn")).to_be_hidden()


def test_rotate_buttons_disabled_in_crop_mode(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    app_page.click("#cropToggleBtn")
    expect(app_page.locator("#rotateLeftBtn")).to_be_disabled()
    expect(app_page.locator("#rotateRightBtn")).to_be_disabled()


def test_rotate_buttons_re_enabled_after_crop_cancel(app_page: Page):
    _switch_to_image(app_page)
    _upload_image(app_page)
    app_page.click("#cropToggleBtn")
    app_page.click("#cancelCropBtn")
    expect(app_page.locator("#rotateLeftBtn")).to_be_enabled()
    expect(app_page.locator("#rotateRightBtn")).to_be_enabled()


# ── Webcam button ─────────────────────────────────────────────────────────────


def test_webcam_button_is_visible_in_image_mode(app_page: Page):
    _switch_to_image(app_page)
    expect(app_page.locator("#webcamBtn")).to_be_visible()
