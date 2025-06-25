# visual_content_analyzer/utils/ui_sidebar.py

import streamlit as st

def display_sidebar():
    """Displays the sidebar content for the Streamlit application."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "This application uses Vision Language Model (VLM) to classify images based on a user-provided text prompt.  "
        "All the user should do is to upload a zip files with the relevant images and provide a text prompt."
    )
    st.sidebar.markdown("### What does it mean?")
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
        "5.  Click 'Analyze Images'. (it will take a while, but it will be worth it)\n" # Changed Classify to Analyze
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

    # Placeholder for API key status, if we want to move that check display here too.
    # For now, API key status is checked and displayed in the main app.py.
    # If get_gemini_client is imported here, it might create circular dependency issues
    # if gemini_utils also needs config from app_config that ui_sidebar might eventually need.
    # Keeping API status in app.py is fine.
    # Example:
    # api_key_status = st.session_state.get("api_key_configured", False)
    # if api_key_status:
    #     st.sidebar.success("Gemini API Client initialized.")
    # else:
    #     st.sidebar.error("Gemini API Client not configured.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Visual Content Analyzer v1.0") # Example version or footer
