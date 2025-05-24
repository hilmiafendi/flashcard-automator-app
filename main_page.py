# main_page.py
import streamlit as st
import fitz # PyMuPDF
import io # To handle file in memory
import google.generativeai as genai # For Google Gemini API calls
import json # For JSON parsing
import os # For checking file existence

# --- Configuration ---
FLASHCARDS_FILE = "flashcards.json" # This file will store a dictionary of flashcard sets

# --- Helper Functions ---

def extract_text_from_pdf(pdf_file):
    """
    Extracts text from a PDF file-like object using PyMuPDF.
    Returns a single string containing all text.
    """
    try:
        pdf_bytes = pdf_file.read()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error during PDF text extraction: {e}")
        return None

def generate_flashcards_gemini(question_text_content, answer_text_content):
    """
    Calls Google Gemini 2.0 Flash to generate flashcards by matching
    questions from the question_text_content to answers in the answer_text_content.
    """
    try:
        # Configure Gemini API key from Streamlit secrets
        # Make sure you have a .streamlit/secrets.toml file with:
        # [gemini]
        # api_key = "YOUR_GEMINI_API_KEY"
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        
        model = genai.GenerativeModel('gemini-2.0-flash')

        instruction_prefix = """
        You are an expert at creating concise and effective flashcards for educational purposes.
        You will be provided with two separate texts: one containing exam questions and another containing corresponding answers (scheme answers).

        **Your primary tasks are:**
        1.  **Language Detection:** Detect the primary language of the input (English or Malay) and generate all flashcards strictly in that detected language.
        2.  **Question-Answer Matching:** Carefully match each question from the 'Question Paper' text to its correct answer from the 'Scheme Answer' text.
        3.  **Concept Extraction from Answers:** For each matched answer, thoroughly analyze and extract the main ideas, definitions, dates, names, cause-effect relationships, and any other key concepts. Break down complex answers into digestible points.
        4.  **Flashcard Generation with Types:** From the extracted concepts, generate an array of JSON objects. Each object must contain a 'type', 'front', and 'back' field. Aim for a mix of types where appropriate.

        **Flashcard Types and Format:**
        -   **"definition" cards:**
                -   `front`: "What is X?" or "Define X." (concise question/term)
                -   `back`: A concise definition or explanation.
                -   Example: `{"type": "definition", "front": "What is Photosynthesis?", "back": "The process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water."}`

        -   **"why_how" cards:**
                -   `front`: "Why does X happen?" or "How does Y work?"
                -   `back`: A bullet-point list of the rationale, steps, or causes/effects.
                -   Example: `{"type": "why_how", "front": "Why is photosynthesis important?", "back": ["Produces oxygen for respiration.", "Converts light energy into chemical energy.", "Forms the base of most food chains." ]}`

        -   **"cloze" cards (Cloze Deletions):**
                -   Generate these from sentences or phrases where a key term or concept can be blanked out.
                -   Create **multiple cloze cards from a single sentence** if there are multiple distinct concepts to test.
                -   The 'front' should be the sentence with `___` (three underscores) replacing the blanked term.
                -   The 'back' should be *only* the blanked term.
                -   Example: `{"type": "cloze", "front": "The three stages of photosynthesis are light-dependent reactions, the _____, and the Calvin cycle.", "back": "electron transport chain"}`

        **General Rules:**
        -   If a question has multiple parts (e.g., Q1. (a), (b)), try to create separate flashcards for each part if distinct answers are provided.
        -   Generate as many distinct and useful flashcards as possible.
        -   Strictly adhere to the JSON format. If no clear matches or flashcards can be generated, return an empty array `[]`.

        """
        prompt_message = f"""
        {instruction_prefix}

        Here is the text from the **Question Paper**:
        ```
        {question_text_content}
        ```

        Here is the text from the **Scheme Answer**:
        ```
        {answer_text_content}
        ```

        Now, generate the flashcards by matching questions to answers.
        """

        response = model.generate_content(
            contents=prompt_message,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        json_string = response.text
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from Gemini response. Ensure Gemini generated valid JSON. Error: {e}\nRaw response (first 500 chars): {json_string[:500]}...")
        return []
    except Exception as e:
        st.error(f"An error occurred during Gemini flashcard generation: {e}")
        return []

def save_flashcard_sets(flashcard_sets):
    """Saves all flashcard sets (a dictionary of lists) to a local JSON file."""
    try:
        with open(FLASHCARDS_FILE, "w", encoding="utf-8") as f:
            json.dump(flashcard_sets, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving flashcard sets: {e}")

def load_flashcard_sets():
    """Loads all flashcard sets (a dictionary of lists) from a local JSON file."""
    if os.path.exists(FLASHCARDS_FILE):
        try:
            with open(FLASHCARDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading flashcard sets from {FLASHCARDS_FILE}: {e}")
            return {}
    else:
        return {}

# --- Main Application Function ---
def main():
    st.title("📚 Flashcard Generation (Gemini 2.0 Flash)")
    st.write("Upload your Question Paper and Scheme Answer PDFs to generate smart flashcards!")

    # Initialize session state for flashcard sets (loads existing on startup)
    if 'flashcard_sets' not in st.session_state:
        st.session_state['flashcard_sets'] = load_flashcard_sets()

    # Initialize other necessary session states
    if 'question_text' not in st.session_state:
        st.session_state['question_text'] = ""
    if 'answer_text' not in st.session_state:
        st.session_state['answer_text'] = ""
    if 'last_set_name' not in st.session_state:
        st.session_state['last_set_name'] = "" # To remember the last entered set name

    # --- PDF Upload Widgets ---
    st.subheader("Upload Your PDFs")
    col_q, col_a = st.columns(2)

    with col_q:
        uploaded_question_file = st.file_uploader("Upload Question Paper PDF", type="pdf", key="q_pdf_uploader")
        if uploaded_question_file:
            st.session_state['uploaded_question_pdf'] = uploaded_question_file
            st.success("Question Paper uploaded!")

    with col_a:
        uploaded_answer_file = st.file_uploader("Upload Scheme Answer PDF", type="pdf", key="a_pdf_uploader")
        if uploaded_answer_file:
            st.session_state['uploaded_answer_pdf'] = uploaded_answer_file
            st.success("Scheme Answer uploaded!")

    st.markdown("---")
    st.subheader("Flashcard Set Information")
    set_name = st.text_input("Enter a name for this flashcard set (e.g., 'Physics Midterm Chapter 3')",
                             value=st.session_state['last_set_name'])
    if set_name:
        st.session_state['last_set_name'] = set_name # Remember the last entered set name

    # --- Action Buttons ---
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        generate_button_pressed = st.button("Generate Flashcards", use_container_width=True)
    with col2:
        load_button_pressed = st.button("Load Saved Flashcards", use_container_width=True) # This will now load all sets
    with col3:
        clear_button_pressed = st.button("Clear All Data", use_container_width=True)

    st.markdown("---")

    # --- Logic for handling button presses ---
    if generate_button_pressed:
        if not set_name:
            st.warning("Please enter a name for the flashcard set before generating.")
        elif 'uploaded_question_pdf' in st.session_state and 'uploaded_answer_pdf' in st.session_state:
            st.info("Processing your PDFs...")

            with st.spinner("Extracting text from Question Paper..."):
                question_text = extract_text_from_pdf(st.session_state['uploaded_question_pdf'])
            if question_text:
                st.session_state['question_text'] = question_text
                st.success("Question Paper text extracted.")
            else:
                st.error("Failed to extract text from Question Paper.")

            with st.spinner("Extracting text from Scheme Answer..."):
                answer_text = extract_text_from_pdf(st.session_state['uploaded_answer_pdf'])
            if answer_text:
                st.session_state['answer_text'] = answer_text
                st.success("Scheme Answer text extracted.")
            else:
                st.error("Failed to extract text from Scheme Answer.")

            if question_text and answer_text:
                progress_text = "Gemini is analyzing both documents and generating flashcards. This might take a moment..."
                my_bar = st.progress(0, text=progress_text)

                my_bar.progress(50, text=progress_text)
                
                # Generate cards using Gemini
                cards = generate_flashcards_gemini(question_text, answer_text)
                
                if cards:
                    # Store cards under the specified set name in the session state dictionary
                    st.session_state['flashcard_sets'][set_name] = cards
                    save_flashcard_sets(st.session_state['flashcard_sets']) # Save all sets to file
                else:
                    st.warning("No flashcards generated from the provided content. Try different PDFs or adjust the prompt.")

                my_bar.empty() # Clear the progress bar
                
                if set_name in st.session_state['flashcard_sets'] and st.session_state['flashcard_sets'][set_name]:
                    st.success(f"Successfully generated {len(st.session_state['flashcard_sets'][set_name])} flashcards for set '{set_name}'!")
                    st.markdown("### 🎉 Flashcards Generated!")
                    st.info("Navigate to the **'Flashcard viewer'** page in the sidebar to review your new flashcards.")
                    st.balloons() # A little celebration!
                else:
                    st.warning("No flashcards could be generated. Check PDF content or errors above.")
            else:
                st.error("Text extraction failed for one or both PDFs. Flashcard generation skipped.")
        else:
            st.warning("Please upload both the Question Paper and Scheme Answer PDFs.")

    if load_button_pressed:
        st.session_state['flashcard_sets'] = load_flashcard_sets() # Reload all sets from file
        if st.session_state['flashcard_sets']:
            st.success(f"Loaded {len(st.session_state['flashcard_sets'])} flashcard sets from file!")
            st.info("Navigate to the **'Flashcard viewer'** page in the sidebar to review them.")
        else:
            st.info("No saved flashcard sets found or an error occurred during loading.")
        st.rerun() # Rerun to update the UI with loaded data

    if clear_button_pressed:
        st.session_state['flashcard_sets'] = {} # Clear all sets in session state
        st.session_state['question_text'] = ""
        st.session_state['answer_text'] = ""
        # Clear uploaded files from session state if they exist
        if 'uploaded_question_pdf' in st.session_state:
            del st.session_state['uploaded_question_pdf']
        if 'uploaded_answer_pdf' in st.session_state:
            del st.session_state['uploaded_answer_pdf']
        if 'last_set_name' in st.session_state:
            del st.session_state['last_set_name']
            
        st.success("All current flashcards and session data cleared.")
        
        # Optionally, remove the saved file as well
        if os.path.exists(FLASHCARDS_FILE):
            os.remove(FLASHCARDS_FILE)
            st.info(f"Removed saved flashcards file: {FLASHCARDS_FILE}")
        st.rerun() # Rerun to update the UI

# If main_page.py is run directly, call main()
# (though in a multi-page app, app.py will call it)
if __name__ == "__main__":
    main()