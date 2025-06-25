# visual_content_analyzer/utils/visualization_utils.py

import json
import base64
from io import BytesIO
from PIL import Image
import re

def parse_gemini_json_output(json_output_str: str) -> dict | list | None:
    """
    Parses JSON output from Gemini, which may be wrapped in markdown code blocks.
    Handles potential errors during parsing with improved robustness.
    """
    if not json_output_str:
        return None

    # Remove markdown fencing if present
    cleaned_str = json_output_str.strip()
    
    # Handle various markdown code block formats
    if cleaned_str.startswith("```json"):
        cleaned_str = cleaned_str[7:] # Remove ```json
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3] # Remove ```
    elif cleaned_str.startswith("```"):
        cleaned_str = cleaned_str[3:]
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3]

    cleaned_str = cleaned_str.strip()

    # Try to parse the cleaned string
    try:
        return json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        # First attempt: try to find JSON within the text
        json_patterns = [
            r'\[.*\]',  # Array pattern
            r'\{.*\}',  # Object pattern
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, cleaned_str, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # Second attempt: try to fix common issues
        # Remove any text before the first [ or {
        for char in ['[', '{']:
            if char in cleaned_str:
                start_idx = cleaned_str.find(char)
                potential_json = cleaned_str[start_idx:]
                try:
                    return json.loads(potential_json)
                except json.JSONDecodeError:
                    continue
        
        # Third attempt: try to extract JSON from common model response patterns
        # Sometimes models add explanatory text
        lines = cleaned_str.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') or line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        
        # If all attempts fail, return None and log the issue
        print(f"Failed to parse JSON from model output. Original: {json_output_str[:200]}...")
        print(f"Cleaned: {cleaned_str[:200]}...")
        return None


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
                # Convert from normalized 0-1000 coordinates to percentage coordinates.
                # The 0-1000 range is assumed to map to 0%-100% of the image dimensions.
                percent_x = (x / 1000.0) * 100
                percent_y = (y / 1000.0) * 100
                
                # Clamping to 0-100% is good practice if source coordinates could be outside 0-1000.
                # However, if they are strictly within 0-1000, this might not be strictly necessary
                # but doesn't hurt. The main issue is usually the scaling factor.
                percent_x = max(0.0, min(100.0, percent_x))
                percent_y = max(0.0, min(100.0, percent_y))
                svg_elements += f'<circle cx="{percent_x}%" cy="{percent_y}%" r="5" fill="red" />'
                svg_elements += f'<text x="{percent_x}%" y="{percent_y}%" dy="-10" fill="white" background="black" font-size="12" text-anchor="middle">{label}</text>'
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
                ymin_raw, xmin_raw, ymax_raw, xmax_raw = item["box_2d"]
                label = item["label"]

                # Clamp normalized coordinates to the [0, 1] range
                ymin = max(0.0, min(1.0, ymin_raw))
                xmin = max(0.0, min(1.0, xmin_raw))
                ymax = max(0.0, min(1.0, ymax_raw))
                xmax = max(0.0, min(1.0, xmax_raw))

                # Ensure ymax >= ymin and xmax >= xmin after clamping
                if ymax < ymin: ymax = ymin
                if xmax < xmin: xmax = xmin

                # Convert normalized (0-1) coordinates to SVG percentage
                svg_x = xmin * 100
                svg_y = ymin * 100
                svg_width = (xmax - xmin) * 100
                svg_height = (ymax - ymin) * 100

                # Ensure width and height are non-negative
                svg_width = max(0.0, svg_width)
                svg_height = max(0.0, svg_height)

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
    # The `boxes_json_str` should be parsed first.
    parsed_boxes_data = parse_gemini_json_output(boxes_json_str)
    if not isinstance(parsed_boxes_data, list):
        parsed_boxes_data = []

    svg_elements = ""
    box_details_list = []

    for item in parsed_boxes_data:
        if isinstance(item, dict) and "box_3d" in item and "label" in item:
            try:
                # box_3d: [x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw]
                params = item["box_3d"]
                label = item["label"]

                if len(params) == 9:
                    x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw = params

                    # For drawing a 2D representation, we'll use x_center, y_center, x_size, y_size.
                    # Assuming these are normalized (0-1) like 2D boxes.
                    # This is an assumption as the prompt for 3D boxes doesn't explicitly state normalization.

                    # Clamp normalized coordinates to the [0, 1] range for the 2D projection
                    norm_xc = max(0.0, min(1.0, x_center))
                    norm_yc = max(0.0, min(1.0, y_center))
                    norm_xs = max(0.0, min(1.0, x_size)) # Width
                    norm_ys = max(0.0, min(1.0, y_size)) # Height

                    # Convert center and size to ymin, xmin, ymax, xmax for 2D box drawing
                    # xmin_2d = norm_xc - (norm_xs / 2.0)
                    # ymin_2d = norm_yc - (norm_ys / 2.0)
                    # xmax_2d = norm_xc + (norm_xs / 2.0)
                    # ymax_2d = norm_yc + (norm_ys / 2.0)

                    # Corrected: x_center, y_center are usually image coords, x_size, y_size are dimensions.
                    # Convert to SVG top-left (x,y) and width, height
                    svg_x = (norm_xc - norm_xs / 2.0) * 100
                    svg_y = (norm_yc - norm_ys / 2.0) * 100
                    svg_width = norm_xs * 100
                    svg_height = norm_ys * 100

                    # Clamp and ensure non-negative dimensions
                    svg_x = max(0.0, min(100.0 - svg_width, svg_x)) # Ensure box starts within bounds
                    svg_y = max(0.0, min(100.0 - svg_height, svg_y))
                    svg_width = max(0.0, min(100.0 - svg_x, svg_width))
                    svg_height = max(0.0, min(100.0 - svg_y, svg_height))


                    # Draw a 2D rectangle representing the base/center of the 3D box
                    svg_elements += f'<rect x="{svg_x}%" y="{svg_y}%" width="{svg_width}%" height="{svg_height}%" style="fill:green;stroke:green;stroke-width:1;fill-opacity:0.1;stroke-opacity:0.9" />'
                    svg_elements += f'<text x="{svg_x}%" y="{svg_y}%" dy="-5" fill="white" background="green" font-size="12">{label} (3D)</text>'

                    # Store details for textual display
                    box_details_list.append(f"<li><b>{label} (3D)</b>: Center:({x_center:.2f}, {y_center:.2f}, {z_center:.2f}), Size:({x_size:.2f}, {y_size:.2f}, {z_size:.2f}), RPY:({roll:.2f}, {pitch:.2f}, {yaw:.2f})</li>")
                else:
                    box_details_list.append(f"<li><b>{label} (3D)</b>: Malformed box_3d data (length {len(params)} not 9): {params}</li>")
            except (TypeError, ValueError, KeyError) as e:
                box_details_list.append(f"<li>Error parsing 3D box data for '{item.get('label', 'Unknown')}': {e}</li>")
                continue
        else:
            # print(f"Skipping malformed item in 3D boxes_data: {item}")
            pass

    box_details_html = "<ul>" + "".join(box_details_list) + "</ul>" if box_details_list else "<p>No valid 3D box data to display details for.</p>"

    html_content = f"""
    <h4>3D Bounding Box Visualization (Simplified 2D Projection) and Data</h4>
    <div style="display: flex; flex-direction: column; gap: 10px;">
        <div style="position: relative; display: inline-block; max-width: {pil_image.width}px; max-height: {pil_image.height}px;">
            <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated 3D Image" style="max-width: 100%; height: auto; display: block;">
            <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; pointer-events: none;">
                {svg_elements}
            </svg>
        </div>
        <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
            <p><b>Detected 3D Box Parameters:</b></p>
            {box_details_html}
            <p><b>Raw Model Output (JSON):</b></p>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{json.dumps(parsed_boxes_data, indent=2)}</pre>
        </div>
    </div>
    <p><small>Note: Displaying a simplified 2D projection of the 3D boxes. Full interactive 3D visualization is more complex. Assumes x_center, y_center, x_size, y_size from 'box_3d' are normalized [0-1] for 2D projection.</small></p>
    """
    return html_content
