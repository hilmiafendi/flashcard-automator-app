# app.py
import streamlit as st
from streamlit_option_menu import option_menu

import main_page
import flashcard_viewer

st.set_page_config(page_title="Flashcard Automation MVP", layout="centered")

with st.sidebar:
    st.image("https://static.vecteezy.com/system/resources/previews/011/670/697/original/flash-card-flat-icon-free-vector.jpg", width=70) # Optional: Gemini logo
    st.markdown("### Flashcard App")
    selected = option_menu(
        menu_title=None, # No menu title
        options=["Main page", "Flashcard viewer"],
        icons=["house", "book"], # Icons for the menu options
        menu_icon="cast", # Icon for the main menu
        default_index=0,
    )

# Logic to display the selected page
if selected == "Main page":
    main_page.main()
elif selected == "Flashcard viewer":
    flashcard_viewer.flashcard_viewer_page()

st.sidebar.markdown("---")
st.sidebar.info("Built with Streamlit and Google Gemini")