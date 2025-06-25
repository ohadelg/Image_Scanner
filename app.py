# visual_content_analyzer/app.py

import streamlit as st
import os
from PIL import Image
from io import BytesIO
import zipfile
import shutil
import pandas as pd
import json # For handling JSON data for CSV export
from utils.gemini_utils import get_gemini_client, generate_content_with_gemini, DEFAULT_MODEL_ID, PRO_MODEL_ID
from utils.visualization_utils import (
    parse_gemini_json_output,
    generate_point_html,
    generate_2d_box_html,
    generate_3d_box_html,
    pil_to_base64
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Visual Content Analyzer with VLM",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Global Variables & Setup ---
TEMP_DIR = "temp_uploaded_images"

# --- Helper Functions ---
def cleanup_temp_dir():
    """Removes the temporary directory if it exists."""
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
            # st.text("Cleaned up temporary files.") # Optional: for debugging
        except Exception as e:
            st.warning(f"Could not clean up temporary directory {TEMP_DIR}: {e}")

def display_analysis_results(results_data, analysis_type):
    """Displays analysis results based on the type and provides download option."""
    if not results_data:
        st.info("No results to display.")
        return

    st.subheader("Analysis Results:")
    for i, result in enumerate(results_data):
        st.markdown(f"---")
        st.markdown(f"#### {result['Image Name']}")

        pil_image = None
        if result.get("Image Bytes"):
            try:
                pil_image = Image.open(result["Image Bytes"])
            except Exception as e:
                st.error(f"Could not load image {result['Image Name']} for display: {e}")

        if analysis_type == "Image Classification":
            col1, col2 = st.columns([1, 2])
            with col1:
                if pil_image:
                    st.image(pil_image, width=200)
                else:
                    st.caption(f"Cannot display: {result['Image Name']}")
            with col2:
                st.write(f"**User Prompt:**")
                st.markdown(f"> {result.get('Prompt', 'N/A')}")
                if result.get('Full Prompt') and os.environ.get("SHOW_FULL_PROMPT", "False").lower() == "true":
                    with st.expander("View Full Prompt (User + JSON Format)"):
                        st.text(result.get('Full Prompt', 'N/A'))
                st.write(f"**Model's Output (Classification):**")
                st.markdown(f"> {result.get('Output', 'N/A')}")

        elif analysis_type in ["Point to Items", "2D Bounding Boxes", "3D Bounding Boxes"]:
            model_output_text = result.get('Output', '')
            html_was_generated = bool(result.get("HtmlOutput"))
            json_parse_error_indicated = "(Error parsing JSON)" in model_output_text

            # Show user prompt and full prompt
            st.write(f"**User Prompt:**")
            st.markdown(f"> {result.get('Prompt', 'N/A')}")
            if result.get('Full Prompt') and os.environ.get("SHOW_FULL_PROMPT", "False").lower() == "true":
                with st.expander("View Full Prompt (User + JSON Format)"):
                    st.text(result.get('Full Prompt', 'N/A'))

            if pil_image and html_was_generated:
                st.components.v1.html(result["HtmlOutput"], height=pil_image.height + 100 if pil_image.height < 800 else 800, scrolling=True)
            else: # Fallback if no HTML output or no image
                if pil_image:
                    st.image(pil_image, caption=f"Base image: {result['Image Name']}", width=300)

                if json_parse_error_indicated and not model_output_text.startswith("Error:"):
                    st.warning("Could not parse the model's output as valid JSON. Displaying raw output.")
                    with st.expander("🔍 Debug: View Raw Model Output"):
                        st.text(model_output_text)
                elif model_output_text.startswith("Error:") or model_output_text.startswith("Content blocked"):
                    st.error(f"Model Error: {model_output_text}")
                else:
                    # Show parsed JSON data for debugging
                    with st.expander("🔍 Debug: View Parsed JSON Data"):
                        if result.get("ParsedJSON"):
                            st.json(result.get("ParsedJSON"))
                        else:
                            st.text("No parsed JSON data available")

                st.markdown(f"**Model's Raw Output:**")
                st.text_area("Raw Output", value=model_output_text, height=150, disabled=True, key=f"raw_output_{i}")

        elif analysis_type == "Segmentation Masks":
            st.info("Segmentation mask display is not yet fully implemented.")
            if pil_image:
                st.image(pil_image, caption=f"Base image: {result['Image Name']}", width=300)
            
            # Show user prompt and full prompt
            st.write(f"**User Prompt:**")
            st.markdown(f"> {result.get('Prompt', 'N/A')}")
            if result.get('Full Prompt') and os.environ.get("SHOW_FULL_PROMPT", "False").lower() == "true":
                with st.expander("View Full Prompt (User + JSON Format)"):
                    st.text(result.get('Full Prompt', 'N/A'))
            
            st.markdown(f"**Model's Raw Output (Segmentation):** \n```\n{result.get('Output', 'N/A')}\n```")

        # Display raw output for debugging or if HTML failed
        if analysis_type not in ["Image Classification"] and not result.get("HtmlOutput"):
             with st.expander("View Raw Output from Model"):
                st.json(result.get('Output', '{}'))


    st.success(f"{analysis_type} complete!")

    # Prepare DataFrame for display and download
    df_display_cols = ["Image Name", "Prompt", "Output"]
    if "AnalysisType" not in [r.get("AnalysisType") for r in results_data if r]: # ensure column exists
        for r in results_data: r["AnalysisType"] = analysis_type # Add analysis type if not present

    df_results = pd.DataFrame(results_data)

    # Ensure 'Output' column exists, even if it's from 'Classification' field
    if "Classification" in df_results.columns and "Output" not in df_results.columns:
        df_results["Output"] = df_results["Classification"]

    # Select columns for DataFrame display, ensuring they exist
    cols_to_display_in_df = [col for col in df_display_cols if col in df_results.columns]
    if not cols_to_display_in_df and "Image Name" in df_results.columns: # Minimal fallback
        cols_to_display_in_df = ["Image Name"]

    display_df = df_results[cols_to_display_in_df] if cols_to_display_in_df else pd.DataFrame()


    st.subheader("Summary of Results:")
    if not display_df.empty:
        st.dataframe(display_df)

        # Download results as CSV - include raw output
        csv_df = df_results[["Image Name", "Prompt", "Output", "AnalysisType"]] if "Output" in df_results.columns else df_results[["Image Name", "Prompt", "AnalysisType"]]
        csv_data = csv_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv_data,
            file_name=f"gemini_{analysis_type.lower().replace(' ', '_')}_results.csv",
            mime="text/csv",
        )
    else:
        st.info("No data to display in summary table.")


# --- Main Application UI ---
st.title("🔍 Visual Content Analyzer with Gemini")
st.markdown(
    "Upload a **ZIP file** containing your images, provide a classification prompt, "
    "and let the model will analyze them!"
)

# --- API Key Configuration Check ---
api_key_configured = False
try:
    get_gemini_client() # Attempt to initialize the Gemini client
    api_key_configured = True
    st.sidebar.success("Gemini API Client initialized successfully.")
except (ValueError, ConnectionError) as e:
    st.error(
        f"**Error initializing Gemini API Client:** {e}. "
        "Please ensure your `GEMINI_API_KEY` is correctly set in a `.env` file. "
    )
    st.markdown(
        "Refer to the `README.md` for instructions on setting up your API key."
    )
    st.stop() # Halt execution if API key is not set

# --- User Inputs ---
st.header("1. Upload Your Image Folder (as a .zip file)")
uploaded_zip_file = st.file_uploader(
    "Select a .zip file containing your images.",
    type=["zip"],
    accept_multiple_files=False,
    help="Ensure the ZIP file contains image files (e.g., .png, .jpg, .jpeg)."
)

st.header("2. Select Analysis Type and Provide Instructions")

analysis_types = [
    "Image Classification",
    "Point to Items",
    "2D Bounding Boxes",
    "Segmentation Masks",
    "3D Bounding Boxes"
]
selected_analysis_type = st.selectbox(
    "Choose the type of analysis:",
    options=analysis_types,
    index=0
)

# Dynamic prompt area based on analysis type
prompt_label = "Enter your instructions for the VLM:"

# Separate user prompts from JSON format specifications
user_prompts = {
    "Image Classification": "Describe the main objects in this image and categorize it (e.g., dog, cat, cow).",
    "Point to Items": "Example: find all the dogs in the image and point to them.",
    "2D Bounding Boxes": "Example: find all the dogs in the image",
    "Segmentation Masks": "Segment the main objects in this image and provide their masks and labels.",
    "3D Bounding Boxes": "Detect the 3D bounding boxes of the main objects in the image."
}

# JSON format specifications that get automatically added to the prompt
json_format_specs = {
    "Image Classification": "Return just one word as output.",
    "Point to Items": "Point to no more than 10 items in the image. Include their labels. The answer should follow the json format: [{\"point\": [y, x], \"label\": \"description\"}, ...]. Points are normalized to 0-1000. IMPORTANT: The coordinates should be in a flat array [y, x], not as separate objects. Return ONLY valid JSON without any additional text or markdown formatting.",
    "2D Bounding Boxes": "Detect the relevant objects in this image and provide their 2D bounding boxes and labels. The answer should follow the json format: [{\"box_2d\": [ymin, xmin, ymax, xmax], \"label\": \"description\"}, ...]. Coordinates are normalized to 0-1. IMPORTANT: The coordinates should be in a flat array [ymin, xmin, ymax, xmax], not as separate objects with properties. Return ONLY valid JSON without any additional text or markdown formatting.",
    "Segmentation Masks": "The answer should follow the json format: [{\"mask\": [coordinates], \"label\": \"description\"}, ...]. (Further details needed on expected JSON format for masks) Return ONLY valid JSON without any additional text or markdown formatting.",
    "3D Bounding Boxes": "Output a json list where each entry contains the object name in \"label\" and its 3D bounding box in \"box_3d\": [x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw]. Return ONLY valid JSON without any additional text or markdown formatting."
}

# Legacy default_prompt_text for backward compatibility (can be removed later)
default_prompt_text = {
    "Image Classification": user_prompts["Image Classification"] + "\n" + json_format_specs["Image Classification"],
    "Point to Items": user_prompts["Point to Items"] + "\n" + json_format_specs["Point to Items"],
    "2D Bounding Boxes": user_prompts["2D Bounding Boxes"] + "\n" + json_format_specs["2D Bounding Boxes"],
    "Segmentation Masks": user_prompts["Segmentation Masks"] + "\n" + json_format_specs["Segmentation Masks"],
    "3D Bounding Boxes": user_prompts["3D Bounding Boxes"] + "\n" + json_format_specs["3D Bounding Boxes"]
}

prompt_help_text = {
    "Image Classification": "Examples: 'What objects are in this image?', 'Is this image related to nature or urban environments?'",
    "Point to Items": "Clearly describe what items to point to, or ask for general items. The JSON format will be automatically added.",
    "2D Bounding Boxes": "Specify if you want all objects or specific ones. The JSON format will be automatically added.",
    "Segmentation Masks": "Describe the objects to segment. The JSON format will be automatically added.",
    "3D Bounding Boxes": "Specify the objects of interest. The JSON format will be automatically added."
}

if selected_analysis_type == "Image Classification":
    prompt_label = "Enter Your Classification Prompt:"

prompt_text = st.text_area(
    label=prompt_label,
    value=user_prompts.get(selected_analysis_type, "Please provide instructions for the selected analysis type."),
    height=150,
    help=prompt_help_text.get(selected_analysis_type, "Provide clear instructions for the AI model.")
)

# Show the JSON format that will be automatically added
if selected_analysis_type in json_format_specs and os.environ.get("SHOW_JSON_FORMAT_SPECS", "False").lower() == "true":
    st.info(f"📋 **JSON Format will be automatically added:**\n{json_format_specs[selected_analysis_type]}")

# --- Process Images Button ---
analyze_button = st.button("Analyze Images", type="primary", disabled=not api_key_configured)

# --- Logic for Processing ---
if analyze_button:
    if uploaded_zip_file is None:
        st.error("❌ Please upload a ZIP file containing images.")
    elif not prompt_text.strip():
        st.error("❌ Please enter a classification prompt.")
    else:
        st.info("🔄 Processing images... This may take a while.")

        # Combine user prompt with JSON format specification
        full_prompt = prompt_text + "\n" + json_format_specs.get(selected_analysis_type, "")

        # Ensure temp_dir is clean before use
        cleanup_temp_dir()
        os.makedirs(TEMP_DIR, exist_ok=True)

        results_data = []
        image_files_processed_paths = []

        try:
            with zipfile.ZipFile(uploaded_zip_file, 'r') as zip_ref:
                zip_ref.extractall(TEMP_DIR)

            image_files = []
            for root, _, files in os.walk(TEMP_DIR):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        image_files.append(os.path.join(root, file))
                        print(f"Found image: {file}")

            if not image_files:
                st.warning("⚠️ No valid image files (png, jpg, jpeg, gif, bmp) found in the uploaded ZIP file.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_images = len(image_files)

                for i, image_path in enumerate(image_files):
                    image_name = os.path.basename(image_path)
                    status_text.text(f"Processing '{image_name}' ({i + 1}/{total_images})...")

                    try:
                        with open(image_path, "rb") as f:
                            image_bytes = f.read() # Read as bytes

                        # Store path for display, use BytesIO for PIL and Gemini
                        # Create a new BytesIO object for each iteration if it's consumed or closed
                        pil_image_display_bytes = BytesIO(image_bytes)

                        model_output = None
                        html_output_for_display = None
                        current_result_data = {
                            "Image Name": image_name,
                            "Prompt": prompt_text,  # Store only the user prompt for display
                            "Full Prompt": full_prompt,  # Store the full prompt for reference
                            "Image Bytes": pil_image_display_bytes, # For display in Streamlit
                            "AnalysisType": selected_analysis_type,
                            "Output": "Error: Processing failed before model call." # Default
                        }

                        gen_config = None
                        model_to_use = DEFAULT_MODEL_ID

                        if selected_analysis_type == "Image Classification":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use)
                            current_result_data["Output"] = model_output

                        elif selected_analysis_type == "Point to Items":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.5})
                            current_result_data["Output"] = model_output
                            if model_output and not model_output.startswith("Error:") and not model_output.startswith("Content blocked"):
                                parsed_json = parse_gemini_json_output(model_output)
                                if parsed_json:
                                    pil_img_for_html = Image.open(BytesIO(image_bytes)) # Re-open for HTML gen
                                    html_output_for_display = generate_point_html(pil_img_for_html, parsed_json, image_id=f"img_{i}")
                                else:
                                    current_result_data["Output"] += " (Error parsing JSON - Model output was not valid JSON format)"
                                    print(f"JSON parsing failed for {image_name}. Raw output: {model_output[:500]}...")

                        elif selected_analysis_type == "2D Bounding Boxes":
                            # Assuming similar config, can be adjusted
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.2})
                            current_result_data["Output"] = model_output
                            if model_output and not model_output.startswith("Error:") and not model_output.startswith("Content blocked"):
                                parsed_json = parse_gemini_json_output(model_output)
                                if parsed_json:
                                    print(f"Debug: Successfully parsed JSON for {image_name}: {parsed_json}")
                                    current_result_data["ParsedJSON"] = parsed_json  # Store for UI display
                                    pil_img_for_html = Image.open(BytesIO(image_bytes))
                                    html_output_for_display = generate_2d_box_html(pil_img_for_html, parsed_json, image_id=f"img_{i}")
                                else:
                                    current_result_data["Output"] += " (Error parsing JSON - Model output was not valid JSON format)"
                                    print(f"JSON parsing failed for {image_name}. Raw output: {model_output[:500]}...")

                        elif selected_analysis_type == "3D Bounding Boxes":
                            # May benefit from Pro model, but let's test with default first.
                            # model_to_use = PRO_MODEL_ID
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.5})
                            current_result_data["Output"] = model_output
                            if model_output and not model_output.startswith("Error:") and not model_output.startswith("Content blocked"):
                                # generate_3d_box_html expects the raw JSON string
                                pil_img_for_html = Image.open(BytesIO(image_bytes))
                                html_output_for_display = generate_3d_box_html(pil_img_for_html, model_output, image_id=f"img_{i}")
                                # No separate JSON parsing check here as generate_3d_box_html does it

                        elif selected_analysis_type == "Segmentation Masks":
                            # Placeholder - requires specific model/prompt tuning
                            model_output = f"Segmentation mask analysis for '{image_name}' is not fully implemented. Prompt: {full_prompt}"
                            st.warning(model_output) # Show once
                            current_result_data["Output"] = model_output

                        if html_output_for_display:
                            current_result_data["HtmlOutput"] = html_output_for_display

                        results_data.append(current_result_data)
                        image_files_processed_paths.append(image_path)

                    except ValueError as ve:
                        st.error(f"Skipping '{image_name}': Invalid image data or value error. {ve}")
                        results_data.append({
                            "Image Name": image_name, "Prompt": prompt_text, "AnalysisType": selected_analysis_type,
                            "Output": f"Error: Invalid image data - {ve}", "Image Bytes": None
                        })
                    except ConnectionError as ce:
                        st.error(f"API Connection Error while processing '{image_name}': {ce}. Please check your API key and internet connection.")
                        results_data.append({
                            "Image Name": image_name, "Prompt": prompt_text, "AnalysisType": selected_analysis_type,
                            "Output": f"Error: API Connection - {ce}", "Image Bytes": None
                        })
                        break
                    except Exception as e:
                        st.error(f"An unexpected error occurred while processing '{image_name}': {type(e).__name__} - {e}")
                        results_data.append({
                            "Image Name": image_name, "Prompt": prompt_text, "AnalysisType": selected_analysis_type,
                            "Output": f"Error: {type(e).__name__} - {e}", "Image Bytes": None
                        })

                    progress_bar.progress((i + 1) / total_images)

                status_text.text(f"Processed {len(image_files_processed_paths)} of {total_images} images.")
                if results_data:
                    display_analysis_results(results_data, selected_analysis_type)
                else:
                    st.info("No images were processed or no results to display.")


        except zipfile.BadZipFile:
            st.error("❌ The uploaded file is not a valid ZIP archive or is corrupted.")
        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {e}")
        finally:
            cleanup_temp_dir()

# --- Sidebar Information ---
st.sidebar.markdown("---")
st.sidebar.markdown("### About") # About section
st.sidebar.info(
    "This application uses Vision Language Model (VLM) to classify images based on a user-provided text prompt.  "
    "All the user should do is to upload a zip files with the relevant images and provide a text prompt."
) 
st.sidebar.markdown("### What does it mean?") # About section
st.sidebar.info(
    "This app gives you the oporunity to analyze images very fast and search for specific objects in them.\n "
    "You can upload large number of images and get the results in a few seconds.\n"
    "You can find outliers in your data and get a quick overview of the images.", 
) 
st.sidebar.markdown("### How to Use")
st.sidebar.markdown(
    "1.  Open the app and make sure you have 'VLM API Key' configured. (green up here👆)\n"
    "2.  Create a ZIP file containing the images you want to analyze. (only images!)\n"
    "3.  Upload the ZIP file using the uploader. (you can just drag and drop it)\n"
    "4.  Enter a text prompt describing what you want Gemini to do (e.g., describe, categorize, etc.).\n"
    "5.  Click 'Classify Images'. (it will take a while, but it will be worth it)"
    "6.  Download the results as a CSV file. (you can also see the results in the app)"
)
st.sidebar.markdown("### Pro Tips 💪🏽")
st.sidebar.markdown(
    "1.  Make sure you have a clear prompt. (e.g., describe, categorize, etc.)\n"
    "2.  Keep it as simple as possible.\n"
    "3.  Explain yourself to the model, including several examples to help it understand the task.\n"
    "4.  To get clean results, force the model to return a single answer. (example: 'Return just one of the options: dog, cat, cow as output.')\n"
    "5.  For best results, ensure your images are well-lit and in focus. Blurry or dark images can hinder the model's ability to accurately interpret the content."
    "6.  If you're looking for specific details, make sure your prompt highlights them. For instance, instead of just 'describe the car,' try 'describe the make, model, and color of the car.'"
)

# Clean up temp directory on script rerun if it somehow persists
# This is a fallback, primary cleanup is in the processing block
if os.path.exists(TEMP_DIR) and not analyze_button: # Avoid cleaning if processing just finished
    cleanup_temp_dir()
