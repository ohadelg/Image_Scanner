# app_config.py

# --- Global Variables & Setup ---
TEMP_DIR = "temp_uploaded_images"

# --- Analysis Configuration ---
ANALYSIS_TYPES = [
    "Image Classification",
    "Point to Items",
    "2D Bounding Boxes",
    "Segmentation Masks",
    "3D Bounding Boxes"
]

# Default user-facing prompts for each analysis type
USER_PROMPTS = {
    "Image Classification": "Describe the main objects in this image and categorize it (e.g., dog, cat, cow).",
    "Point to Items": "Example: find all the dogs in the image and point to them.",
    "2D Bounding Boxes": "Example: find all the dogs in the image",
    "Segmentation Masks": "Segment the main objects in this image and provide their masks and labels.",
    "3D Bounding Boxes": "Detect the 3D bounding boxes of the main objects in the image."
}

# JSON format specifications that get automatically added to the prompt by the application
JSON_FORMAT_SPECS = {
    "Image Classification": "Return just one word as output.",
    "Point to Items": "Point to no more than 10 items in the image. Include their labels. The answer should follow the json format: [{\"point\": [y, x], \"label\": \"description\"}, ...]. Points are normalized to 0-1000. IMPORTANT: The coordinates should be in a flat array [y, x], not as separate objects. Return ONLY valid JSON without any additional text or markdown formatting.",
    "2D Bounding Boxes": "Detect the relevant objects in this image and provide their 2D bounding boxes and labels. The answer should follow the json format: [{\"box_2d\": [ymin, xmin, ymax, xmax], \"label\": \"description\"}, ...]. Coordinates are normalized to 0-1. IMPORTANT: The coordinates should be in a flat array [ymin, xmin, ymax, xmax], not as separate objects with properties. Return ONLY valid JSON without any additional text or markdown formatting.",
    "Segmentation Masks": "The answer should follow the json format: [{\"mask\": [coordinates], \"label\": \"description\"}, ...]. (Further details needed on expected JSON format for masks) Return ONLY valid JSON without any additional text or markdown formatting.",
    "3D Bounding Boxes": "Output a json list where each entry contains the object name in \"label\" and its 3D bounding box in \"box_3d\": [x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw]. Return ONLY valid JSON without any additional text or markdown formatting."
}

# Help text for the prompt input field
PROMPT_HELP_TEXT = {
    "Image Classification": "Examples: 'What objects are in this image?', 'Is this image related to nature or urban environments?'",
    "Point to Items": "Clearly describe what items to point to, or ask for general items. The JSON format will be automatically added.",
    "2D Bounding Boxes": "Specify if you want all objects or specific ones. The JSON format will be automatically added.",
    "Segmentation Masks": "Describe the objects to segment. The JSON format will be automatically added.",
    "3D Bounding Boxes": "Specify the objects of interest. The JSON format will be automatically added."
}

# DEFAULT_PROMPT_TEXT was found to be unused after refactoring app.py's prompt construction.
# The initial value for the prompt_text text_area is taken directly from USER_PROMPTS.
# The full_prompt sent to the model is constructed in app.py by combining the
# current prompt_text (from the text_area) and the relevant JSON_FORMAT_SPECS.
