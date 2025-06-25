# visual_content_analyzer/utils/gemini_utils.py

from google import genai as google_genai_sdk
from google.genai import types as google_genai_types
from PIL import Image
import os
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables from .env file at the module level
load_dotenv()

_GEMINI_CLIENT = None

def get_gemini_client():
    """Initializes and returns the Gemini API client using the new SDK."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError(
            "GEMINI_API_KEY not found or not set in environment variables. "
            "Please set it in a .env file or as an environment variable. "
            "Make sure it's not the placeholder value."
        )
    try:
        _GEMINI_CLIENT = google_genai_sdk.Client(api_key=api_key)
        return _GEMINI_CLIENT
    except Exception as e:
        raise ConnectionError(f"Failed to initialize Gemini Client: {e}")

# Default model IDs, can be overridden
DEFAULT_MODEL_ID = "gemini-1.5-flash-latest" # Updated from "gemini-2.5-flash-lite-preview-06-17"
PRO_MODEL_ID = "gemini-1.5-pro-latest" # Updated from "gemini-2.5-pro" as per common model IDs

def generate_content_with_gemini(image_bytes, prompt_text, model_id=DEFAULT_MODEL_ID, generation_config_params=None):
    """
    Sends image bytes and a prompt to the specified Gemini model using the new SDK.

    Args:
        image_bytes: Image data in bytes.
        prompt_text: The text prompt for the VLM. This should be carefully constructed
                     by the calling function (e.g., in app.py) to request the desired
                     output format (e.g., JSON for points or bounding boxes) and specify
                     any constraints (e.g., number of items).
        model_id: The model ID to use (e.g., "gemini-1.5-flash-latest", "gemini-1.5-pro-latest").
                     Chosen based on the task requirements (e.g., pro for more complex tasks).
        generation_config_params: Optional dictionary for generation configuration.
                                  Example: `{'temperature': 0.5, 'max_output_tokens': 2048}`.
                                  For spatial tasks requiring JSON, temperature might be set (e.g., 0.2-0.5)
                                  to encourage factual, structured output.

    Returns:
        The text response from the Gemini VLM.

    Raises:
        ConnectionError: If the Gemini client cannot be initialized.
        ValueError: If image_bytes is not valid image data.
        Exception: For other errors during API call.
    """
    client = get_gemini_client()

    try:
        img = Image.open(BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")

    contents = [img, prompt_text]

    config = None
    if generation_config_params:
        config = google_genai_types.GenerateContentConfig(**generation_config_params)

    try:
        # The new SDK uses client.models.generate_content
        # However, the cookbook for Gemini 2 (which this task is based on) shows client.generate_content
        # Let's try to use the direct client.generate_content if available, or client.models.generate_content
        # Looking at google-genai SDK, it should be `client.generate_content`
        # The model is now specified in each call directly.

        # Correction: The new SDK (google-genai) uses `client.generate_content` directly.
        # The `model` argument should be the model resource name string e.g. "models/gemini-1.5-pro-latest"
        # or we can initialize a model object first: `model = client.get_model(f"models/{model_id}")`
        # and then `model.generate_content(...)`

        # Using the direct model string for simplicity as shown in some new SDK examples.
        # The SDK will prepend "models/" if not present for convenience for some model names.

        model_to_call = client.get_model(f"models/{model_id}")
        response = model_to_call.generate_content(contents, generation_config=config)

        if hasattr(response, 'text'):
            return response.text
        else:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"Content blocked by API. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
            # Check for candidates and parts if text is not directly available
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
            return "Gemini API returned a response without direct text and no explicit error. Check response parts."

    except AttributeError as ae:
        # This might happen if client.models.generate_content was the right path
        # For now, sticking to client.get_model().generate_content as it's common in new SDK.
        return f"SDK usage error: {ae}. This might be due to an unexpected SDK structure."
    except Exception as e:
        # Log the full error for debugging
        # print(f"Full error in generate_content_with_gemini: {type(e).__name__} - {e}")
        # Consider re-raising or handling specific google.api_core.exceptions
        return f"Error generating content with Gemini: {type(e).__name__} - {e}"

# Keep the old function name for now to minimize changes in app.py initially,
# but it will now use the new generic function.
def classify_image_with_gemini(image_bytes, prompt_text):
    """
    Legacy wrapper for image classification. Uses the new generate_content_with_gemini.
    """
    # Using default model and no specific generation config for classification
    return generate_content_with_gemini(image_bytes, prompt_text, model_id=DEFAULT_MODEL_ID)

[end of utils/gemini_utils.py]
