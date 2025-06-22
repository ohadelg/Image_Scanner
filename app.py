# visual_content_analyzer/app.py

import streamlit as st
import os
from PIL import Image
from io import BytesIO
import zipfile
import shutil
import pandas as pd
from utils.gemini_utils import classify_image_with_gemini, configure_model, get_vision_model

# --- Page Configuration ---
st.set_page_config(
    page_title="Visual Content Analyzer with VLM",
    page_icon="🌅",
    layout="wide"
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

def display_results(results_data):
    """Displays classification results and provides download option."""
    if not results_data:
        st.info("No results to display.")
        return

    st.subheader("Classification Results:")
    for i, result in enumerate(results_data):
        col1, col2 = st.columns([1, 2])
        with col1:
            if result.get("Image Bytes"):
                st.image(result["Image Bytes"], caption=result["Image Name"], width=200)
            else:
                st.caption(f"Could not display: {result['Image Name']}")
        with col2:
            # st.write(f"**Prompt:** {result['Prompt']}")
            st.write(f"**Model's Output:**")
            st.markdown(f"> {result['Classification']}") # Using markdown for blockquote
        if i < len(results_data) - 1: # Don't add separator after the last item
            st.markdown("---")

    st.success("Classification complete!")

    # Display results in a DataFrame
    df_results = pd.DataFrame(results_data)
    # Reorder columns for better readability
    if "Image Bytes" in df_results.columns: # Image Bytes not needed in CSV
        display_df = df_results[["Image Name", "Prompt", "Classification"]]
    else:
        display_df = df_results

    st.subheader("Summary of Results:")
    st.dataframe(display_df)

    # Download results as CSV
    csv_data = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results as CSV",
        data=csv_data,
        file_name="gemini_classification_results.csv",
        mime="text/csv",
    )

# --- Main Application UI ---
st.title("🔍 Visual Content Analyzer with VLM")
st.markdown(
    "Upload a **ZIP file** containing your images, provide a classification prompt, "
    "and let the model will analyze them!"
)

# --- API Key Configuration Check ---
api_key_configured = False
try:
    configure_model() # Attempt to configure Gemini (loads .env)
    get_vision_model() # Check if model can be fetched
    api_key_configured = True
    st.sidebar.success("VLM API Key configured successfully.")
except (ValueError, ConnectionError) as e:
    st.error(
        f"**Error configuring Gemini API:** {e}. "
        "Please ensure your `VLM_API_KEY` is correctly set in a `.env` file "
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

st.header("2. Enter Your Classification Prompt")
default_prompt = "Describe the main objects in this image and categorize it (e.g., nature, urban, abstract).\n"
default_prompt += "Return just one of the options: dog, cat, cow as output."
prompt_text = st.text_area(
    "Enter the prompt for VLM to analyze (Don't forget to delete the default prompt):",
    value=default_prompt,
    height=100,
    help="Examples: 'What objects are in this image?', 'Is this image related to nature or urban environments?', 'Categorize these images as animals, plants, or vehicles.'"
)

# --- Process Images Button ---
classify_button = st.button("Classify Images", type="primary", disabled=not api_key_configured)

# --- Logic for Processing ---
if classify_button:
    if uploaded_zip_file is None:
        st.error("❌ Please upload a ZIP file containing images.")
    elif not prompt_text.strip():
        st.error("❌ Please enter a classification prompt.")
    else:
        st.info("🔄 Processing images... This may take a while.")

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
                        pil_image_bytes = BytesIO(image_bytes)

                        classification_result = classify_image_with_gemini(image_bytes, prompt_text)

                        results_data.append({
                            "Image Name": image_name,
                            "Prompt": prompt_text,
                            "Classification": classification_result,
                            "Image Bytes": pil_image_bytes # For display
                        })
                        image_files_processed_paths.append(image_path)

                    except ValueError as ve: # From classify_image_with_gemini if image data is invalid
                        st.error(f"Skipping '{image_name}': Invalid image data. {ve}")
                        results_data.append({
                            "Image Name": image_name,
                            "Prompt": prompt_text,
                            "Classification": f"Error: Invalid image data - {ve}",
                            "Image Bytes": None
                        })
                    except ConnectionError as ce: # From Gemini utils if API key issue arises mid-process
                        st.error(f"API Connection Error while processing '{image_name}': {ce}. Please check your API key and internet connection.")
                        # Optionally break or allow continuing with other images
                        break
                    except Exception as e:
                        st.error(f"An unexpected error occurred while processing '{image_name}': {e}")
                        results_data.append({
                            "Image Name": image_name,
                            "Prompt": prompt_text,
                            "Classification": f"Error: {e}",
                            "Image Bytes": None
                        })

                    progress_bar.progress((i + 1) / total_images)

                status_text.text(f"Processed {len(image_files_processed_paths)} of {total_images} images.")
                if results_data:
                    display_results(results_data)
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
if os.path.exists(TEMP_DIR) and not classify_button: # Avoid cleaning if processing just finished
    cleanup_temp_dir()
