# Visual Content Analyzer with VLM

## Overview

This project is a Streamlit web application that leverages Vision Language Model (VLM) for image classification and analysis. Users can upload a folder of images (as a ZIP file) and provide a text prompt (e.g., "What are the objects in this image?", "Categorize these images."). The application then sends each image and the prompt to the API, displaying the VLM's analysis in an interactive GUI.

## Core Functionality

*   **Image Folder Upload (ZIP):** Users can upload a `.zip` file containing multiple image files (e.g., JPG, PNG).
*   **Custom Prompt Input:** A text input field allows users to define the classification task or question for the VLM.
*   **Gemini VLM Integration:** The backend communicates with the Gemini API (specifically `gemini-pro-vision`) to process images and prompts.
*   **Batch Processing:** The application iterates through all valid images in the uploaded folder.
*   **Result Display:** Classified results for each image are presented, including the original image and Gemini's textual response.
*   **Download Results:** Users can download the classification summary as a CSV file.

## Folder Hierarchy

```
|.streamlit/
|  └── config.toml           # Streamlit configuration (e.g., theme)
| app.py                    # Main Streamlit application file
| requirements.txt          # Python dependencies
| .env                      # For storing the Gemini API key (IMPORTANT: Keep this file private)
| utils/
│  ├── __init__.py
│  ├── gemini_utils.py       # Functions for interacting with Gemini API
│  └── image_processing.py   # Placeholder for image handling functions
|data/
|  └── sample_images/        # Placeholder for sample images
|      ├── image1.jpg        # Example (add your own or use provided)
|      └── image2.png        # Example (add your own or use provided)
|README.md                 # This file
```

## Setup and Installation

Follow these steps to set up and run the project locally:

1.  **Clone the Repository (or create files as described):**
    If you cloned this from a repository:
    ```bash
    git clone <repository-url>
    cd visual_content_analyzer
    ```
    If you are setting this up manually, ensure all files from the "Folder Hierarchy" section are in place.

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    Activate the environment:
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Obtain and Configure Gemini API Key:**
    *   Create a new API key. **Keep this key secure and private.**
    *   In the root of your project (`visual_content_analyzer/`), create a file named `.env`.
    *   Add your API key to the `.env` file like this (you can use `.env.example` as a template):
        ```env
        GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"
        # Optional:
        # SHOW_JSON_FORMAT_SPECS="True"
        # SHOW_FULL_PROMPT="False"
        ```
        Replace `"YOUR_ACTUAL_GEMINI_API_KEY_HERE"` with the key you obtained.
        **Do not commit the `.env` file with your actual key to public repositories.** A `.gitignore` file should ideally list `.env`.
    *   The `.env.example` file provides a template for these settings.

## How to Run the Application

1.  **Ensure your virtual environment is activated** (see Step 2 in Setup).
2.  **Make sure your `GEMINI_API_KEY` is correctly set** in your `.env` file (see Step 4 in Setup).
3.  **Navigate to the project root directory** (`visual_content_analyzer/`) in your terminal.
4.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```
    This will typically open the application in your default web browser at `http://localhost:8501`.

## Usage

1.  The application will first check if your Gemini API key is configured. If not, an error message will guide you.
2.  **Upload Images:** Click the "Select a .zip file..." button to upload a ZIP archive containing your image files.
3.  **Enter Prompt:** Modify or use the default prompt in the text area. This prompt guides Gemini on how to analyze the images.
4.  **Classify:** Click the "Classify Images" button.
5.  **View Results:** The application will process each image and display the original image alongside Gemini's textual response. A summary table is also provided.
6.  **Download:** You can download the summary of results as a CSV file.

## Important Notes

*   **API Key Security:** Your Gemini API key is sensitive. Keep it private. The `.env` file method is for local development. For deployment (e.g., to Streamlit f Community Cloud), use their secrets management features.
*   **Rate Limits:** Be mindful of Gemini API rate limits, especially when processing a large number of images.
*   **Error Handling:** The application includes basic error handling. If you encounter issues, check the error messages and your API key setup.
*   **ZIP File Structure:** The application expects a flat structure of images within the ZIP file or images in subfolders. It will recursively find all supported image types.
```
