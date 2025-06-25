# visual_content_analyzer/utils/visualization_utils.py

import json
import base64
from io import BytesIO
from PIL import Image
import re

# Segmentation colors for different mask instances (matching sample app)
SEGMENTATION_COLORS = [
    '#E6194B', '#3C89D0', '#3CB44B', '#FFE119', '#911EB4',
    '#42D4F4', '#F58231', '#F032E6', '#BFEF45', '#469990'
]

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

SEGMENTATION_COLORS_RGB = [hex_to_rgb(color) for color in SEGMENTATION_COLORS]

def parse_gemini_json_output(json_output_str: str) -> dict | list | None:
    """
    Parses JSON output from Gemini, which may be wrapped in markdown code blocks.
    Handles potential errors during parsing with improved robustness.
    """
    if not json_output_str:
        return None

    # Debug logging
    print("=" * 80)
    print("🔍 JSON PARSER DEBUG LOG")
    print("=" * 80)
    print(f"📥 Input message length: {len(json_output_str)} characters")
    print(f"📥 Input message preview: {json_output_str[:200]}...")
    print("-" * 80)

    # Remove markdown fencing if present
    cleaned_str = json_output_str.strip()
    
    # Handle various markdown code block formats
    if cleaned_str.startswith("```json"):
        cleaned_str = cleaned_str[7:] # Remove ```json
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3] # Remove ```
        print("🔄 Removed ```json markdown fencing")
    elif cleaned_str.startswith("```"):
        cleaned_str = cleaned_str[3:]
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3]
        print("🔄 Removed ``` markdown fencing")

    cleaned_str = cleaned_str.strip()
    print(f"🧹 Cleaned message length: {len(cleaned_str)} characters")
    print(f"🧹 Cleaned message preview: {cleaned_str[:200]}...")

    # Try to parse the cleaned string
    try:
        parsed_data = json.loads(cleaned_str)
        print("✅ Successfully parsed JSON on first attempt")
        print(f"📊 Parsed data type: {type(parsed_data)}")
        print(f"📊 Parsed data: {parsed_data}")
        
        # Post-process the parsed data to fix common model output issues
        if isinstance(parsed_data, list):
            print(f"📋 Processing {len(parsed_data)} items in list")
            for i, item in enumerate(parsed_data):
                if isinstance(item, dict) and "box_2d" in item:
                    print(f"   📦 Item {i+1}: Found box_2d field")
                    # Fix the case where box_2d contains objects instead of flat array
                    box_2d = item["box_2d"]
                    print(f"   📦 Item {i+1}: Original box_2d: {box_2d}")
                    if isinstance(box_2d, list) and len(box_2d) > 0:
                        if isinstance(box_2d[0], dict):
                            # Convert from [{"ymin": 238, "xmin": 270, ...}, "label"] to [238, 270, 818, 511]
                            coords = box_2d[0]
                            if "ymin" in coords and "xmin" in coords and "ymax" in coords and "xmax" in coords:
                                item["box_2d"] = [coords["ymin"], coords["xmin"], coords["ymax"], coords["xmax"]]
                                print(f"   🔄 Item {i+1}: Fixed box_2d format: {item['box_2d']}")
                            else:
                                print(f"   ❌ Item {i+1}: Missing required coordinate fields in box_2d")
                        else:
                            print(f"   ✅ Item {i+1}: box_2d already in correct format")
                    else:
                        print(f"   ❌ Item {i+1}: box_2d is not a valid list")
        
        print("=" * 80)
        print("🔍 END JSON PARSER DEBUG LOG")
        print("=" * 80)
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error on first attempt: {e}")
        print("🔄 Trying alternative parsing methods...")
        
        # Fix missing commas issue
        print("🔧 Attempting to fix missing commas...")
        fixed_str = cleaned_str
        # Add missing commas after objects in arrays
        fixed_str = re.sub(r'}(\s*)"label"', r'},\1"label"', fixed_str)
        
        try:
            parsed_data = json.loads(fixed_str)
            print("✅ Successfully parsed JSON after fixing commas")
            print(f"📊 Parsed data: {parsed_data}")
            
            # Apply the same post-processing
            if isinstance(parsed_data, list):
                for i, item in enumerate(parsed_data):
                    if isinstance(item, dict) and "box_2d" in item:
                        box_2d = item["box_2d"]
                        if isinstance(box_2d, list) and len(box_2d) > 0:
                            if isinstance(box_2d[0], dict):
                                coords = box_2d[0]
                                if "ymin" in coords and "xmin" in coords and "ymax" in coords and "xmax" in coords:
                                    item["box_2d"] = [coords["ymin"], coords["xmin"], coords["ymax"], coords["xmax"]]
                                    print(f"🔄 Fixed box_2d format: {item['box_2d']}")
            
            print("=" * 80)
            print("🔍 END JSON PARSER DEBUG LOG")
            print("=" * 80)
            return parsed_data
        except json.JSONDecodeError:
            print("❌ Still failed after fixing commas")
        
        # Try to fix the structure where label is inside box_2d array
        print("🔧 Attempting to fix malformed box_2d structure...")
        try:
            # Pattern to match the malformed structure and fix it
            # From: [{"box_2d": [{"ymin": 166, ...}, "label": "dog"]}]
            # To:   [{"box_2d": [166, 318, 876, 776], "label": "dog"}]
            
            # Extract coordinates and labels using regex
            coord_pattern = r'"ymin":\s*(\d+).*?"xmin":\s*(\d+).*?"ymax":\s*(\d+).*?"xmax":\s*(\d+)'
            label_pattern = r'"label":\s*"([^"]+)"'
            
            coords_matches = re.findall(coord_pattern, cleaned_str, re.DOTALL)
            labels = re.findall(label_pattern, cleaned_str)
            
            if coords_matches and labels:
                print(f"🔧 Found {len(coords_matches)} coordinate sets and {len(labels)} labels")
                
                # Construct valid JSON
                items = []
                for i, (ymin, xmin, ymax, xmax) in enumerate(coords_matches):
                    if i < len(labels):
                        item = {
                            "box_2d": [int(ymin), int(xmin), int(ymax), int(xmax)],
                            "label": labels[i]
                        }
                        items.append(item)
                
                if items:
                    result = items
                    print(f"✅ Successfully reconstructed JSON: {result}")
                    print("=" * 80)
                    print("🔍 END JSON PARSER DEBUG LOG")
                    print("=" * 80)
                    return result
        except Exception as e:
            print(f"❌ Structure fix failed: {e}")
        
        # First attempt: try to find JSON within the text
        json_patterns = [
            r'\[.*\]',  # Array pattern
            r'\{.*\}',  # Object pattern
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, cleaned_str, re.DOTALL)
            print(f"🔍 Found {len(matches)} matches for pattern {pattern}")
            for j, match in enumerate(matches):
                try:
                    # Try to fix the match
                    fixed_match = re.sub(r'}(\s*)"label"', r'},\1"label"', match)
                    parsed_data = json.loads(fixed_match)
                    print(f"✅ Successfully parsed JSON using pattern {pattern}, match {j+1}")
                    print(f"📊 Parsed data: {parsed_data}")
                    
                    # Apply the same post-processing
                    if isinstance(parsed_data, list):
                        for i, item in enumerate(parsed_data):
                            if isinstance(item, dict) and "box_2d" in item:
                                box_2d = item["box_2d"]
                                if isinstance(box_2d, list) and len(box_2d) > 0:
                                    if isinstance(box_2d[0], dict):
                                        coords = box_2d[0]
                                        if "ymin" in coords and "xmin" in coords and "ymax" in coords and "xmax" in coords:
                                            item["box_2d"] = [coords["ymin"], coords["xmin"], coords["ymax"], coords["xmax"]]
                                            print(f"🔄 Fixed box_2d format: {item['box_2d']}")
                    
                    print("=" * 80)
                    print("🔍 END JSON PARSER DEBUG LOG")
                    print("=" * 80)
                    return parsed_data
                except json.JSONDecodeError:
                    continue
        
        # If all attempts fail, return None and log the issue
        print("❌ All parsing attempts failed")
        print(f"📥 Original input: {json_output_str[:200]}...")
        print(f"🧹 Cleaned input: {cleaned_str[:200]}...")
        print("=" * 80)
        print("🔍 END JSON PARSER DEBUG LOG")
        print("=" * 80)
        return None


def pil_to_base64(pil_image: Image.Image, format="PNG") -> str:
    """Converts a PIL Image object to a base64 encoded string."""
    buffered = BytesIO()
    pil_image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def generate_point_html(pil_image: Image.Image, points_data: list, image_id: str = "imageToAnnotate", mirror_x: bool = False) -> str:
    """
    Generates HTML to display an image with points overlaid.
    Matches the sample app's approach: coordinates normalized to 0-1000, positioned using percentages.
    
    Args:
        pil_image: The PIL Image object.
        points_data: A list of dictionaries, where each dict has "point": [y, x] (normalized to 0-1000)
                   and "label": "description".
        image_id: A unique ID for the image element in HTML, if multiple images are on a page.
        mirror_x: Whether to mirror the x-coordinate (not used in sample app).
    
    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)
    
    # Ensure points_data is a list of dicts as expected
    if not isinstance(points_data, list):
        points_data = [] # Default to empty if format is incorrect
    
    # Debug logging
    print("=" * 80)
    print("🔍 POINTS VISUALIZATION DEBUG LOG")
    print("=" * 80)
    print(f"📁 Image ID: {image_id}")
    print(f"📐 Image Dimensions: {pil_image.width} x {pil_image.height} pixels")
    print(f"🔄 Mirror X: {mirror_x}")
    print(f"📦 Number of points received: {len(points_data)}")
    print(f"📋 Raw points data: {points_data}")
    print("-" * 80)
    
    point_elements = ""
    point_details = []
    
    for i, item in enumerate(points_data):
        if isinstance(item, dict) and "point" in item and "label" in item:
            try:
                # Extract coordinates (normalized to 0-1000 like sample app)
                point_coords = item["point"]
                label = item["label"]
                
                if len(point_coords) == 2:
                    y_raw, x_raw = point_coords
                    
                    print(f"📍 Point {i+1}: '{label}'")
                    print(f"   📊 Raw coordinates: y={y_raw}, x={x_raw}")
                    
                    # Convert from normalized 0-1000 to percentages (like sample app)
                    # Note: sample app swaps y,x: x = point[1]/1000, y = point[0]/1000
                    x_percent = (x_raw / 1000) * 100
                    y_percent = (y_raw / 1000) * 100
                    
                    print(f"   📐 Percentages: x={x_percent:.1f}%, y={y_percent:.1f}%")
                    print(f"   ✅ Point {i+1} processed successfully")
                    
                    # Create point element (like sample app)
                    point_elements += f"""
                    <div style="position: absolute; 
                               left: {x_percent}%; 
                               top: {y_percent}%; 
                               pointer-events: none; 
                               z-index: {10 + i};">
                        <div style="position: absolute; 
                                   background: #3B68FF; 
                                   text-align: center; 
                                   color: white; 
                                   font-size: 12px; 
                                   padding: 2px 6px; 
                                   border-radius: 3px; 
                                   bottom: 16px; 
                                   left: 50%; 
                                   transform: translateX(-50%); 
                                   white-space: nowrap;">
                            {label}
                        </div>
                        <div style="position: absolute; 
                                   width: 11px; 
                                   height: 11px; 
                                   background: #3B68FF; 
                                   border-radius: 50%; 
                                   border: 2px solid white; 
                                   transform: translate(-50%, -50%);">
                        </div>
                    </div>
                    """
                    
                    point_details.append(f"<li><b>{label}</b>: Point({x_raw:.0f}, {y_raw:.0f})</li>")
                    
            except (TypeError, ValueError, KeyError) as e:
                print(f"   ❌ Error processing point {i+1}: {e}")
                point_details.append(f"<li>Error processing point {i+1}: {e}</li>")
                continue
        else:
            print(f"   ❌ Skipping malformed item {i+1}: {item}")
            point_details.append(f"<li>Invalid point data format for item {i+1}</li>")
    
    print("-" * 80)
    print(f"🎨 Generated {len(point_elements.split('position: absolute')) - 1} point elements")
    print(f"📏 Total point elements length: {len(point_elements)} characters")
    print("=" * 80)
    print("🔍 END POINTS VISUALIZATION DEBUG LOG")
    print("=" * 80)
    
    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Points Image" style="max-width: 100%; height: auto; display: block;">
        {point_elements}
    </div>
    """
    return html_content


def generate_2d_box_html(pil_image: Image.Image, boxes_data: list, image_id: str = "imageToAnnotate2D") -> str:
    """
    Generates HTML to display an image with 2D bounding boxes overlaid.
    Matches the sample app's approach: coordinates normalized to 0-1000, positioned using percentages.
    
    Args:
        pil_image: The PIL Image object.
        boxes_data: A list of dictionaries, where each dict has "box_2d": [ymin, xmin, ymax, xmax] (normalized to 0-1000)
                   and "label": "description".
        image_id: A unique ID for the image element in HTML, if multiple images are on a page.
    
    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)
    
    # Ensure boxes_data is a list of dicts as expected
    if not isinstance(boxes_data, list):
        boxes_data = [] # Default to empty if format is incorrect
    
    # Debug logging
    print("=" * 80)
    print("🔍 2D BOUNDING BOX DEBUG LOG")
    print("=" * 80)
    print(f"📁 Image ID: {image_id}")
    print(f"📐 Image Dimensions: {pil_image.width} x {pil_image.height} pixels")
    print(f"📐 Image Mode: {pil_image.mode}")
    print(f"📐 Image Format: {pil_image.format}")
    print(f"📦 Number of boxes received: {len(boxes_data)}")
    print(f"📋 Raw boxes data: {boxes_data}")
    print("-" * 80)
    
    box_elements = ""
    box_details = []
    
    for i, item in enumerate(boxes_data):
        if isinstance(item, dict) and "box_2d" in item and "label" in item:
            try:
                # Extract coordinates (normalized to 0-1000 like sample app)
                box_2d = item["box_2d"]
                label = item["label"]
                
                if len(box_2d) == 4:
                    ymin, xmin, ymax, xmax = box_2d
                    
                    print(f"📦 Box {i+1}: '{label}'")
                    print(f"   📊 Raw coordinates: ymin={ymin}, xmin={xmin}, ymax={ymax}, xmax={xmax}")
                    
                    # Convert from normalized 0-1000 to percentages (like sample app)
                    x_percent = (xmin / 1000) * 100
                    y_percent = (ymin / 1000) * 100
                    width_percent = ((xmax - xmin) / 1000) * 100
                    height_percent = ((ymax - ymin) / 1000) * 100
                    
                    print(f"   📐 Percentages: x={x_percent:.1f}%, y={y_percent:.1f}%, w={width_percent:.1f}%, h={height_percent:.1f}%")
                    print(f"   ✅ Box {i+1} processed successfully")
                    
                    # Create box element (like sample app)
                    box_elements += f"""
                    <div style="position: absolute; 
                               top: {y_percent}%; 
                               left: {x_percent}%; 
                               width: {width_percent}%; 
                               height: {height_percent}%; 
                               border: 2px solid #3B68FF; 
                               pointer-events: none; 
                               z-index: {10 + i};">
                        <div style="position: absolute; 
                                   top: 0; 
                                   left: 0; 
                                   background: #3B68FF; 
                                   color: white; 
                                   padding: 2px 6px; 
                                   font-size: 12px; 
                                   font-weight: bold;">
                            {label}
                        </div>
                    </div>
                    """
                    
                    box_details.append(f"<li><b>{label}</b>: Box({xmin:.0f}, {ymin:.0f}, {xmax:.0f}, {ymax:.0f})</li>")
                    
            except (TypeError, ValueError, KeyError) as e:
                print(f"   ❌ Error processing box {i+1}: {e}")
                box_details.append(f"<li>Error processing box {i+1}: {e}</li>")
                continue
        else:
            print(f"   ❌ Skipping malformed item {i+1}: {item}")
            box_details.append(f"<li>Invalid box data format for item {i+1}</li>")
    
    print("-" * 80)
    print(f"🎨 Generated {len(box_elements.split('position: absolute')) - 1} box elements")
    print(f"📏 Total box elements length: {len(box_elements)} characters")
    print("=" * 80)
    print("🔍 END 2D BOUNDING BOX DEBUG LOG")
    print("=" * 80)
    
    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="2D Bounding Box Image" style="max-width: 100%; height: auto; display: block;">
        {box_elements}
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


def generate_segmentation_html(pil_image: Image.Image, segmentation_data: list, image_id: str = "imageToAnnotateSegmentation") -> str:
    """
    Generates HTML to display an image with segmentation masks overlaid using HTML5 Canvas.
    Each mask is stretched to fit its bounding box, matching the sample app's approach.
    
    Args:
        pil_image: The base image
        segmentation_data: List of segmentation objects with box_2d, mask, and label
        image_id: Unique ID for the image element
    
    Returns:
        HTML string with the image and overlaid segmentation masks
    """
    img_base64 = pil_to_base64(pil_image)
    width = pil_image.width
    height = pil_image.height
    
    # Generate canvas elements for each segmentation mask
    canvas_elements = ""
    mask_details = []
    
    for i, item in enumerate(segmentation_data):
        if isinstance(item, dict) and "box_2d" in item and "mask" in item and "label" in item:
            try:
                # Extract bounding box coordinates (normalized to 0-1000)
                box_2d = item["box_2d"]
                mask_data = item["mask"]
                label = item["label"]
                
                if len(box_2d) == 4:
                    ymin, xmin, ymax, xmax = box_2d
                    # Convert to pixel coordinates
                    x_px = int((xmin / 1000) * width)
                    y_px = int((ymin / 1000) * height)
                    w_px = max(1, int(((xmax - xmin) / 1000) * width))
                    h_px = max(1, int(((ymax - ymin) / 1000) * height))
                    
                    # Get color for this mask (same as sample app)
                    color_rgb = SEGMENTATION_COLORS_RGB[i % len(SEGMENTATION_COLORS_RGB)]
                    color_hex = SEGMENTATION_COLORS[i % len(SEGMENTATION_COLORS)]
                    
                    # Create canvas element for this mask
                    canvas_id = f"mask_canvas_{image_id}_{i}"
                    canvas_elements += f"""
                    <div style="position: absolute; 
                               top: {y_px}px; 
                               left: {x_px}px; 
                               width: {w_px}px; 
                               height: {h_px}px; 
                               pointer-events: none; 
                               z-index: {10 + i};">
                        <canvas id="{canvas_id}" 
                                width="{w_px}" height="{h_px}"
                                style="width: 100%; height: 100%; opacity: 0.5; display: block;">
                        </canvas>
                        <div style="position: absolute; 
                                   top: 0; 
                                   left: 0; 
                                   background: {color_hex}; 
                                   color: white; 
                                   padding: 2px 6px; 
                                   font-size: 12px; 
                                   font-weight: bold; 
                                   border-radius: 3px; 
                                   z-index: {20 + i};">
                            {label}
                        </div>
                    </div>
                    """
                    
                    mask_details.append(f"<li><b>{label}</b>: Box({xmin:.0f}, {ymin:.0f}, {xmax:.0f}, {ymax:.0f})</li>")
                    
                    # Add JavaScript to process the mask (similar to sample app's BoxMask)
                    # Clean up mask data - remove data URL prefix if present
                    clean_mask_data = mask_data
                    if mask_data.startswith('data:image/png;base64,'):
                        clean_mask_data = mask_data[22:]  # Remove prefix
                    elif mask_data.startswith('data:image/'):
                        # Find the base64 part
                        base64_start = mask_data.find('base64,')
                        if base64_start != -1:
                            clean_mask_data = mask_data[base64_start + 7:]
                    
                    canvas_elements += f"""
                    <script>
                    (function() {{
                        const canvas = document.getElementById('{canvas_id}');
                        const ctx = canvas.getContext('2d');
                        const maskData = '{clean_mask_data}';
                        if (canvas && ctx && maskData) {{
                            const img = new window.Image();
                            img.onload = function() {{
                                // Stretch the mask to fill the canvas (bounding box)
                                ctx.clearRect(0, 0, canvas.width, canvas.height);
                                ctx.imageSmoothingEnabled = false;
                                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                                const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
                                const data = pixels.data;
                                for (let i = 0; i < data.length; i += 4) {{
                                    // Use alpha from mask (like sample app)
                                    data[i + 3] = data[i];
                                    // Set color from palette (like sample app)
                                    data[i] = {color_rgb[0]};
                                    data[i + 1] = {color_rgb[1]};
                                    data[i + 2] = {color_rgb[2]};
                                }}
                                ctx.putImageData(pixels, 0, 0);
                            }};
                            img.onerror = function() {{
                                ctx.fillStyle = '{color_hex}';
                                ctx.globalAlpha = 0.3;
                                ctx.fillRect(0, 0, canvas.width, canvas.height);
                            }};
                            img.src = 'data:image/png;base64,' + maskData;
                        }}
                    }})();
                    </script>
                    """
            except (TypeError, ValueError, KeyError) as e:
                mask_details.append(f"<li>Error processing mask {i}: {e}</li>")
                continue
        else:
            mask_details.append(f"<li>Invalid mask data format for item {i}</li>")
    
    mask_details_html = "<ul>" + "".join(mask_details) + "</ul>" if mask_details else "<p>No valid segmentation data to display.</p>"
    
    html_content = f"""
    <div style="position: relative; display: inline-block; width: {width}px; height: {height}px;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Segmentation Image" style="width: 100%; height: 100%; display: block;">
        {canvas_elements}
    </div>
    """
    return html_content
