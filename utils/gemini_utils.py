# visual_content_analyzer/utils/gemini_utils.py

import google.generativeai as google_genai_sdk
from google.generativeai import types as google_genai_types
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
        google_genai_sdk.configure(api_key=api_key)
        _GEMINI_CLIENT = google_genai_sdk
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

    # Get the model
    model = client.GenerativeModel(model_id)
    
    # Prepare generation config if provided
    generation_config = None
    if generation_config_params:
        generation_config = google_genai_types.GenerationConfig(**generation_config_params)

    try:
        # Generate content with the model
        response = model.generate_content([img, prompt_text], generation_config=generation_config)
        
        if hasattr(response, 'text'):
            return response.text
        else:
            # Handle different response formats
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"Content blocked by API. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
            # Check for candidates and parts if text is not directly available
            if hasattr(response, 'candidates') and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
            return "Gemini API returned a response without direct text and no explicit error. Check response parts."

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

# [end of utils/gemini_utils.py]
