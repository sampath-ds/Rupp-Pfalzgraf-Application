import streamlit as st
from pymongo import MongoClient
import pandas as pd
from dotenv import load_dotenv
import os
import openai
import chatbot  # Import the chatbot module
import dashboard  # Import the dashboard module
from openai import OpenAI

# Set page configuration (must be the first Streamlit command)
st.set_page_config(page_title="Data Visionaries", page_icon=":bar_chart:", layout="wide")



# MongoDB setup
mongo_url = "MONGODB URL HERE"
mongo_client = MongoClient(mongo_url)
database = mongo_client["RAG"]


# OpenAI client setup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)

# Fetch data (placeholder for the actual implementation)
def fetch_collection_as_df(collection_name):
    collection = database[collection_name]
    return pd.DataFrame(list(collection.find()))

# Home Page
def home_page():
    st.title("Welcome to Data Visionaries")
    st.markdown("""
        **Choose a section to explore:**
        - **Chatbot:** Interact with a smart AI assistant for queries.
        - **Dashboard:** Visualize and analyze the firm's data.
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Go to Chatbot"):
            st.session_state.page = "chatbot"

    with col2:
        if st.button("Go to Dashboard"):
            st.session_state.page = "dashboard"

# Navigation Buttons with Home Button/Logo
def navigation_buttons():
    col1, col2 = st.columns([8.5, 1.5])  # Home button/logo on the left
    with col1:
        if st.button("🏠 Home"):
            st.session_state.page = "home"
    return

# Main App Logic
def main():
    # Initialize session state for page navigation
    if "page" not in st.session_state:
        st.session_state.page = "home"

    # Navigation logic
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "chatbot":
        navigation_buttons()  # Add Home button at the top
        chatbot.chatbot_page(database)  # Call the chatbot function
    elif st.session_state.page == "dashboard":
        navigation_buttons()  # Add Home button at the top
        dashboard.dashboard_page(database)  # Call the dashboard function

if __name__ == "__main__":
    main()
