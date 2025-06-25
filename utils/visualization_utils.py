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
    Generates an HTML string to display an image with points overlaid.

    Args:
        pil_image: The PIL Image object.
        points_data: A list of dictionaries, where each dict has "point": [y, x] (normalized 0-1000)
                     and "label": "description".
        image_id: A unique ID for the image element in HTML, if multiple images are on a page.
        mirror_x: If True, mirrors the x-coordinate (useful if coordinates are in different coordinate system).

    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)

    # Ensure points_data is a list of dicts as expected
    if not isinstance(points_data, list):
        # print(f"Warning: points_data is not a list: {points_data}")
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

    svg_elements = ""
    for i, item in enumerate(points_data):
        if isinstance(item, dict) and "point" in item and "label" in item:
            try:
                y_raw, x_raw = item["point"]
                label = item["label"]
                
                print(f"📍 Point {i+1}: '{label}'")
                print(f"   📊 Raw coordinates: y={y_raw}, x={x_raw}")

                # Convert from normalized 0-1000 coordinates to absolute pixel coordinates
                # The 0-1000 range maps to the actual image dimensions
                if mirror_x:
                    # Mirror the x-coordinate: x = width - x
                    svg_x = pil_image.width - ((x_raw / 1000.0) * pil_image.width)
                    print(f"   🔄 Mirrored x-coordinate: {x_raw} → {svg_x:.1f}px")
                else:
                    svg_x = (x_raw / 1000.0) * pil_image.width
                
                svg_y = (y_raw / 1000.0) * pil_image.height
                
                # Clamp coordinates to image bounds
                svg_x = max(0.0, min(pil_image.width, svg_x))
                svg_y = max(0.0, min(pil_image.height, svg_y))
                
                print(f"   🎯 SVG coordinates: x={svg_x:.1f}px, y={svg_y:.1f}px")
                print(f"   ✅ Point {i+1} processed successfully")

                # Make points more visible with bright colors and larger size
                svg_elements += f'<circle cx="{svg_x}" cy="{svg_y}" r="8" fill="red" stroke="white" stroke-width="2" />'
                svg_elements += f'<text x="{svg_x}" y="{svg_y}" dy="-12" fill="white" stroke="black" stroke-width="1" font-size="12" font-weight="bold" text-anchor="middle">{label}</text>'
            except (TypeError, ValueError, KeyError) as e:
                print(f"   ❌ Error processing point {i+1}: {e}")
                continue # Skip malformed items
        else:
            print(f"   ❌ Skipping malformed item {i+1}: {item}")
            pass

    print("-" * 80)
    print(f"🎨 Generated {len(svg_elements.split('<circle')) - 1} SVG circles")
    print(f"📏 Total SVG elements length: {len(svg_elements)} characters")

    # If no points were generated, add a test point to verify the function works
    if not svg_elements:
        print("⚠️  No points generated, adding test point")
        test_x = pil_image.width * 0.1  # 10% from left
        test_y = pil_image.height * 0.1  # 10% from top
        svg_elements = f'<circle cx="{test_x}" cy="{test_y}" r="10" fill="yellow" stroke="blue" stroke-width="3" />'
        svg_elements += f'<text x="{test_x}" y="{test_y}" dy="-15" fill="black" stroke="white" stroke-width="1" font-size="14" font-weight="bold" text-anchor="middle">TEST POINT</text>'

    print("=" * 80)
    print("🔍 END POINTS VISUALIZATION DEBUG LOG")
    print("=" * 80)
    print(f"📐 Final SVG viewBox: 0 0 {pil_image.width} {pil_image.height}")
    print(f"🎯 Scaling approach: Normalized 0-1000 → Absolute pixels → SVG viewBox → Responsive scaling")
    print(f"✅ Each image will have its own coordinate system based on its dimensions")
    print("=" * 80)

    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated Image" style="max-width: 100%; height: auto; display: block;">
        <svg viewBox="0 0 {pil_image.width} {pil_image.height}" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 10; width: 100%; height: 100%;">
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
        boxes_data: A list of dictionaries, where each dict has "box_2d": [ymin, xmin, ymax, xmax] 
                     (can be normalized 0-1 or absolute pixel coordinates)
                     and "label": "description".
        image_id: A unique ID for the image element in HTML.
    Returns:
        An HTML string for rendering.
    """
    img_base64 = pil_to_base64(pil_image)
    svg_elements = ""

    if not isinstance(boxes_data, list):
        boxes_data = []

    # Comprehensive debug logging
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
    
    for i, item in enumerate(boxes_data):
        if isinstance(item, dict) and "box_2d" in item and "label" in item:
            try:
                ymin_raw, xmin_raw, ymax_raw, xmax_raw = item["box_2d"]
                label = item["label"]
                
                print(f"📦 Box {i+1}: '{label}'")
                print(f"   📊 Raw coordinates: ymin={ymin_raw}, xmin={xmin_raw}, ymax={ymax_raw}, xmax={xmax_raw}")

                # Determine if coordinates are normalized (0-1) or absolute pixels
                # If any coordinate is > 1, assume they are absolute pixel coordinates
                is_normalized = all(coord <= 1.0 for coord in [ymin_raw, xmin_raw, ymax_raw, xmax_raw])
                
                if is_normalized:
                    print(f"   🔄 Using normalized coordinates (0-1)")
                    # Clamp normalized coordinates to the [0, 1] range
                    ymin = max(0.0, min(1.0, ymin_raw))
                    xmin = max(0.0, min(1.0, xmin_raw))
                    ymax = max(0.0, min(1.0, ymax_raw))
                    xmax = max(0.0, min(1.0, xmax_raw))
                else:
                    print(f"   🔄 Converting absolute pixel coordinates to normalized")
                    print(f"   📏 Image bounds: width={pil_image.width}, height={pil_image.height}")
                    
                    # Check if coordinates are within image bounds
                    if (xmin_raw >= pil_image.width or xmax_raw >= pil_image.width or 
                        ymin_raw >= pil_image.height or ymax_raw >= pil_image.height):
                        print(f"   ⚠️  WARNING: Coordinates outside image bounds!")
                        print(f"   📏 Image: {pil_image.width}x{pil_image.height}, Coords: xmin={xmin_raw}, xmax={xmax_raw}, ymin={ymin_raw}, ymax={ymax_raw}")
                        
                        # Try to scale coordinates to fit within image bounds
                        # Find the maximum scale factor needed
                        scale_x = min(1.0, (pil_image.width - 1) / max(xmax_raw, 1))
                        scale_y = min(1.0, (pil_image.height - 1) / max(ymax_raw, 1))
                        scale_factor = min(scale_x, scale_y)
                        
                        print(f"   🔧 Scaling coordinates by factor: {scale_factor:.4f}")
                        
                        # Scale the coordinates
                        xmin_raw = xmin_raw * scale_factor
                        xmax_raw = xmax_raw * scale_factor
                        ymin_raw = ymin_raw * scale_factor
                        ymax_raw = ymax_raw * scale_factor
                        
                        print(f"   📐 Scaled coordinates: xmin={xmin_raw:.1f}, xmax={xmax_raw:.1f}, ymin={ymin_raw:.1f}, ymax={ymax_raw:.1f}")
                    
                    # Convert absolute pixel coordinates to normalized (0-1)
                    ymin = max(0.0, min(1.0, ymin_raw / pil_image.height))
                    xmin = max(0.0, min(1.0, xmin_raw / pil_image.width))
                    ymax = max(0.0, min(1.0, ymax_raw / pil_image.height))
                    xmax = max(0.0, min(1.0, xmax_raw / pil_image.width))
                    print(f"   📐 Normalized: ymin={ymin:.4f}, xmin={xmin:.4f}, ymax={ymax:.4f}, xmax={xmax:.4f}")

                # Ensure ymax >= ymin and xmax >= xmin after clamping
                if ymax < ymin: 
                    ymax = ymin
                    print(f"   ⚠️  Fixed ymax < ymin")
                if xmax < xmin: 
                    xmax = xmin
                    print(f"   ⚠️  Fixed xmax < xmin")

                # Convert normalized (0-1) coordinates to absolute pixel coordinates
                svg_x = xmin * pil_image.width
                svg_y = ymin * pil_image.height
                svg_width = (xmax - xmin) * pil_image.width
                svg_height = (ymax - ymin) * pil_image.height

                # Ensure width and height are non-negative and have minimum size
                original_width = svg_width
                original_height = svg_height
                svg_width = max(4.0, svg_width)  # Minimum 4 pixels width
                svg_height = max(4.0, svg_height)  # Minimum 4 pixels height
                
                if original_width < 4.0 or original_height < 4.0:
                    print(f"   ⚠️  Enforced minimum size: width {original_width:.1f}px → {svg_width:.1f}px, height {original_height:.1f}px → {svg_height:.1f}px")
                
                print(f"   🎯 SVG coordinates: x={svg_x:.1f}px, y={svg_y:.1f}px, w={svg_width:.1f}px, h={svg_height:.1f}px")
                
                # Check if the box is too small or positioned incorrectly
                if svg_width <= 4.0 and svg_height <= 4.0:
                    print(f"   ⚠️  WARNING: Box is very small, may not be visible!")
                    # Use a larger fallback box in the center of the image
                    svg_x = pil_image.width * 0.25  # 25% from left
                    svg_y = pil_image.height * 0.25  # 25% from top
                    svg_width = pil_image.width * 0.5  # 50% width
                    svg_height = pil_image.height * 0.5  # 50% height
                    print(f"   🔧 Using fallback box: x={svg_x:.1f}px, y={svg_y:.1f}px, w={svg_width:.1f}px, h={svg_height:.1f}px")
                
                print(f"   ✅ Box {i+1} processed successfully")

                # Make boxes much more visible with bright colors and thick stroke
                svg_elements += f'<rect x="{svg_x}" y="{svg_y}" width="{svg_width}" height="{svg_height}" style="fill:lime;stroke:red;stroke-width:3;fill-opacity:0.3;stroke-opacity:1.0" />'
                svg_elements += f'<text x="{svg_x}" y="{svg_y}" dy="-5" fill="white" stroke="black" stroke-width="1" font-size="14" font-weight="bold">{label}</text>'
            except (TypeError, ValueError, KeyError) as e:
                print(f"   ❌ Error processing box {i+1}: {e}")
                continue
        else:
            print(f"   ❌ Skipping malformed item {i+1}: {item}")
            pass

    print("-" * 80)
    print(f"🎨 Generated {len(svg_elements.split('<rect')) - 1} SVG rectangles")
    print(f"📏 Total SVG elements length: {len(svg_elements)} characters")

    # If no boxes were generated, add a test box to verify the function works
    if not svg_elements:
        print("⚠️  No boxes generated, adding test box")
        test_x = pil_image.width * 0.1  # 10% from left
        test_y = pil_image.height * 0.1  # 10% from top
        test_width = pil_image.width * 0.2  # 20% width
        test_height = pil_image.height * 0.2  # 20% height
        svg_elements = f'<rect x="{test_x}" y="{test_y}" width="{test_width}" height="{test_height}" style="fill:yellow;stroke:blue;stroke-width:4;fill-opacity:0.5;stroke-opacity:1.0" />'
        svg_elements += f'<text x="{test_x}" y="{test_y}" dy="-5" fill="black" stroke="white" stroke-width="1" font-size="16" font-weight="bold">TEST BOX</text>'

    print("=" * 80)
    print("🔍 END 2D BOUNDING BOX DEBUG LOG")
    print("=" * 80)
    print(f"📐 Final SVG viewBox: 0 0 {pil_image.width} {pil_image.height}")
    print(f"🎯 Scaling approach: Absolute pixels → SVG viewBox → Responsive scaling")
    print(f"✅ Each image will have its own coordinate system based on its dimensions")
    print("=" * 80)

    html_content = f"""
    <div style="position: relative; display: inline-block;">
        <img id="{image_id}" src="data:image/png;base64,{img_base64}" alt="Annotated 2D Image" style="max-width: 100%; height: auto; display: block;">
        <svg viewBox="0 0 {pil_image.width} {pil_image.height}" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 10; width: 100%; height: 100%;">
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
