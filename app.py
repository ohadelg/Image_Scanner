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
from app_config import (
    TEMP_DIR,
    ANALYSIS_TYPES,
    USER_PROMPTS,
    JSON_FORMAT_SPECS,
    PROMPT_HELP_TEXT
    # DEFAULT_PROMPT_TEXT removed as it's unused
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Visual Content Analyzer with VLM",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Helper Functions ---
def cleanup_temp_dir():
    """Removes the temporary directory if it exists."""
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
        except Exception as e:
            st.warning(f"Could not clean up temporary directory {TEMP_DIR}: {e}")

def _get_generation_config(analysis_type: str) -> dict | None:
    """Returns specific generation config for an analysis type, if any."""
    if analysis_type == "Point to Items":
        return {'temperature': 0.5}
    elif analysis_type == "2D Bounding Boxes":
        return {'temperature': 0.2}
    elif analysis_type == "3D Bounding Boxes":
        return {'temperature': 0.5}
    # Add other specific configs here if needed for other types
    return None

def _process_single_image(image_bytes: bytes, full_prompt: str, analysis_type: str, model_id: str) -> tuple[str, dict | None, str | None]:
    """
    Processes a single image with Gemini.
    Returns: (model_output, parsed_json_if_applicable, error_message_if_any)
    """
    # Debug logging
    print("=" * 80)
    print("🔍 IMAGE PROCESSING DEBUG LOG")
    print("=" * 80)
    print(f"📁 Analysis Type: {analysis_type}")
    print(f"🤖 Model ID: {model_id}")
    print(f"📝 Full Prompt Length: {len(full_prompt)} characters")
    print(f"📝 Full Prompt Preview: {full_prompt[:200]}...")
    print(f"🖼️  Image Size: {len(image_bytes)} bytes")
    print("-" * 80)
    
    generation_config = _get_generation_config(analysis_type)
    print(f"⚙️  Generation Config: {generation_config}")
    
    model_output = generate_content_with_gemini(
        image_bytes,
        full_prompt,
        model_id=model_id,
        generation_config_params=generation_config
    )
    
    print(f"🤖 Raw Model Output Length: {len(model_output)} characters")
    print(f"🤖 Raw Model Output Preview: {model_output[:200]}...")
    print("-" * 80)

    if model_output and not model_output.startswith("Error:") and not model_output.startswith("Content blocked"):
        if analysis_type in ["Point to Items", "2D Bounding Boxes"]: # Types that expect simple JSON list output
            print(f"🔍 Parsing JSON for {analysis_type}...")
            parsed_json = parse_gemini_json_output(model_output)
            if not parsed_json:
                print(f"❌ JSON parsing failed for {analysis_type}")
                print("=" * 80)
                print("🔍 END IMAGE PROCESSING DEBUG LOG")
                print("=" * 80)
                return model_output + " (Error parsing JSON - Model output was not valid JSON format)", None, "JSON parsing failed"
            else:
                print(f"✅ JSON parsing successful for {analysis_type}")
                print(f"📊 Parsed JSON: {parsed_json}")
                print("=" * 80)
                print("🔍 END IMAGE PROCESSING DEBUG LOG")
                print("=" * 80)
                return model_output, parsed_json, None
        # For 3D Bounding Boxes, HTML generation handles parsing. For Classification/Segmentation, no direct JSON parsing needed here.
        print(f"✅ Model output received for {analysis_type} (no JSON parsing needed)")
        print("=" * 80)
        print("🔍 END IMAGE PROCESSING DEBUG LOG")
        print("=" * 80)
        return model_output, None, None # No direct parsing needed at this stage for these types or handled later
    else:
        print(f"❌ Model error or blocked content: {model_output}")
        print("=" * 80)
        print("🔍 END IMAGE PROCESSING DEBUG LOG")
        print("=" * 80)
        return model_output, None, model_output # Error or blocked content


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
            if pil_image:
                st.image(pil_image, caption=f"Base image: {result['Image Name']}", width=300)
            else:
                st.caption(f"Cannot display image: {result['Image Name']}")

            # Show user prompt
            st.write(f"**User Prompt:**")
            st.markdown(f"> {result.get('Prompt', 'N/A')}")

            # Show full prompt if enabled
            if result.get('Full Prompt') and os.environ.get("SHOW_FULL_PROMPT", "False").lower() == "true":
                with st.expander("View Full Prompt (User + JSON Format)"):
                    st.text(result.get('Full Prompt', 'N/A'))
            
            model_output_segmentation = result.get('Output', 'N/A')
            st.markdown(f"**Model's Output (Segmentation Data):**")
            if model_output_segmentation.startswith("Error:") or model_output_segmentation.startswith("Content blocked") or model_output_segmentation.startswith("Segmentation mask analysis for"):
                st.warning(model_output_segmentation)
            else:
                # Attempt to parse as JSON and pretty-print if successful
                parsed_json_output = parse_gemini_json_output(model_output_segmentation)
                if parsed_json_output:
                    st.json(parsed_json_output)
                else:
                    # If not valid JSON, show as plain text in a code block
                    st.markdown(f"```\n{model_output_segmentation}\n```")
            st.info("Note: Visual rendering of segmentation masks is not yet implemented. Displaying raw model output.")

        # Display raw output for debugging or if HTML failed - this section might be redundant for segmentation now
        # if analysis_type not in ["Image Classification", "Segmentation Masks"] and not result.get("HtmlOutput"):
        #      with st.expander("View Raw Output from Model"):
        #         st.json(result.get('Output', '{}'))
        # Consolidate the raw output display for other types if HTML failed
        elif analysis_type not in ["Image Classification", "Segmentation Masks"] and not result.get("HtmlOutput"):
             # This part is for Point to Items, 2D Bounding Boxes, 3D Bounding Boxes if HTML output failed
             # but was already handled within their specific blocks if json_parse_error_indicated or model_output_text.startswith("Error:")
             # So, this expander might be showing duplicate info or could be refined.
             # For now, let's ensure it doesn't show for segmentation.
            pass # Already handled in the specific blocks for other types


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
# This remains in app.py as it's crucial for app startup and uses st.error/st.stop.
# The success message for the sidebar can be passed or handled if ui_sidebar needs it.
api_key_configured = False
try:
    get_gemini_client() # Attempt to initialize the Gemini client
    api_key_configured = True
    # The success message st.sidebar.success("Gemini API Client initialized successfully.")
    # will be part of the main app structure, or ui_sidebar can be made aware of this state.
    # For now, let's keep it simple: main app handles this sidebar message.
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


# --- Initialize Sidebar ---
from utils.ui_sidebar import display_sidebar
display_sidebar() # Call the function to display sidebar contents

# --- User Inputs ---
st.header("1. Upload Your Image Folder (as a .zip file)")
uploaded_zip_file = st.file_uploader(
    "Select a .zip file containing your images.",
    type=["zip"],
    accept_multiple_files=False,
    help="Ensure the ZIP file contains image files (e.g., .png, .jpg, .jpeg)."
)

st.header("2. Select Analysis Type and Provide Instructions")

# ANALYSIS_TYPES is now imported from app_config
selected_analysis_type = st.selectbox(
    "Choose the type of analysis:",
    options=ANALYSIS_TYPES, # Use imported ANALYSIS_TYPES
    index=0
)

# Dynamic prompt area based on analysis type
prompt_label = "Enter your instructions for the VLM:"

# USER_PROMPTS, JSON_FORMAT_SPECS, DEFAULT_PROMPT_TEXT, PROMPT_HELP_TEXT are now imported from app_config

if selected_analysis_type == "Image Classification":
    prompt_label = "Enter Your Classification Prompt:"

prompt_text = st.text_area(
    label=prompt_label,
    value=USER_PROMPTS.get(selected_analysis_type, "Please provide instructions for the selected analysis type."), # Use imported USER_PROMPTS
    height=150,
    help=PROMPT_HELP_TEXT.get(selected_analysis_type, "Provide clear instructions for the AI model.") # Use imported PROMPT_HELP_TEXT
)

# Show the JSON format that will be automatically added
if selected_analysis_type in JSON_FORMAT_SPECS and os.environ.get("SHOW_JSON_FORMAT_SPECS", "False").lower() == "true":
    st.info(f"📋 **JSON Format will be automatically added:**\n{JSON_FORMAT_SPECS[selected_analysis_type]}") # Use imported JSON_FORMAT_SPECS

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

        # Combine user prompt with JSON format specification (use imported JSON_FORMAT_SPECS)
        full_prompt = prompt_text + "\n" + JSON_FORMAT_SPECS.get(selected_analysis_type, "")

        # Ensure temp_dir is clean before use (TEMP_DIR is imported)
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

                    # Debug logging for image processing
                    print("=" * 80)
                    print(f"🖼️  PROCESSING IMAGE: {image_name}")
                    print(f"📁 Image Path: {image_path}")
                    print(f"📊 Image Index: {i + 1}/{total_images}")
                    print("=" * 80)

                    try:
                        with open(image_path, "rb") as f:
                            image_bytes = f.read() # Read as bytes

                        pil_image_display_bytes = BytesIO(image_bytes) # For storing/displaying in Streamlit

                        current_result_data = {
                            "Image Name": image_name,
                            "Prompt": prompt_text,
                            "Full Prompt": full_prompt,
                            "Image Bytes": pil_image_display_bytes,
                            "AnalysisType": selected_analysis_type,
                            "Output": "Error: Processing failed before model call.", # Default
                            "HtmlOutput": None,
                            "ParsedJSON": None
                        }

                        model_to_use = DEFAULT_MODEL_ID # Could be made configurable per analysis type

                        # Core processing call
                        model_output_raw, parsed_json_data, error_msg = _process_single_image(
                            image_bytes, full_prompt, selected_analysis_type, model_to_use
                        )
                        current_result_data["Output"] = model_output_raw
                        if parsed_json_data:
                            current_result_data["ParsedJSON"] = parsed_json_data

                        # HTML generation based on analysis type and successful processing
                        if not error_msg: # No error from _process_single_image (includes JSON parsing for relevant types)
                            pil_img_for_html = Image.open(BytesIO(image_bytes)) # Re-open for HTML generation
                            if selected_analysis_type == "Point to Items" and parsed_json_data:
                                current_result_data["HtmlOutput"] = generate_point_html(pil_img_for_html, parsed_json_data, image_id=f"img_{i}")
                            elif selected_analysis_type == "2D Bounding Boxes" and parsed_json_data:
                                current_result_data["HtmlOutput"] = generate_2d_box_html(pil_img_for_html, parsed_json_data, image_id=f"img_{i}")
                            elif selected_analysis_type == "3D Bounding Boxes": # generate_3d_box_html takes raw model output
                                current_result_data["HtmlOutput"] = generate_3d_box_html(pil_img_for_html, model_output_raw, image_id=f"img_{i}")
                            # Image Classification and Segmentation Masks do not generate HTML overlays here by default

                        elif selected_analysis_type == "Segmentation Masks" and not model_output_raw.startswith("Error:"):
                            # Special handling for segmentation if we want to update its status
                            # For now, _process_single_image already sets current_result_data["Output"]
                            # If it's the placeholder, it's fine. If it's actual model output, also fine.
                            # The placeholder `f"Segmentation mask analysis for '{image_name}'..."` is now part of the json_spec.
                            # Actual model call will occur.
                            pass


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

# --- Sidebar Information --- is now handled by display_sidebar() from utils.ui_sidebar ---

# Clean up temp directory on script rerun if it somehow persists
# This is a fallback, primary cleanup is in the processing block
if os.path.exists(TEMP_DIR) and not analyze_button: # Avoid cleaning if processing just finished
    cleanup_temp_dir()
