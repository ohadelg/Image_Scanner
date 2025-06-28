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
                # Convert from normalized 0-1000 coordinates to percentage coordinates
                # Ensure input x, y are within 0-1000 range first.
                # Clamping input values if they are outside the expected 0-1000 range.
                x_norm = max(0, min(1000, x))
                y_norm = max(0, min(1000, y))

                percent_x = (x_norm / 1000.0) * 100
                percent_y = (y_norm / 1000.0) * 100
                
                # Point styling
                circle_radius = 5 # px
                text_font_size = 12 # px
                text_color = "white"
                text_bg_color = "rgba(0,0,0,0.7)" # Semi-transparent black background for text
                point_color = "red"

                svg_elements += f'<circle cx="{percent_x}%" cy="{percent_y}%" r="{circle_radius}" fill="{point_color}" />'
                
                # Adjust text label position to avoid going off-screen
                # If point is near top, draw text below; otherwise above.
                text_dy = "-1em" # Default above point
                if percent_y < 10: # If point is in top 10% of image height
                    text_dy = "1.5em" # Draw below point (adjust as needed)

                # Text anchor based on x position to avoid going off sides
                text_anchor = "middle"
                if percent_x < 10: # Near left edge
                    text_anchor = "start"
                elif percent_x > 90: # Near right edge
                    text_anchor = "end"

                # Using a rect for text background for better appearance
                # Note: SVG <text> does not directly support a 'background' attribute.
                # A common workaround is to draw a <rect> behind the text.
                # For simplicity here, we'll keep the text element as is, but acknowledge this limitation.
                # A more robust solution would calculate text width and draw a rect.
                # The fill on text element is for the text itself.
                # Adding a slight stroke or using a background rect would be an improvement for future.
                svg_elements += f'<text x="{percent_x}%" y="{percent_y}%" dy="{text_dy}" fill="{text_color}" font-size="{text_font_size}px" text-anchor="{text_anchor}" style="paint-order: stroke; stroke: {text_bg_color}; stroke-width: 0.2em; stroke-linejoin: round;">{label}</text>'
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
    # Attempting to draw a simplified 2D representation of the 3D box.
    # Assumption: x_center, y_center, x_size, y_size from box_3d are normalized (0-1000)
    # and can be used to draw a 2D rectangle on the image plane.
    # box_3d format: [x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw]

    img_base64 = pil_to_base64(pil_image) # Moved from original position
    svg_elements = ""
    parsed_boxes = parse_gemini_json_output(boxes_json_str)

    raw_json_display = json.dumps(parsed_boxes, indent=2) # For showing raw data

    if not isinstance(parsed_boxes, list):
        parsed_boxes = []

    for item in parsed_boxes:
        if isinstance(item, dict) and "box_3d" in item and "label" in item:
            try:
                b3d = item["box_3d"]
                label = item["label"]

                if len(b3d) >= 5: # Need at least x_c, y_c, x_s, y_s
                    x_center_norm, y_center_norm, _, x_size_norm, y_size_norm = b3d[:5]

                    # Convert normalized (0-1000) center and size to SVG percentage for a 2D box
                    # Clamp input values to be safe
                    x_center = max(0, min(1000, x_center_norm)) / 10.0  # to percentage
                    y_center = max(0, min(1000, y_center_norm)) / 10.0  # to percentage
                    width_pct = max(0, min(1000, x_size_norm)) / 10.0    # to percentage
                    height_pct = max(0, min(1000, y_size_norm)) / 10.0   # to percentage

                    svg_x = x_center - width_pct / 2
                    svg_y = y_center - height_pct / 2

                    # Ensure box coordinates are within image boundaries (0-100%)
                    svg_x = max(0, min(100 - width_pct, svg_x))
                    svg_y = max(0, min(100 - height_pct, svg_y))
                    # width_pct = min(width_pct, 100 - svg_x) # Adjust width if it goes out of bounds
                    # height_pct = min(height_pct, 100 - svg_y) # Adjust height

                    svg_elements += f'<rect x="{svg_x}%" y="{svg_y}%" width="{width_pct}%" height="{height_pct}%" style="fill:purple;stroke:purple;stroke-width:1;fill-opacity:0.15;stroke-opacity:0.9" />'
                    svg_elements += f'<text x="{svg_x}%" y="{svg_y}%" dy="-5" fill="white" background="purple" font-size="12">{label} (3D)</text>'
            except (TypeError, ValueError, KeyError, IndexError) as e:
                # print(f"Skipping invalid 3D box item: {item}. Error: {e}")
                continue
        else:
            pass # print(f"Skipping malformed item in 3D boxes_data: {item}")

    # Display the image with SVG overlays, and also the raw JSON data
    html_content = f"""
    <div style="position: relative; display: inline-block; margin-bottom: 20px;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated 3D Image" style="max-width: 100%; height: auto;">
        <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; pointer-events: none;">
            {svg_elements}
        </svg>
    </div>
    <h4>3D Bounding Box Data (Raw JSON)</h4>
    <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
        <pre style="white-space: pre-wrap; word-wrap: break-word;">{raw_json_display}</pre>
    </div>
    <p><small>Note: Displaying a simplified 2D projection of the 3D boxes. Full 3D parameters (z-axis, rotation) are in the raw JSON above.</small></p>
    """
    return html_content


def generate_segmentation_html(pil_image: Image.Image, segments_data: list, image_id: str = "imageToSegment") -> str:
    """
    Generates an HTML string to display an image with segmentation masks (polygons) overlaid.

    Args:
        pil_image: The PIL Image object.
        segments_data: A list of dictionaries, where each dict has "label": "description"
                       and "mask": a list of polygons. Each polygon is a flat list of
                       [x1, y1, x2, y2, ..., xn, yn] coordinates normalized to 0-1000.
        image_id: A unique ID for the image element in HTML.

    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)
    svg_elements = ""

    if not isinstance(segments_data, list):
        # print(f"Warning: segments_data is not a list: {segments_data}")
        segments_data = []

    # Define a list of distinct colors for masks with some transparency
    colors = [
        "rgba(230, 25, 75, 0.5)",  # Red
        "rgba(60, 180, 75, 0.5)", # Green
        "rgba(0, 130, 200, 0.5)", # Blue
        "rgba(255, 225, 25, 0.5)",# Yellow
        "rgba(245, 130, 48, 0.5)", # Orange
        "rgba(145, 30, 180, 0.5)", # Purple
        "rgba(70, 240, 240, 0.5)", # Cyan
        "rgba(240, 50, 230, 0.5)", # Magenta
        "rgba(210, 245, 60, 0.5)", # Lime
        "rgba(250, 190, 212, 0.5)",# Pink
        "rgba(0, 128, 128, 0.5)", # Teal
        "rgba(220, 190, 255, 0.5)",# Lavender
    ]
    color_index = 0

    for item in segments_data:
        if not (isinstance(item, dict) and "mask" in item and "label" in item):
            # print(f"Skipping malformed item in segments_data: {item}")
            continue

        label = item["label"]
        polygons = item["mask"]

        if not isinstance(polygons, list):
            # print(f"Skipping item '{label}' with invalid polygons format: {polygons}")
            continue

        current_color = colors[color_index % len(colors)]
        color_index += 1

        for poly_coords in polygons:
            if not (isinstance(poly_coords, list) and len(poly_coords) >= 6 and len(poly_coords) % 2 == 0):
                # print(f"Skipping invalid polygon coordinate list for label '{label}': {poly_coords}")
                continue # Polygon needs at least 3 points (6 coordinates)

            # Convert [x1,y1,x2,y2,...] normalized 0-1000 to SVG point string "x1,y1 x2,y2 ..." in percentages
            points_str_list = []
            for j in range(0, len(poly_coords), 2):
                x_orig = poly_coords[j]
                y_orig = poly_coords[j+1]

                # Ensure coordinates are numbers before clamping
                if not (isinstance(x_orig, (int, float)) and isinstance(y_orig, (int, float))):
                    # print(f"Skipping non-numeric coordinate in polygon for label '{label}': ({x_orig}, {y_orig})")
                    points_str_list = [] # Invalidate this polygon
                    break

                x = max(0, min(1000, x_orig))     # Clamp x
                y = max(0, min(1000, y_orig)) # Clamp y
                points_str_list.append(f"{(x / 1000.0) * 100}%," + f"{(y / 1000.0) * 100}%")

            if points_str_list: # Only add polygon if points were valid
                svg_elements += f'<polygon points="{" ".join(points_str_list)}" style="fill:{current_color}; stroke:black; stroke-width:0.2px;" />'

        # Add label - position near the first point of the first valid polygon
        if polygons:
            first_valid_poly = next((p for p in polygons if isinstance(p, list) and len(p) >=2 and isinstance(p[0], (int,float)) and isinstance(p[1], (int,float))), None)
            if first_valid_poly:
                text_x_orig = first_valid_poly[0]
                text_y_orig = first_valid_poly[1]
                text_x = (max(0, min(1000, text_x_orig)) / 1000.0) * 100
                text_y = (max(0, min(1000, text_y_orig)) / 1000.0) * 100

                text_anchor = "middle"
                if text_x < 10: text_anchor = "start"
                elif text_x > 90: text_anchor = "end"

                text_dy = "-0.5em"
                if text_y < 10: text_dy = "1em"


                svg_elements += f'<text x="{text_x}%" y="{text_y}%" dy="{text_dy}" fill="black" font-size="10px" text-anchor="{text_anchor}" style="paint-order: stroke; stroke: white; stroke-width: 0.15em; stroke-linejoin: round;">{label}</text>'

    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Segmented Image" style="max-width: 100%; height: auto;">
        <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; pointer-events: none;">
            {svg_elements}
        </svg>
    </div>
    """
    return html_content
