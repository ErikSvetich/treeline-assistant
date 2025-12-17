import streamlit as st
import google.generativeai as genai
import boto3
from boto3.dynamodb.conditions import Key
import time
import uuid

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Tree Line Assistant", page_icon="🌲")

# Initialize Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize DynamoDB (Connects using secrets)
if "AWS_ACCESS_KEY_ID" in st.secrets:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name='us-west-2', # CHANGE THIS TO YOUR AWS REGION
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
    )
    table = dynamodb.Table('TreelineMemory')

# --- PERSONA DEFINITIONS ---
PERSONAS = {
    "🌲 Tree Line Data (Business)": """
        You are the Chief Data Architect for Tree Line Data. 
        Your goal is to optimize for scalable data architecture and consulting deliverables.
        Do not default to agreement. Challenge premises. Identify edge cases. 
        Use a 'Stated Assumptions & Confidence' format.
    """,
    "👟 Nike HR (Analytics)": """
        You are a Technical Lead in People Analytics. 
        Focus on enterprise SQL, data privacy (GDPR/CCPA), and HR metrics.
        Be professional, corporate, and precise.
    """,
    "🎮 Indie Game Dev": """
        You are a Lead Game Designer for a retro-aesthetic indie game. 
        Focus on gameplay loops, pixel art logic, and Godot/Unity implementation.
        Be creative, enthusiastic, and technically detailed.
    """
}

# --- FUNCTIONS ---
def get_session_id():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

def load_chat_history(session_id):
    try:
        response = table.query(
            KeyConditionExpression=Key('SessionID').eq(session_id)
        )
        return response.get('Items', [])
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        return []

def save_message(session_id, role, content, persona):
    try:
        timestamp = int(time.time() * 1000)
        table.put_item(
            Item={
                'SessionID': session_id,
                'Timestamp': timestamp,
                'Role': role,     # 'user' or 'model'
                'Content': content,
                'Persona': persona
            }
        )
    except Exception as e:
        st.error(f"Failed to save message: {e}")

# --- MAIN UI ---
def main():
    st.title("Tree Line AI 🌲")
    
    # Sidebar for Persona Selection
    selected_persona = st.sidebar.selectbox("Active Agent", list(PERSONAS.keys()))
    
    # Initialize Session
    session_id = get_session_id()
    
    # Load history from DB (or session state if DB fails)
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Optional: Load previous context from DB here if you want persistence across reloads

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("How can I help you?"):
        # 1. Display User Message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(session_id, "user", prompt, selected_persona)

        # 2. Generate Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                # Construct the full prompt context
                system_prompt = PERSONAS[selected_persona]
                model = genai.GenerativeModel('gemini-pro')
                
                # We send the system prompt + the user query
                # For a true chat history, you'd append previous messages here
                full_response = model.generate_content(f"System: {system_prompt}\n\nUser: {prompt}")
                
                response_text = full_response.text
                message_placeholder.markdown(response_text)
                
                # 3. Save Assistant Response
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                save_message(session_id, "model", response_text, selected_persona)
                
            except Exception as e:
                message_placeholder.error(f"Error: {e}")

if __name__ == "__main__":
    main()