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
    generate_segmentation_html, # Added import for segmentation
    pil_to_base64
)
from ui_sidebar import display_sidebar # Import the new sidebar function
import app_config # Import the new config file

# --- Page Configuration ---
st.set_page_config(
    page_title="Visual Content Analyzer with VLM",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Global Variables & Setup ---
# TEMP_DIR is now sourced from app_config.TEMP_DIR_NAME below, where it's used.

# --- Helper Functions ---
def _process_visual_model_output(
    image_bytes_for_html: BytesIO,
    model_output_text: str,
    html_generation_function, # e.g., generate_point_html
    image_id: str
) -> tuple[str | None, dict | list | None, str | None]:
    """
    Helper to process model output for visual analysis types that produce HTML.
    Parses JSON, generates HTML, and returns HTML, parsed JSON, and any error message.
    """
    html_output_for_display = None
    parsed_json_data = None
    error_message_suffix = None

    if model_output_text and not model_output_text.startswith("Error:") and not model_output_text.startswith("Content blocked"):
        parsed_json_data = parse_gemini_json_output(model_output_text)
        if parsed_json_data:
            try:
                # Re-open image from bytes for HTML generation, as BytesIO can be consumed
                pil_img_for_html = Image.open(BytesIO(image_bytes_for_html.getvalue()))
                html_output_for_display = html_generation_function(pil_img_for_html, parsed_json_data, image_id=image_id)
            except Exception as e:
                # print(f"Error during HTML generation for {image_id}: {e}")
                error_message_suffix = f" (Error during HTML generation: {e})"
        else:
            error_message_suffix = " (Error parsing JSON - Model output was not valid JSON format)"
            # print(f"JSON parsing failed for {image_id}. Raw output: {model_output_text[:500]}...")
    # If model_output_text itself is an error (e.g., "Error: API connection failed"), it will be handled by the caller.
    return html_output_for_display, parsed_json_data, error_message_suffix

def _display_prompt_info(result_item):
    """Helper to display User Prompt and Full Prompt consistently."""
    st.write(f"**User Prompt:**")
    st.markdown(f"> {result_item.get('Prompt', 'N/A')}")
    if result_item.get('Full Prompt') and os.environ.get(app_config.ENV_VAR_SHOW_FULL_PROMPT, "False").lower() == "true":
        with st.expander("View Full Prompt (User + JSON Format)"):
            st.text(result_item.get('Full Prompt', 'N/A'))

def _display_visual_fallback_info(result_item, pil_image_obj, model_output_str, parse_error_indicated, item_idx):
    """Helper to display fallback information when HTML generation fails for visual types."""
    if pil_image_obj:
        st.image(pil_image_obj, caption=f"Base image: {result_item['Image Name']}", width=300)

    # Debug info for parsing and raw output
    expander_title_suffix = f" (Image: {result_item['Image Name']})"
    if parse_error_indicated and not model_output_str.startswith("Error:"):
        st.warning("Could not parse the model's output as valid JSON. Displaying raw output.")
        with st.expander(f"🔍 Debug: View Raw Model Output{expander_title_suffix}"):
            st.text(model_output_str)
    elif model_output_str.startswith("Error:") or model_output_str.startswith("Content blocked"):
        st.error(f"Model Error: {model_output_str}")
    else:
        with st.expander(f"🔍 Debug: View Parsed JSON Data{expander_title_suffix}"):
            if result_item.get("ParsedJSON"):
                st.json(result_item.get("ParsedJSON"))
            else:
                st.text("No parsed JSON data available.")

    st.markdown(f"**Model's Raw Output:**")
    st.text_area("Raw Output", value=model_output_str, height=150, disabled=True, key=f"raw_output_fallback_{item_idx}")

def cleanup_temp_dir():
    """Removes the temporary directory if it exists."""
    if os.path.exists(app_config.TEMP_DIR_NAME):
        try:
            shutil.rmtree(app_config.TEMP_DIR_NAME)
            # st.text("Cleaned up temporary files.") # Optional: for debugging
        except Exception as e:
            st.warning(f"Could not clean up temporary directory {app_config.TEMP_DIR_NAME}: {e}")

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
                _display_prompt_info(result) # Refactored
                st.write(f"**Model's Output (Classification):**")
                st.markdown(f"> {result.get('Output', 'N/A')}")

        elif analysis_type in ["Point to Items", "2D Bounding Boxes", "3D Bounding Boxes", "Segmentation Masks"]: # Added Segmentation Masks here
            model_output_text = result.get('Output', '')
            html_was_generated = bool(result.get("HtmlOutput"))
            json_parse_error_indicated = "(Error parsing JSON)" in model_output_text

            _display_prompt_info(result) # Refactored

            if pil_image and html_was_generated:
                # Adjusted height calculation for better fit, added a bit more buffer
                # Removed the 800px cap to allow taller images to display fully with their annotations.
                # Max height can be controlled by CSS if necessary, but this gives more flexibility.
                component_height = pil_image.height + 150 # Increased buffer from 100 to 150
                st.components.v1.html(result["HtmlOutput"], height=component_height, scrolling=True)
            else: # Fallback if no HTML output or no image
                _display_visual_fallback_info(result, pil_image, model_output_text, json_parse_error_indicated, i)

        # The "Segmentation Masks" specific elif block has been removed as its logic is merged
        # into the consolidated block:
        # elif analysis_type in ["Point to Items", "2D Bounding Boxes", "3D Bounding Boxes", "Segmentation Masks"]:

        # Display raw output for debugging or if HTML failed
        # This condition should now correctly apply to all visual types including Segmentation if HtmlOutput is missing.
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

# analysis_types, user_prompts, json_format_specs, prompt_help_text are now in app_config
selected_analysis_type = st.selectbox(
    "Choose the type of analysis:",
    options=app_config.analysis_types, # Use from app_config
    index=0
)

# Dynamic prompt area based on analysis type
prompt_label = "Enter your instructions for the VLM:"

# Construct default_prompt_text using imported configs
# This remains in app.py as it's derived data based on runtime selections.
default_prompt_text = {
    key: app_config.user_prompts.get(key, "") + "\n" + app_config.json_format_specs.get(key, "")
    for key in app_config.analysis_types
}

if selected_analysis_type == "Image Classification": # This specific type still needs its own label
    prompt_label = "Enter Your Classification Prompt:"

prompt_text = st.text_area(
    label=prompt_label,
    value=app_config.user_prompts.get(selected_analysis_type, "Please provide instructions for the selected analysis type."), # Use from app_config
    height=150,
    help=app_config.prompt_help_text.get(selected_analysis_type, "Provide clear instructions for the AI model.") # Use from app_config
)

# Show the JSON format that will be automatically added
# Use from app_config for keys and values
if selected_analysis_type in app_config.json_format_specs and os.environ.get(app_config.ENV_VAR_SHOW_JSON_SPECS, "False").lower() == "true":
    st.info(f"📋 **JSON Format will be automatically added:**\n{app_config.json_format_specs[selected_analysis_type]}")

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

        # Combine user prompt with JSON format specification from app_config
        full_prompt = prompt_text + "\n" + app_config.json_format_specs.get(selected_analysis_type, "")

        # Ensure temp_dir is clean before use
        cleanup_temp_dir() # Uses app_config.TEMP_DIR_NAME internally now
        os.makedirs(app_config.TEMP_DIR_NAME, exist_ok=True)

        results_data = []
        image_files_processed_paths = []

        try:
            with zipfile.ZipFile(uploaded_zip_file, 'r') as zip_ref:
                zip_ref.extractall(app_config.TEMP_DIR_NAME)

            image_files = []
            for root, _, files in os.walk(app_config.TEMP_DIR_NAME):
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
                        model_to_use = app_config.DEFAULT_GEMINI_MODEL # Use from app_config

                        if selected_analysis_type == "Image Classification":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use)
                            current_result_data["Output"] = model_output

                        elif selected_analysis_type == "Point to Items":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.5})
                            current_result_data["Output"] = model_output
                            html_output_for_display, parsed_json, error_suffix = _process_visual_model_output(
                                BytesIO(image_bytes), model_output, generate_point_html, f"img_{i}"
                            )
                            if parsed_json: current_result_data["ParsedJSON"] = parsed_json
                            if error_suffix: current_result_data["Output"] += error_suffix

                        elif selected_analysis_type == "2D Bounding Boxes":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.2})
                            current_result_data["Output"] = model_output
                            html_output_for_display, parsed_json, error_suffix = _process_visual_model_output(
                                BytesIO(image_bytes), model_output, generate_2d_box_html, f"img_{i}"
                            )
                            if parsed_json: current_result_data["ParsedJSON"] = parsed_json
                            if error_suffix: current_result_data["Output"] += error_suffix

                        elif selected_analysis_type == "3D Bounding Boxes":
                            # May benefit from Pro model, but let's test with default first.
                            # model_to_use = app_config.PRO_GEMINI_MODEL # Use from app_config
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.5})
                            current_result_data["Output"] = model_output
                            # _process_visual_model_output is not used here because generate_3d_box_html takes raw model_output
                            if model_output and not model_output.startswith("Error:") and not model_output.startswith("Content blocked"):
                                pil_img_for_html = Image.open(BytesIO(image_bytes))
                                html_output_for_display = generate_3d_box_html(pil_img_for_html, model_output, image_id=f"img_{i}")
                                # Note: generate_3d_box_html does its own parsing. If it were to return parsed_json,
                                # we could store it in current_result_data["ParsedJSON"] here.

                        elif selected_analysis_type == "Segmentation Masks":
                            model_output = generate_content_with_gemini(image_bytes, full_prompt, model_id=model_to_use, generation_config_params={'temperature': 0.3}) # Adjusted temp
                            current_result_data["Output"] = model_output
                            html_output_for_display, parsed_json, error_suffix = _process_visual_model_output(
                                BytesIO(image_bytes), model_output, generate_segmentation_html, f"img_{i}"
                            )
                            if parsed_json: current_result_data["ParsedJSON"] = parsed_json
                            if error_suffix: current_result_data["Output"] += error_suffix
                            # else: Error or content blocked messages are already in model_output

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

# Clean up temp directory on script rerun if it somehow persists
# This is a fallback, primary cleanup is in the processing block
if os.path.exists(TEMP_DIR) and not analyze_button: # Avoid cleaning if processing just finished
    cleanup_temp_dir()

# Display the sidebar content
display_sidebar()
