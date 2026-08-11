from langbot_unified_pipeline.vision import run_vision_with_fallback, sanitize_vision_text


def test_refusal_and_upload_instructions_are_rejected():
    assert sanitize_vision_text("I cannot see the image. Please upload the image.") == ""


def test_prompt_echo_is_rejected():
    prompt = "Describe visible objects layout relationships and all readable text"
    assert sanitize_vision_text(prompt, prompt) == ""


def test_invalid_primary_uses_valid_fallback():
    result = run_vision_with_fallback(
        b"image",
        "image/png",
        "Describe the visible object and text",
        lambda _data, _mime, _prompt: "Please upload the image",
        lambda _data, _mime, _prompt: "A red square with the text PUBLIC_TEST_ALPHA.",
    )
    assert result == "A red square with the text PUBLIC_TEST_ALPHA."


def test_empty_and_invalid_fallback_return_empty():
    result = run_vision_with_fallback(
        b"image",
        "image/png",
        "Describe the image",
        lambda *_args: "",
        lambda *_args: "I cannot see the image",
    )
    assert result == ""
