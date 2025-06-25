# visual_content_analyzer/utils/visualization_utils.py

import json
import base64
from io import BytesIO
from PIL import Image

def parse_gemini_json_output(json_output_str: str) -> dict | list | None:
    """
    Parses JSON output from Gemini, which may be wrapped in markdown code blocks.
    Handles potential errors during parsing.
    """
    if not json_output_str:
        return None

    # Remove markdown fencing if present
    cleaned_str = json_output_str.strip()
    if cleaned_str.startswith("```json"):
        cleaned_str = cleaned_str[7:] # Remove ```json
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3] # Remove ```
    elif cleaned_str.startswith("```"): # Less specific, but might occur
        cleaned_str = cleaned_str[3:]
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3]

    cleaned_str = cleaned_str.strip()

    try:
        return json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        # print(f"JSONDecodeError: {e} in string: '{cleaned_str[:200]}...'") # For debugging
        # Attempt to fix common issues like trailing commas (though json.loads is strict)
        # Python's eval is unsafe, so not using it.
        # For now, just return None or raise a custom error.
        # Consider more sophisticated cleaning if this becomes a frequent issue.
        # A common issue is if the model returns multiple JSON objects or text alongside JSON.
        # This parser expects a single, potentially fenced, JSON object/array.
        return None # Or raise ValueError(f"Failed to parse JSON: {e}. Content: {cleaned_str[:200]}...")


def pil_to_base64(pil_image: Image.Image, format="PNG") -> str:
    """Converts a PIL Image object to a base64 encoded string."""
    buffered = BytesIO()
    pil_image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def generate_point_html(pil_image: Image.Image, points_data: list, image_id: str = "imageToAnnotate") -> str:
    """
    Generates an HTML string to display an image with points overlaid.

    Args:
        pil_image: The PIL Image object.
        points_data: A list of dictionaries, where each dict has "point": [y, x] (normalized 0-1000)
                     and "label": "description".
        image_id: A unique ID for the image element in HTML, if multiple images are on a page.

    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)

    # Ensure points_data is a list of dicts as expected
    if not isinstance(points_data, list):
        # print(f"Warning: points_data is not a list: {points_data}")
        points_data = [] # Default to empty if format is incorrect

    svg_elements = ""
    for item in points_data:
        if isinstance(item, dict) and "point" in item and "label" in item:
            try:
                y, x = item["point"]
                label = item["label"]
                # Normalize from 0-1000 to 0-1 for SVG percentage coordinates
                svg_x = x / 1000.0 * 100
                svg_y = y / 1000.0 * 100
                svg_elements += f'<circle cx="{svg_x}%" cy="{svg_y}%" r="5" fill="red" />'
                svg_elements += f'<text x="{svg_x}%" y="{svg_y}%" dy="-10" fill="white" background="black" font-size="12" text-anchor="middle">{label}</text>'
            except (TypeError, ValueError, KeyError) as e:
                # print(f"Skipping invalid point item: {item}. Error: {e}")
                continue # Skip malformed items
        else:
            # print(f"Skipping malformed item in points_data: {item}")
            pass


    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated Image" style="max-width: 100%; height: auto;">
        <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; pointer-events: none;">
            {svg_elements}
        </svg>
    </div>
    """
    return html_content


def generate_2d_box_html(pil_image: Image.Image, boxes_data: list, image_id: str = "imageToAnnotate2D") -> str:
    """
    Generates an HTML string to display an image with 2D bounding boxes overlaid.
    Args:
        pil_image: The PIL Image object.
        boxes_data: A list of dictionaries, where each dict has "box_2d": [ymin, xmin, ymax, xmax] (normalized 0-1)
                     and "label": "description".
        image_id: A unique ID for the image element in HTML.
    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)
    svg_elements = ""

    if not isinstance(boxes_data, list):
        boxes_data = []

    for item in boxes_data:
        if isinstance(item, dict) and "box_2d" in item and "label" in item:
            try:
                ymin, xmin, ymax, xmax = item["box_2d"]
                label = item["label"]

                # Convert normalized (0-1) coordinates to SVG percentage
                svg_x = xmin * 100
                svg_y = ymin * 100
                svg_width = (xmax - xmin) * 100
                svg_height = (ymax - ymin) * 100

                svg_elements += f'<rect x="{svg_x}%" y="{svg_y}%" width="{svg_width}%" height="{svg_height}%" style="fill:blue;stroke:blue;stroke-width:1;fill-opacity:0.1;stroke-opacity:0.9" />'
                svg_elements += f'<text x="{svg_x}%" y="{svg_y}%" dy="-5" fill="white" background="blue" font-size="12">{label}</text>'
            except (TypeError, ValueError, KeyError) as e:
                # print(f"Skipping invalid 2D box item: {item}. Error: {e}")
                continue
        else:
            pass # print(f"Skipping malformed item in 2D boxes_data: {item}")


    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated 2D Image" style="max-width: 100%; height: auto;">
        <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; pointer-events: none;">
            {svg_elements}
        </svg>
    </div>
    """
    return html_content


def generate_3d_box_html(pil_image: Image.Image, boxes_json_str: str, image_id: str = "imageToAnnotate3D") -> str:
    """
    Generates HTML to display an image with 3D bounding boxes.
    This is a simplified version of the notebook's visualizer.
    It expects boxes_json_str to be the direct JSON string from Gemini.
    """
    img_base64 = pil_to_base64(pil_image)

    # The notebook's JS is quite involved. For a Streamlit context,
    # a full port of the interactive three.js visualizer is complex.
    # This will be a simplified version or a placeholder if direct embedding is too hard.
    # For now, let's try to adapt the core concept of projecting boxes.
    # The original script uses external libraries and complex DOM manipulation.
    # A true 3D rendering in Streamlit would typically require a custom component or a library like PyDeck for limited 3D.

    # Given the complexity of the JS from the notebook (three.js, orbit controls, etc.)
    # a direct copy-paste into this string is not feasible without significant refactoring
    # for a non-Jupyter, single-HTML output.
    # The notebook's `generate_3d_box_html` mainly sets up divs and passes data to JS
    # that is assumed to be loaded in the Colab environment.

    # Simplified approach: Display the image and the raw JSON for 3D boxes.
    # A proper 3D visualization is a significant sub-project.

    # Let's include the basic structure and the JS that parses the boxes,
    # but the rendering part will be challenging to make work identically
    # without the full three.js setup from the notebook's environment.

    # The provided snippet in the prompt for `generate_3d_box_html` is mostly HTML structure
    # and placeholders for JS functions like `init` and `renderBoxes`.
    # The actual three.js logic is not in that snippet.

    # For now, this function will display the image and the JSON data.
    # If a more direct visualization is needed, it would require either:
    # 1. A much more complex HTML string with inline three.js and dependencies (hard to manage).
    # 2. A Streamlit custom component.
    # 3. Server-side projection of 3D boxes to 2D and drawing them (complex math).

    # Using a placeholder approach similar to the original prompt's structure,
    # but acknowledging the JS part won't fully function without its dependencies.

    # Let's try to adapt the HTML structure from the user's prompt,
    # and include a script tag that would attempt to process `boxes_json_str`.
    # The visualization part of the script from the notebook is complex and relies on `three.js`.
    # We will include a simplified version that attempts to draw basic overlays or prints data.

    # The core of the notebook's 3D viz is in a <script type="module"> section.
    # Trying to replicate a simplified version.

    # For simplicity in Streamlit, we'll use the 2D box representation for 3D boxes for now,
    # and just list the 3D properties. A full 3D interactive view is out of scope for simple HTML generation.
    # The `boxes_json_str` should be parsed first.

    parsed_boxes = parse_gemini_json_output(boxes_json_str)
    if not isinstance(parsed_boxes, list):
        parsed_boxes = []

    # Create a simple textual representation of 3D boxes for now.
    # A visual representation would require projecting 3D coordinates to 2D,
    # which involves camera parameters, etc. This is non-trivial.

    box_details_html = "<ul>"
    for box_data in parsed_boxes:
        if isinstance(box_data, dict) and "label" in box_data and "box_3d" in box_data:
            label = box_data.get("label", "N/A")
            box_3d_params = box_data.get("box_3d", [])
            box_details_html += f"<li><b>{label}</b>: {box_3d_params}</li>"
    box_details_html += "</ul>"


    # Fallback: show image and the JSON data as text.
    # This is because the notebook's HTML relies on external JS and a specific environment.
    html_content = f"""
    <h4>3D Bounding Box Data (Raw JSON and Details)</h4>
    <div style="display: flex; flex-direction: row; gap: 20px;">
        <div style="flex: 1;">
            <p><b>Annotated Image (No 3D Overlay - See Data Below):</b></p>
            <img src="data:image/png;base64,{img_base64}" alt="Base Image" style="max-width: 100%; height: auto;">
        </div>
        <div style="flex: 1; background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
            <p><b>Detected 3D Box Data:</b></p>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{json.dumps(parsed_boxes, indent=2)}</pre>
            <p><b>Formatted Details:</b></p>
            {box_details_html}
        </div>
    </div>
    <p><small>Note: Full interactive 3D visualization as seen in the cookbook requires a more complex setup (e.g., with three.js) not directly replicable here. Displaying raw data and basic details instead.</small></p>
    """
    return html_content


[end of utils/visualization_utils.py]
