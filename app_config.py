# app_config.py

# Analysis types offered by the application
analysis_types = [
    "Image Classification",
    "Point to Items",
    "2D Bounding Boxes",
    "Segmentation Masks",
    "3D Bounding Boxes"
]

# Default user-facing prompts for each analysis type
user_prompts = {
    "Image Classification": "Describe the main objects in this image and categorize it (e.g., dog, cat, cow).",
    "Point to Items": "Example: find all the dogs in the image and point to them.",
    "2D Bounding Boxes": "Example: find all the dogs in the image",
    "Segmentation Masks": "Segment the main objects in this image and provide their masks and labels.",
    "3D Bounding Boxes": "Detect the 3D bounding boxes of the main objects in the image."
}

# Detailed JSON format specifications for the model, appended to the user's prompt
json_format_specs = {
    "Image Classification": "Return just one word as output.",
    "Point to Items": "Point to no more than 10 items in the image. Include their labels. The answer should follow the json format: [{\"point\": [y, x], \"label\": \"description\"}, ...]. Points are normalized to 0-1000. IMPORTANT: The coordinates should be in a flat array [y, x], not as separate objects. Return ONLY valid JSON without any additional text or markdown formatting.",
    "2D Bounding Boxes": "Detect the relevant objects in this image and provide their 2D bounding boxes and labels. The answer should follow the json format: [{\"box_2d\": [ymin, xmin, ymax, xmax], \"label\": \"description\"}, ...]. Coordinates are normalized to 0-1. IMPORTANT: The coordinates should be in a flat array [ymin, xmin, ymax, xmax], not as separate objects with properties. Return ONLY valid JSON without any additional text or markdown formatting.",
    "Segmentation Masks": "Detect and segment objects. Each object should have a 'label' and a 'mask'. The 'mask' is a list of polygons, where each polygon is a flat list of alternating x, y coordinates normalized to 0-1000 (e.g., [x1, y1, x2, y2, ..., xn, yn]). Example: [{'label': 'sky', 'mask': [[x1,y1,x2,y2,x3,y3,x1,y1]]}, {'label': 'tree', 'mask': [[x1,y1,x2,y2,...], [xa1,ya1,xa2,ya2,...]]}]. IMPORTANT: X and Y coordinates are alternating in the flat list for each polygon. Return ONLY valid JSON without any additional text or markdown formatting.",
    "3D Bounding Boxes": "Output a json list where each entry contains the object name in \"label\" and its 3D bounding box in \"box_3d\": [x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw]. Return ONLY valid JSON without any additional text or markdown formatting."
}

# Help text displayed to the user for the prompt input field
prompt_help_text = {
    "Image Classification": "Examples: 'What objects are in this image?', 'Is this image related to nature or urban environments?'",
    "Point to Items": "Clearly describe what items to point to, or ask for general items. The JSON format will be automatically added.",
    "2D Bounding Boxes": "Specify if you want all objects or specific ones. The JSON format will be automatically added.",
    "Segmentation Masks": "Describe the objects to segment. The JSON format will be automatically added.",
    "3D Bounding Boxes": "Specify the objects of interest. The JSON format will be automatically added."
}

# Other global settings
TEMP_DIR_NAME = "temp_uploaded_images" # Name of the temporary directory for uploads
DEFAULT_GEMINI_MODEL = "gemini-1.0-pro-vision-latest" # Default model for most tasks
PRO_GEMINI_MODEL = "gemini-1.5-pro-latest" # Pro model, potentially for more complex tasks

# Environment variable names (optional, but good for centralizing)
ENV_VAR_API_KEY = "GEMINI_API_KEY"
ENV_VAR_SHOW_JSON_SPECS = "SHOW_JSON_FORMAT_SPECS"
ENV_VAR_SHOW_FULL_PROMPT = "SHOW_FULL_PROMPT"
