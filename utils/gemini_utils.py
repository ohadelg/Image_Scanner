# visual_content_analyzer/utils/gemini_utils.py

import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables from .env file at the module level
# This ensures that other functions in this module can assume `genai` is configured if `configure_gemini` was called.
load_dotenv()

_GEMINI_API_KEY_CONFIGURED = False

def configure_model():
    """Configures the Gemini API with the API key from environment variables."""
    global _GEMINI_API_KEY_CONFIGURED
    if _GEMINI_API_KEY_CONFIGURED:
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError(
            "API_KEY not found or not set in environment variables. "
            "Please set it in a .env file or as an environment variable. "
            "Make sure it's not the placeholder value."
        )
    try:
        genai.configure(api_key=api_key)
        _GEMINI_API_KEY_CONFIGURED = True
    except Exception as e:
        raise ConnectionError(f"Failed to configure Gemini API: {e}")


def get_vision_model():
    """
    Returns the Gemini 2.5 Flash Lite Preview model.
    """
    return genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')


def classify_image_with_gemini(image_bytes, prompt_text):
    """
    Sends image bytes and a prompt to the Gemini VLM for classification.

    Args:
        image_bytes: Image data in bytes (e.g., from st.file_uploader or reading a file in binary mode).
        prompt_text: The text prompt for the VLM.

    Returns:
        The text response from the Gemini VLM.

    Raises:
        ConnectionError: If the Gemini API is not configured or model cannot be fetched.
        ValueError: If image_bytes is not valid image data.
        Exception: For other errors during API call.
    """
    model = get_vision_model() # This will also ensure configuration

    try:
        # PIL.Image.open can handle BytesIO directly
        img = Image.open(BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")

    # For image classification, Gemini's generate_content takes a list of parts.
    # The first part is the image, the second is the text prompt.
    contents = [img, prompt_text]

    try:
        response = model.generate_content(contents)
        # It's good practice to check if 'text' attribute exists,
        # though for gemini-pro-vision, it typically does on success.
        if hasattr(response, 'text'):
            return response.text
        else:
            # If no 'text' but also no error, the response might be structured differently
            # or blocked. It's safer to return a string indicating this.
            # You might want to log response.parts or response.prompt_feedback for debugging.
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"Content blocked by API. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
            return "Gemini API returned a response without text and no explicit error."

    except Exception as e:
        # More specific error handling can be added here if needed
        # For example, handling specific API errors from google.generativeai.types.generation_types.BlockedPromptException
        return f"Error classifying image with Gemini: {e}"
