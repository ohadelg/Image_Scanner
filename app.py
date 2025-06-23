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

# --- Localization & Language State ---
LOCALIZATION = {
    "app_title": {
        "en": "🔍 Visual Content Analyzer with VLM",
        "he": "🔍 מנתח תוכן חזותי עם VLM"
    },
    "app_description": {
        "en": "Upload a **ZIP file** containing your images, provide a classification prompt, and let the model will analyze them!",
        "he": "העלה **קובץ ZIP** המכיל את התמונות שלך, ספק הנחיה לסיווג, ותן למודל לנתח אותן!"
    },
    "api_key_configured_success": {
        "en": "VLM API Key configured successfully.",
        "he": "מפתח ה-API של VLM הוגדר בהצלחה."
    },
    "api_key_error": {
        "en": "**Error configuring Gemini API:** {e}. Please ensure your `VLM_API_KEY` is correctly set in a `.env` file.",
        "he": "**שגיאה בהגדרת Gemini API:** {e}. אנא ודא שמפתח `VLM_API_KEY` שלך מוגדר כראוי בקובץ `.env`."
    },
    "api_key_readme_instructions": {
        "en": "Refer to the `README.md` for instructions on setting up your API key.",
        "he": "עיין בקובץ `README.md` להוראות הגדרת מפתח ה-API שלך."
    },
    "upload_header": {
        "en": "1. Upload Your Image Folder (as a .zip file)",
        "he": "1. העלה את תיקיית התמונות שלך (כקובץ zip.)"
    },
    "zip_uploader_label": {
        "en": "Select a .zip file containing your images.",
        "he": "בחר קובץ zip. המכיל את התמונות שלך."
    },
    "zip_uploader_help": {
        "en": "Ensure the ZIP file contains image files (e.g., .png, .jpg, .jpeg).",
        "he": "ודא שקובץ ה-ZIP מכיל קבצי תמונה (למשל, png, .jpg, .jpeg)."
    },
    "prompt_header": {
        "en": "2. Enter Your Classification Prompt",
        "he": "2. הזן את הנחיית הסיווג שלך"
    },
    "default_prompt_part1": {
        "en": "Describe the main objects in this image and categorize it (e.g., nature, urban, abstract).\n",
        "he": "תאר את האובייקטים העיקריים בתמונה זו וסווג אותה (למשל, טבע, עירוני, מופשט).\n"
    },
    "default_prompt_part2": {
        "en": "Return just one of the options: dog, cat, cow as output.",
        "he": "החזר רק אחת מהאפשרויות: כלב, חתול, פרה כפלט."
    },
    "prompt_text_area_label": {
        "en": "Enter the prompt for VLM to analyze (Don't forget to delete the default prompt):",
        "he": "הזן את ההנחיה ל-VLM לניתוח (אל תשכח למחוק את הנחיית ברירת המחדל):"
    },
    "prompt_text_area_help": {
        "en": "Examples: 'What objects are in this image?', 'Is this image related to nature or urban environments?', 'Categorize these images as animals, plants, or vehicles.'",
        "he": "דוגמאות: 'אילו אובייקטים נמצאים בתמונה זו?', 'האם תמונה זו קשורה לסביבות טבעיות או עירוניות?', 'סווג תמונות אלו כחיות, צמחים או כלי רכב.'"
    },
    "classify_button_label": {
        "en": "Classify Images",
        "he": "סווג תמונות"
    },
    "error_no_zip": {
        "en": "❌ Please upload a ZIP file containing images.",
        "he": "❌ אנא העלה קובץ ZIP המכיל תמונות."
    },
    "error_no_prompt": {
        "en": "❌ Please enter a classification prompt.",
        "he": "❌ אנא הזן הנחיית סיווג."
    },
    "info_processing_images": {
        "en": "🔄 Processing images... This may take a while.",
        "he": "🔄 מעבד תמונות... פעולה זו עשויה להימשך זמן מה."
    },
    "warning_no_valid_images": {
        "en": "⚠️ No valid image files (png, jpg, jpeg, gif, bmp) found in the uploaded ZIP file.",
        "he": "⚠️ לא נמצאו קבצי תמונה חוקיים (png, jpg, jpeg, gif, bmp) בקובץ ה-ZIP שהועלה."
    },
    "status_processing_image": {
        "en": "Processing '{image_name}' ({i}/{total_images})...", # Placeholder for dynamic values
        "he": "מעבד את '{image_name}' ({i}/{total_images})..." # Placeholder for dynamic values
    },
    "error_skip_image_invalid_data": {
        "en": "Skipping '{image_name}': Invalid image data. {ve}", # Placeholder
        "he": "מדלג על '{image_name}': נתוני תמונה לא חוקיים. {ve}" # Placeholder
    },
    "error_api_connection": {
        "en": "API Connection Error while processing '{image_name}': {ce}. Please check your API key and internet connection.", # Placeholder
        "he": "שגיאת חיבור API בעת עיבוד '{image_name}': {ce}. אנא בדוק את מפתח ה-API שלך ואת החיבור לאינטרנט." # Placeholder
    },
    "error_unexpected_processing": {
        "en": "An unexpected error occurred while processing '{image_name}': {e}", # Placeholder
        "he": "שגיאה בלתי צפויה אירעה בעת עיבוד '{image_name}': {e}" # Placeholder
    },
    "status_processed_summary": {
        "en": "Processed {processed_count} of {total_images} images.", # Placeholder
        "he": "עובדו {processed_count} מתוך {total_images} תמונות." # Placeholder
    },
    "info_no_images_processed": {
        "en": "No images were processed or no results to display.",
        "he": "לא עובדו תמונות או שאין תוצאות להצגה."
    },
    "error_bad_zip": {
        "en": "❌ The uploaded file is not a valid ZIP archive or is corrupted.",
        "he": "❌ הקובץ שהועלה אינו ארכיון ZIP חוקי או שהוא פגום."
    },
    "error_unexpected_zip_processing": {
        "en": "An unexpected error occurred during processing: {e}", # Placeholder
        "he": "שגיאה בלתי צפויה אירעה במהלך העיבוד: {e}" # Placeholder
    },
    "results_subheader": {
        "en": "Classification Results:",
        "he": "תוצאות הסיווג:"
    },
    "results_info_no_results": {
        "en": "No results to display.",
        "he": "אין תוצאות להצגה."
    },
    "results_image_caption": { # Used if image bytes available
        "en": "{image_name}", # Placeholder
        "he": "{image_name}" # Placeholder
    },
    "results_could_not_display_image": {
        "en": "Could not display: {image_name}", # Placeholder
        "he": "לא ניתן היה להציג: {image_name}" # Placeholder
    },
    "results_model_output_label": {
        "en": "**Model's Output:**",
        "he": "**פלט המודל:**"
    },
    "results_success_classification_complete": {
        "en": "Classification complete!",
        "he": "הסיווג הושלם!"
    },
    "results_summary_subheader": {
        "en": "Summary of Results:",
        "he": "סיכום התוצאות:"
    },
    "results_download_button_label": {
        "en": "Download Results as CSV",
        "he": "הורד תוצאות כקובץ CSV"
    },
    "sidebar_about_header": {
        "en": "### About",
        "he": "### אודות"
    },
    "sidebar_about_info": {
        "en": "This application uses Vision Language Model (VLM) to classify images based on a user-provided text prompt. All the user should do is to upload a zip files with the relevant images and provide a text prompt.",
        "he": "יישום זה משתמש במודל שפה חזותי (VLM) לסיווג תמונות בהתבסס על הנחיית טקסט המסופקת על ידי המשתמש. כל מה שהמשתמש צריך לעשות הוא להעלות קובץ zip עם התמונות הרלוונטיות ולספק הנחיית טקסט."
    },
    "sidebar_what_does_it_mean_header": {
        "en": "### What does it mean?",
        "he": "### מה זה אומר?"
    },
    "sidebar_what_does_it_mean_info": {
        "en": "This app gives you the oporunity to analyze images very fast and search for specific objects in them.\n You can upload large number of images and get the results in a few seconds.\nYou can find outliers in your data and get a quick overview of the images.",
        "he": "אפליקציה זו נותנת לך את ההזדמנות לנתח תמונות במהירות רבה ולחפש בהן אובייקטים ספציפיים.\n באפשרותך להעלות מספר רב של תמונות ולקבל את התוצאות תוך מספר שניות.\n באפשרותך למצוא חריגים בנתונים שלך ולקבל סקירה מהירה של התמונות."
    },
    "sidebar_how_to_use_header": {
        "en": "### How to Use",
        "he": "### איך להשתמש"
    },
    "sidebar_how_to_use_steps": { # This will be a list of strings for easier processing
        "en": [
            "1.  Open the app and make sure you have 'VLM API Key' configured. (green up here👆)",
            "2.  Create a ZIP file containing the images you want to analyze. (only images!)",
            "3.  Upload the ZIP file using the uploader. (you can just drag and drop it)",
            "4.  Enter a text prompt describing what you want Gemini to do (e.g., describe, categorize, etc.).",
            "5.  Click 'Classify Images'. (it will take a while, but it will be worth it)",
            "6.  Download the results as a CSV file. (you can also see the results in the app)"
        ],
        "he": [
            "1.  פתח את האפליקציה וודא שמפתח ה-API של VLM מוגדר. (ירוק למעלה👆)",
            "2.  צור קובץ ZIP המכיל את התמונות שברצונך לנתח. (רק תמונות!)",
            "3.  העלה את קובץ ה-ZIP באמצעות המעלן. (אפשר פשוט לגרור ולשחרר אותו)",
            "4.  הזן הנחיית טקסט המתארת מה ברצונך ש-Gemini יעשה (למשל, תאר, סווג וכו').",
            "5.  לחץ על 'סווג תמונות'. (זה ייקח זמן, אבל זה יהיה שווה את זה)",
            "6.  הורד את התוצאות כקובץ CSV. (אפשר גם לראות את התוצאות באפליקציה)"
        ]
    },
    "sidebar_pro_tips_header": {
        "en": "### Pro Tips 💪🏽",
        "he": "### טיפים למקצוענים 💪🏽"
    },
    "sidebar_pro_tips_list": { # This will be a list of strings
        "en": [
            "1.  Make sure you have a clear prompt. (e.g., describe, categorize, etc.)",
            "2.  Keep it as simple as possible.",
            "3.  Explain yourself to the model, including several examples to help it understand the task.",
            "4.  To get clean results, force the model to return a single answer. (example: 'Return just one of the options: dog, cat, cow as output.')",
            "5.  For best results, ensure your images are well-lit and in focus. Blurry or dark images can hinder the model's ability to accurately interpret the content.",
            "6.  If you're looking for specific details, make sure your prompt highlights them. For instance, instead of just 'describe the car,' try 'describe the make, model, and color of the car.'"
        ],
        "he": [
            "1.  ודא שיש לך הנחיה ברורה. (למשל, תאר, סווג וכו')",
            "2.  שמור על פשטות ככל האפשר.",
            "3.  הסבר את עצמך למודל, כולל מספר דוגמאות שיעזרו לו להבין את המשימה.",
            "4.  כדי לקבל תוצאות נקיות, אילוץ את המודל להחזיר תשובה אחת. (דוגמה: 'החזר רק אחת מהאפשרויות: כלב, חתול, פרה כפלט.')",
            "5.  לקבלת התוצאות הטובות ביותר, ודא שהתמונות שלך מוארות היטב ובפוקוס. תמונות מטושטשות או כהות עלולות להפריע ליכולת של המודל לפרש את התוכן במדויק.",
            "6.  אם אתה מחפש פרטים ספציפיים, ודא שההנחיה שלך מדגישה אותם. לדוגמה, במקום רק 'תאר את המכונית', נסה 'תאר את היצרן, הדגם והצבע של המכונית.'"
        ]
    },
    "column_image_name": {"en": "Image Name", "he": "שם התמונה"},
    "column_prompt": {"en": "Prompt", "he": "הנחיה"},
    "column_classification": {"en": "Classification", "he": "סיווג"},
    "cleanup_temp_dir_message": {"en": "Cleaned up temporary files.", "he": "ניקוי קבצים זמניים הושלם."}, # For optional debugging
    "cleanup_temp_dir_warning": {"en": "Could not clean up temporary directory {TEMP_DIR}: {e}", "he": "לא ניתן היה לנקות את התיקייה הזמנית {TEMP_DIR}: {e}"} # Placeholder
}

# Initialize language session state
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# --- Language Switcher Callbacks ---
def set_language_en():
    st.session_state.language = 'en'
    st.rerun()

def set_language_he():
    st.session_state.language = 'he'
    st.rerun()

# --- Language Switcher UI ---
# Must be placed early, before elements that use localized text
lang_cols = st.columns([0.05, 0.05, 0.9]) # Adjust ratios as needed for spacing
with lang_cols[0]:
    if st.button("🇺🇸", key="lang_en", on_click=set_language_en, help="Switch to English"):
        pass
with lang_cols[1]:
    if st.button("🇮🇱", key="lang_he", on_click=set_language_he, help="Switch to Hebrew"):
        pass


# --- Global Variables & Setup ---
TEMP_DIR = "temp_uploaded_images"

# --- Helper Functions ---

def localized_text(key, element_type="markdown", **kwargs):
    """
    Retrieves localized text and applies appropriate styling for language.

    Args:
        key (str): The key for the localized string in LOCALIZATION.
        element_type (str): The type of Streamlit element this text is for.
                            Controls how text is rendered (e.g., "markdown", "title",
                            "header", "button", "label", "help").
        **kwargs: Additional arguments to pass to the Streamlit element if needed
                  (e.g., 'unsafe_allow_html' for markdown, 'help' for buttons).
    """
    lang = st.session_state.language

    # Fallback to English if a translation is missing (should not happen with current setup)
    text_dict = LOCALIZATION.get(key, LOCALIZATION.get(key, {}))
    text = text_dict.get(lang, text_dict.get('en', f"MISSING_TRANSLATION_FOR_{key}"))

    if isinstance(text, list): # For lists like sidebar_how_to_use_steps
        processed_list = []
        for item in text:
            item_text = item.format(**kwargs) if kwargs else item # Allow formatting for list items
            processed_list.append(item_text)
        # For lists, we often want to iterate and render them one by one with markdown
        # So, we'll return the list and let the caller handle rendering each item.
        # Or, if a specific "list_markdown" type is needed, it can be added.
        return processed_list


    # Apply formatting if kwargs are provided (e.g. for dynamic error messages)
    try:
        formatted_text = text.format(**kwargs) if kwargs else text
    except KeyError as e:
        # This can happen if a placeholder in the string is not in kwargs
        # print(f"Warning: Missing placeholder {e} for key '{key}' in localized_text. Using raw text.")
        formatted_text = text


    # Default alignment and direction
    align = "left"
    direction = "ltr"
    if lang == 'he':
        align = "right"
        direction = "rtl"

    # Render based on element type
    if element_type == "markdown":
        st.markdown(f"<div style='text-align: {align}; direction: {direction};'>{formatted_text}</div>", unsafe_allow_html=True)
    elif element_type == "title":
        st.markdown(f"<h1 style='text-align: {align}; direction: {direction};'>{formatted_text}</h1>", unsafe_allow_html=True)
    elif element_type == "header":
        st.markdown(f"<h2 style='text-align: {align}; direction: {direction};'>{formatted_text}</h2>", unsafe_allow_html=True)
    elif element_type == "subheader":
        st.markdown(f"<h3 style='text-align: {align}; direction: {direction};'>{formatted_text}</h3>", unsafe_allow_html=True)
    elif element_type == "success":
        # For st.success, st.info, etc., we should use the original Streamlit methods
        # but ensure the text itself is correctly oriented if it contains mixed script.
        # The components themselves are LTR by default. Markdown provides more control.
        if lang == 'he':
             # For RTL, wrapping with a div helps ensure the text block itself is RTL
            st.success(f"{formatted_text}") # Streamlit's success will handle icon
            # To force alignment within the success box (if needed beyond component default):
            # st.markdown(f"<div style='text-align: {align}; direction: {direction};'><span style='color: green;'>✅ {formatted_text}</span></div>", unsafe_allow_html=True)
        else:
            st.success(formatted_text)
    elif element_type == "info":
        if lang == 'he':
            st.info(f"{formatted_text}")
            # st.markdown(f"<div style='text-align: {align}; direction: {direction};'><span style='color: blue;'>ℹ️ {formatted_text}</span></div>", unsafe_allow_html=True)
        else:
            st.info(formatted_text)
    elif element_type == "warning":
        if lang == 'he':
            st.warning(f"{formatted_text}")
            # st.markdown(f"<div style='text-align: {align}; direction: {direction};'><span style='color: orange;'>⚠️ {formatted_text}</span></div>", unsafe_allow_html=True)
        else:
            st.warning(formatted_text)
    elif element_type == "error":
        # st.error handles icons. We mainly pass the formatted text.
        # Forcing RTL within st.error is tricky without full HTML.
        # The text itself should render correctly if it's purely Hebrew.
        st.error(formatted_text, icon="❌")


    # For elements where only the text content needs to be returned
    elif element_type in ["button_label", "download_button_label", "uploader_label", "uploader_help",
                          "text_area_label", "text_area_help", "sidebar_label", "caption", "raw_text"]:
        return formatted_text
    elif element_type == "sidebar_markdown_header": # For sidebar headers like "### About"
        # This will be used by st.sidebar.markdown(localized_text(key, "sidebar_markdown_header"))
        # The markdown itself handles the ###. We just return the text.
        return formatted_text
    else: # Default to markdown if type is unknown
        st.markdown(f"<div style='text-align: {align}; direction: {direction};'>{formatted_text}</div>", unsafe_allow_html=True)


def cleanup_temp_dir():
    """Removes the temporary directory if it exists."""
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
            # localized_text("cleanup_temp_dir_message", "raw_text") # Optional: for debugging
        except Exception as e:
            # Using st.warning directly here as localized_text might not be fully available during early errors
            st.warning(LOCALIZATION["cleanup_temp_dir_warning"][st.session_state.language].format(TEMP_DIR=TEMP_DIR, e=e))


def display_results(results_data):
    """Displays classification results and provides download option."""
    lang = st.session_state.language
    align = "left" if lang == "en" else "right"
    direction = "ltr" if lang == "en" else "rtl"

    if not results_data:
        localized_text("results_info_no_results", "info")
        return

    localized_text("results_subheader", "subheader")
    for i, result in enumerate(results_data):
        # Determine column order based on language
        cols = st.columns([1, 2])
        img_col, text_col = (cols[0], cols[1]) if lang == "en" else (cols[1], cols[0])

        with img_col:
            if result.get("Image Bytes"):
                image_caption_text = localized_text("results_image_caption", "caption", image_name=result["Image Name"])
                st.image(result["Image Bytes"], caption=image_caption_text, width=200)
            else:
                no_display_text = localized_text("results_could_not_display_image", "caption", image_name=result["Image Name"])
                st.caption(no_display_text)
        with text_col:
            localized_text("results_model_output_label", "markdown")
            # Wrap the classification result for directionality and blockquote styling
            # Ensure blockquote border aligns with text direction
            border_side = "border-left" if lang == "en" else "border-right"
            padding_side = "padding-left" if lang == "en" else "padding-right"
            st.markdown(
                f"<div style='text-align: {align}; direction: {direction};'>"
                f"<blockquote style='{border_side}: 5px solid #ccc; {padding_side}: 10px; margin-{align}: 0; margin-{('right' if lang == 'en' else 'left')}: 0; text-align: {align};'>"
                f"{result['Classification']}"
                f"</blockquote></div>",
                unsafe_allow_html=True
            )

        if i < len(results_data) - 1:
            st.markdown("---")

    localized_text("results_success_classification_complete", "success")

    df_results = pd.DataFrame(results_data)

    column_mapping = {
        "Image Name": localized_text("column_image_name", "raw_text"),
        "Prompt": localized_text("column_prompt", "raw_text"),
        "Classification": localized_text("column_classification", "raw_text")
    }

    display_df_columns = ["Image Name", "Prompt", "Classification"]

    # Prepare data for DataFrame, ensuring all items have the necessary keys
    processed_df_data = []
    for item in results_data:
        processed_df_data.append({
            "Image Name": item.get("Image Name", ""),
            "Prompt": item.get("Prompt", ""),
            "Classification": item.get("Classification", "")
        })

    if not processed_df_data: # Handle case where results_data was not empty but all items were malformed
        display_df = pd.DataFrame(columns=display_df_columns).rename(columns=column_mapping)
    else:
        display_df = pd.DataFrame(processed_df_data)[display_df_columns].rename(columns=column_mapping)

    localized_text("results_summary_subheader", "subheader")

    # For st.dataframe, RTL alignment is tricky. Headers are localized.
    # Content alignment will mostly be default.
    # One option for better RTL in dataframe is to convert to HTML and apply styles.
    # For now, we use st.dataframe directly.
    if lang == 'he':
        # For Hebrew, reverse the column order for display to be more natural in RTL
        st.dataframe(display_df[display_df.columns[::-1]])
    else:
        st.dataframe(display_df)

    # Use original English column names for CSV for consistency
    csv_df_to_download = pd.DataFrame(processed_df_data)[display_df_columns]
    csv_data = csv_df_to_download.to_csv(index=False).encode('utf-8')

    st.download_button(
        label=localized_text("results_download_button_label", "download_button_label"),
        data=csv_data,
        file_name="gemini_classification_results.csv",
        mime="text/csv",
    )

# --- Main Application UI ---
localized_text("app_title", "title")
localized_text("app_description", "markdown")

# --- API Key Configuration Check ---
api_key_configured = False
try:
    configure_model() # Attempt to configure Gemini (loads .env)
    get_vision_model() # Check if model can be fetched
    api_key_configured = True
    st.sidebar.success(localized_text("api_key_configured_success", "raw_text"))
except (ValueError, ConnectionError) as e:
    localized_text("api_key_error", "error", e=str(e))
    localized_text("api_key_readme_instructions", "markdown")
    st.stop()

# --- User Inputs ---
localized_text("upload_header", "header")
uploaded_zip_file = st.file_uploader(
    localized_text("zip_uploader_label", "uploader_label"),
    type=["zip"],
    accept_multiple_files=False,
    help=localized_text("zip_uploader_help", "uploader_help")
)

localized_text("prompt_header", "header")
default_prompt_part1 = localized_text("default_prompt_part1", "raw_text")
default_prompt_part2 = localized_text("default_prompt_part2", "raw_text")
default_prompt = default_prompt_part1 + default_prompt_part2

prompt_text = st.text_area(
    localized_text("prompt_text_area_label", "text_area_label"),
    value=default_prompt,
    height=100,
    help=localized_text("prompt_text_area_help", "text_area_help")
)

# --- Process Images Button ---
classify_button = st.button(
    localized_text("classify_button_label", "button_label"),
    type="primary",
    disabled=not api_key_configured
)

# --- Logic for Processing ---
if classify_button:
    if uploaded_zip_file is None:
        localized_text("error_no_zip", "error")
    elif not prompt_text.strip():
        localized_text("error_no_prompt", "error")
    else:
        localized_text("info_processing_images", "info")

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
                        # print(f"Found image: {file}") # Keep for debugging if needed

            if not image_files:
                localized_text("warning_no_valid_images", "warning")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_images = len(image_files)

                for i, image_path in enumerate(image_files):
                    image_name = os.path.basename(image_path)

                    status_msg_template = localized_text("status_processing_image", "raw_text")
                    current_lang_status = st.session_state.language # Use a different var name to avoid conflict
                    align_status = "left" if current_lang_status == "en" else "right"
                    direction_status = "ltr" if current_lang_status == "en" else "rtl"
                    status_text.markdown(
                        f"<div style='text-align: {align_status}; direction: {direction_status};'>{status_msg_template.format(image_name=image_name, i=i + 1, total_images=total_images)}</div>",
                        unsafe_allow_html=True
                    )

                    try:
                        with open(image_path, "rb") as f:
                            image_bytes = f.read()
                        pil_image_bytes = BytesIO(image_bytes)
                        classification_result = classify_image_with_gemini(image_bytes, prompt_text)
                        results_data.append({
                            "Image Name": image_name,
                            "Prompt": prompt_text,
                            "Classification": classification_result,
                            "Image Bytes": pil_image_bytes
                        })
                        image_files_processed_paths.append(image_path)

                    except ValueError as ve:
                        error_text = localized_text("error_skip_image_invalid_data", "raw_text", image_name=image_name, ve=str(ve))
                        localized_text("error_skip_image_invalid_data", "error", image_name=image_name, ve=str(ve))
                        results_data.append({
                            "Image Name": image_name, "Prompt": prompt_text,
                            "Classification": error_text.replace(f"Skipping '{image_name}': ",""), "Image Bytes": None
                        })
                    except ConnectionError as ce:
                        localized_text("error_api_connection", "error", image_name=image_name, ce=str(ce))
                        break
                    except Exception as e:
                        error_text = localized_text("error_unexpected_processing", "raw_text", image_name=image_name, e=str(e))
                        localized_text("error_unexpected_processing", "error", image_name=image_name, e=str(e))
                        results_data.append({
                            "Image Name": image_name, "Prompt": prompt_text,
                            "Classification": error_text.replace(f"An unexpected error occurred while processing '{image_name}': ",""), "Image Bytes": None
                        })
                    progress_bar.progress((i + 1) / total_images)

                summary_msg_template = localized_text("status_processed_summary", "raw_text")
                current_lang_summary = st.session_state.language # Use a different var name
                align_summary = "left" if current_lang_summary == "en" else "right"
                direction_summary = "ltr" if current_lang_summary == "en" else "rtl"
                status_text.markdown(
                    f"<div style='text-align: {align_summary}; direction: {direction_summary};'>{summary_msg_template.format(processed_count=len(image_files_processed_paths), total_images=total_images)}</div>",
                    unsafe_allow_html=True
                )

                if results_data:
                    display_results(results_data)
                else:
                    localized_text("info_no_images_processed", "info")
        except zipfile.BadZipFile:
            localized_text("error_bad_zip", "error")
        except Exception as e:
            localized_text("error_unexpected_zip_processing", "error", e=str(e))
        finally:
            cleanup_temp_dir()

# --- Sidebar Information ---
st.sidebar.markdown("---")
localized_text("sidebar_about_header", element_type="sidebar_label", target=st.sidebar) # Special handling for sidebar
st.sidebar.info(localized_text("sidebar_about_info", "raw_text"))

localized_text("sidebar_what_does_it_mean_header", element_type="sidebar_label", target=st.sidebar)
st.sidebar.info(localized_text("sidebar_what_does_it_mean_info", "raw_text"))

localized_text("sidebar_how_to_use_header", element_type="sidebar_label", target=st.sidebar)
how_to_use_steps = localized_text("sidebar_how_to_use_steps", "raw_text") # Returns a list
for step in how_to_use_steps:
    # Each step is markdown, apply alignment
    lang = st.session_state.language
    align = "left" if lang == "en" else "right"
    direction = "ltr" if lang == "en" else "rtl"
    st.sidebar.markdown(f"<div style='text-align: {align}; direction: {direction};'>{step}</div>", unsafe_allow_html=True)


localized_text("sidebar_pro_tips_header", element_type="sidebar_label", target=st.sidebar)
pro_tips_list = localized_text("sidebar_pro_tips_list", "raw_text") # Returns a list
for tip in pro_tips_list:
    # Each tip is markdown, apply alignment
    lang = st.session_state.language
    align = "left" if lang == "en" else "right"
    direction = "ltr" if lang == "en" else "rtl"
    st.sidebar.markdown(f"<div style='text-align: {align}; direction: {direction};'>{tip}</div>", unsafe_allow_html=True)


# Clean up temp directory on script rerun if it somehow persists
if os.path.exists(TEMP_DIR) and not classify_button:
    cleanup_temp_dir()
