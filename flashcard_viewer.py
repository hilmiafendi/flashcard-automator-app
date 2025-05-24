# flashcard_viewer.py
import streamlit as st
import random
import os
import json
import google.generativeai as genai

# --- Configuration ---
FLASHCARDS_FILE = "flashcards.json"

# --- Helper Functions ---

def configure_gemini():
    """
    Configures the Google Gemini API.
    Stops the app if API key is not found in Streamlit secrets.
    """
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        return genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        st.error(f"Gemini API configuration failed. Check .streamlit/secrets.toml. Error: {e}")
        st.stop()

def load_flashcard_sets():
    """Loads all flashcard sets from a local JSON file."""
    if os.path.exists(FLASHCARDS_FILE):
        try:
            with open(FLASHCARDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load flashcard sets: {e}")
            return {}
    return {}

def initialize_flashcard_viewer_state(selected_flashcards):
    """
    Initializes or resets the session state for the flashcard viewer when a new set is selected.
    This ensures that when switching sets, the view starts fresh.
    """
    # Use a unique identifier for the current set to prevent unnecessary resets
    # If the content of the selected_flashcards list changes, this hash will change.
    current_set_id = hash(json.dumps(selected_flashcards, sort_keys=True))

    # Only re-initialize if the selected set's content has changed
    if "current_set_hash" not in st.session_state or st.session_state["current_set_hash"] != current_set_id:
        st.session_state["current_set_hash"] = current_set_id
        st.session_state["flashcards_current_set"] = selected_flashcards

        # Reset viewer state when a new set is selected or initialized
        st.session_state["current_card_index"] = 0
        st.session_state["show_answer"] = False
        st.session_state["chat_history"] = []
        st.session_state["current_flashcard_context"] = "" # Context for AI chat for this specific card

        # Only shuffle if there are cards to shuffle
        if selected_flashcards:
            st.session_state["shuffled_cards"] = random.sample(range(len(selected_flashcards)), len(selected_flashcards))
        else:
            st.session_state["shuffled_cards"] = []
        
        # Trigger a rerun immediately to display the first card of the new set
        st.rerun()


def render_flashcard(current_card, total_cards, current_index_display):
    """Renders a single flashcard with its question and optionally the answer."""
    st.subheader(f"Flashcard {current_index_display + 1} / {total_cards}")
    st.markdown(f"**Type:** `{current_card.get('type', 'N/A')}`")
    st.markdown("---")
    st.markdown("<h3 style='text-align: center; color: #306998;'>❓ Question:</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 1.2em; font-weight: bold;'>{current_card.get('front', 'N/A')}</p>", unsafe_allow_html=True)

    if st.session_state["show_answer"]:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: #4CAF50;'>✅ Answer:</h3>", unsafe_allow_html=True)
        back = current_card.get("back", "N/A")
        if isinstance(back, list):
            for item in back:
                st.markdown(f"<p style='text-align: center; font-size: 1.1em;'>- {item}</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='text-align: center; font-size: 1.1em;'>{back}</p>", unsafe_allow_html=True)

        render_ai_chat(current_card, back)

def render_ai_chat(current_card, back_content):
    """Renders the AI chat interface for the current flashcard."""
    st.markdown("---")
    with st.expander("💬 Ask AI about this Flashcard"):
        st.info("Ask AI for more detail about this question/answer.")

        # Show previous Q&A
        for message in st.session_state["chat_history"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Your question to AI...", key=f"ai_chat_input_{st.session_state['current_flashcard_context']}"):
            # Append user follow-up
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Build full conversation context for the AI
            history = ""
            for msg in st.session_state["chat_history"]:
                speaker = "User" if msg["role"] == "user" else "Assistant"
                history += f"{speaker}: {msg['content']}\n"
            history += f"Flashcard Question: {current_card.get('front', 'N/A')}\n"
            history += f"Flashcard Answer: {back_content}\n"

            with st.spinner("AI is thinking..."):
                try:
                    ai_response = st.session_state["gemini"].generate_content(
                        history + "Now, answer the user's most recent question concisely (max 3 sentences)."
                    )
                    response = ai_response.text
                    # Append AI response
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.markdown(response)
                except Exception as e:
                    error_msg = f"Sorry, AI request failed: {e}. Please check your API key or try again later."
                    st.session_state["chat_history"].append({"role": "assistant", "content": error_msg})
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)

            st.rerun() # Rerun to show the new chat message

def navigation_controls(total_cards):
    """Renders buttons for flashcard navigation (previous, shuffle, show answer, next)."""
    col1, col2, col3, col4 = st.columns(4)

    if total_cards == 0:
        return # No controls if no cards are loaded

    with col1:
        if st.button("⏪ Previous Card", use_container_width=True):
            st.session_state["current_card_index"] = (st.session_state["current_card_index"] - 1) % total_cards
            st.session_state["show_answer"] = False
            st.session_state["chat_history"] = []
            st.rerun()

    with col2:
        if st.button("🔄 Shuffle Cards", use_container_width=True):
            st.session_state["shuffled_cards"] = random.sample(range(total_cards), total_cards)
            st.session_state["current_card_index"] = 0
            st.session_state["show_answer"] = False
            st.session_state["chat_history"] = []
            st.rerun()

    with col3:
        if st.button("👁️ Show Answer", use_container_width=True):
            st.session_state["show_answer"] = True

    with col4:
        if st.button("⏩ Next Card", use_container_width=True):
            st.session_state["current_card_index"] = (st.session_state["current_card_index"] + 1) % total_cards
            st.session_state["show_answer"] = False
            st.session_state["chat_history"] = []
            st.rerun()

# --- Main Application Logic ---

def flashcard_viewer_page():
    """
    Main function for the Flashcard Viewer page.
    Manages switching between dashboard view and individual flashcard review view.
    """
    st.title("✨ Interactive Flashcard Viewer")

    # Initialize Gemini model once
    if "gemini" not in st.session_state:
        st.session_state["gemini"] = configure_gemini()

    # --- View Management ---
    # Use session state to control which part of the UI is shown
    if "viewer_current_view" not in st.session_state:
        st.session_state["viewer_current_view"] = "dashboard" # Default view
    if "selected_set_name" not in st.session_state:
        st.session_state["selected_set_name"] = None # No set selected initially

    all_flashcard_sets = load_flashcard_sets()

    if st.session_state["viewer_current_view"] == "dashboard":
        display_dashboard_view(all_flashcard_sets)
    elif st.session_state["viewer_current_view"] == "flashcard_review":
        display_flashcard_review_view(all_flashcard_sets)

    st.markdown("---")
    # st.info("Use the sidebar to switch between 'Main page' and 'Flashcard viewer'.") # Redundant if using app.py sidebar

def display_dashboard_view(all_flashcard_sets):
    """
    Renders the dashboard view, showing all available flashcard sets as clickable cards.
    """
    st.write("Select a flashcard set to start reviewing:")

    if not all_flashcard_sets:
        st.info("No flashcard sets found. Please generate some from the 'Main page'.")
        return

    # Create a grid-like layout for the cards
    cols_per_row = 3 # Adjust as needed for desired layout
    set_names = list(all_flashcard_sets.keys())
    num_sets = len(set_names)
    num_rows = (num_sets + cols_per_row - 1) // cols_per_row # Ceiling division for rows

    for i in range(num_rows):
        cols = st.columns(cols_per_row) # Create columns for each row
        for j in range(cols_per_row):
            set_index = i * cols_per_row + j
            if set_index < num_sets:
                set_name = set_names[set_index]
                cards_in_set = all_flashcard_sets[set_name]
                num_cards = len(cards_in_set)

                with cols[j]: # Place content in the current column
                    with st.container(border=True): # Use a container with border for the card effect
                        st.subheader(f"🗂️ {set_name}") # Set name as subheader
                        st.markdown(f"**Cards:** {num_cards}") # Display number of cards
                        st.markdown("---") # Separator
                        st.markdown("Ready to review!") # Small message

                        # Button to open the set
                        if st.button(f"Open Set", key=f"open_set_{set_name}", use_container_width=True):
                            st.session_state["selected_set_name"] = set_name # Store selected set name
                            st.session_state["viewer_current_view"] = "flashcard_review" # Switch to review view
                            st.rerun() # Trigger a rerun to display the review view

def display_flashcard_review_view(all_flashcard_sets):
    """
    Renders the individual flashcard review view for the selected set.
    """
    selected_set_name = st.session_state["selected_set_name"]

    # Add a "Back to Sets" button at the top of the review view
    if st.button("⬅️ Back to All Sets"):
        st.session_state["viewer_current_view"] = "dashboard" # Switch back to dashboard
        st.session_state["selected_set_name"] = None # Clear selected set
        st.session_state["flashcards_current_set"] = [] # Clear current flashcards
        st.session_state["current_set_hash"] = None # Clear hash for a clean start on next set selection
        st.rerun() # Trigger a rerun to display the dashboard

    st.header(f"Set: {selected_set_name}") # Display the name of the current set
    st.write("Review your flashcards below.")

    selected_flashcards = all_flashcard_sets.get(selected_set_name, [])

    if not selected_flashcards:
        st.warning(f"The selected set '{selected_set_name}' is empty or not found. Please go back and select another set or generate new flashcards.")
        return

    # Initialize or reset flashcard viewer specific state for the selected set
    initialize_flashcard_viewer_state(selected_flashcards)
    flashcards_for_display = st.session_state["flashcards_current_set"]
    total_cards = len(flashcards_for_display)

    # Ensure shuffled_cards is valid and up-to-date for the current set size
    # This might be redundant due to initialize_flashcard_viewer_state, but serves as a safeguard.
    if "shuffled_cards" not in st.session_state or len(st.session_state["shuffled_cards"]) != total_cards:
         st.session_state["shuffled_cards"] = random.sample(range(total_cards), total_cards)
         st.session_state["current_card_index"] = 0
         # No rerun here, as initialize_flashcard_viewer_state already triggers it if needed.

    current_index_in_shuffled = st.session_state["current_card_index"]
    actual_card_index = st.session_state["shuffled_cards"][current_index_in_shuffled]
    current_card = flashcards_for_display[actual_card_index]

    # Reset chat history when card changes
    # The context key now includes the set name to distinguish contexts between different sets.
    context_key = f"{selected_set_name}_{current_card.get('front','')}_{current_card.get('back','')}"
    if st.session_state["current_flashcard_context"] != context_key:
        st.session_state["current_flashcard_context"] = context_key
        st.session_state["chat_history"] = []
        st.session_state["show_answer"] = False # Hide answer automatically when card changes

    st.markdown("---")
    with st.container(border=True): # Display the current flashcard within a bordered container
        render_flashcard(current_card, total_cards, current_index_in_shuffled)
    st.markdown("---")
    navigation_controls(total_cards)


# Entry point when flashcard_viewer.py is run directly
if __name__ == "__main__":
    flashcard_viewer_page()