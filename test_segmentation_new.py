#!/usr/bin/env python3
"""
Test script for the new segmentation functionality
"""

import json
from PIL import Image
import base64
from io import BytesIO
from utils.visualization_utils import generate_segmentation_html

def test_segmentation_new_format():
    """Test the segmentation HTML generation with the new format (box_2d, mask, label)"""
    
    # Create a simple test image
    test_image = Image.new('RGB', (200, 200), color='white')
    
    # Create sample segmentation data in the new format (like sample app)
    sample_data = [
        {
            "box_2d": [50, 50, 150, 150],  # [ymin, xmin, ymax, xmax] normalized to 0-1000
            "label": "Test Object 1",
            "mask": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # 1x1 transparent PNG
        },
        {
            "box_2d": [10, 10, 90, 90],  # [ymin, xmin, ymax, xmax] normalized to 0-1000
            "label": "Test Object 2", 
            "mask": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # 1x1 transparent PNG
        }
    ]
    
    try:
        # Generate HTML
        html_output = generate_segmentation_html(test_image, sample_data, "test_image_new")
        print("✅ New segmentation HTML generation successful!")
        print(f"HTML length: {len(html_output)} characters")
        
        # Check if the HTML contains expected elements
        if "mask_canvas_test_image_new_0" in html_output:
            print("✅ Canvas elements found in HTML")
        else:
            print("❌ Canvas elements not found in HTML")
            
        if "Test Object 1" in html_output and "Test Object 2" in html_output:
            print("✅ Labels found in HTML")
        else:
            print("❌ Labels not found in HTML")
            
        return True
    except Exception as e:
        print(f"❌ New segmentation HTML generation failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing new segmentation functionality...")
    success = test_segmentation_new_format()
    if success:
        print("🎉 New segmentation test passed!")
    else:
        print("💥 New segmentation test failed!") 