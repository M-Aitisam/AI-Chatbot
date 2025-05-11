import streamlit as st
import time
import random
from datetime import datetime, timedelta
import spacy
import os
import logging
import json
from PIL import Image

# Load English language model for NLP
nlp = spacy.load("en_core_web_sm")

# Set page config
st.set_page_config(
    page_title="University Admission Chatbot",
    page_icon="🎓",
    layout="wide"
)

class EnhancedAdmissionChatbot:
    def __init__(self):
        self.admission_data = self.load_admission_data()
        self.user_sessions = {}
        self.setup_logging()
        self.general_responses = {
            'greeting': [
                "Hello! Welcome to University Admission Assistant. How can I help you today?",
                "Hi there! I'm here to help with your university admission questions.",
                "Welcome! Ask me anything about university admissions."
            ],
            'fallback': [
                "I'm sorry, I didn't understand that. I can help with admission deadlines, required documents, fees, and application status.",
                "Could you rephrase that? I specialize in university admission queries.",
                "I'm not sure I follow. I can assist with admission-related questions."
            ],
            'upload_help': "You can upload documents like transcripts, recommendation letters, or your CV using the file uploader below.",
            'file_types': "I accept PDF, JPG, and PNG files for uploads."
        }
        
    def setup_logging(self):
        logging.basicConfig(
            filename='chatbot_analytics.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
    def load_admission_data(self):
        try:
            with open('admission_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "deadlines": {
                    "undergraduate": "2023-12-15",
                    "graduate": "2023-11-30",
                    "phd": "2023-10-31",
                    "scholarship": "2023-09-15"
                },
                "documents": {
                    "undergraduate": ["High school transcripts", "Standardized test scores", 
                                    "Personal statement", "Letters of recommendation"],
                    "graduate": ["Bachelor's degree transcripts", "GRE/GMAT scores", 
                               "Statement of purpose", "Letters of recommendation"],
                    "phd": ["Master's degree transcripts", "Research proposal", 
                          "Publications (if any)", "Letters of recommendation"]
                },
                "fees": {
                    "undergraduate": {"application_fee": 50, "tuition_deposit": 500},
                    "graduate": {"application_fee": 75, "tuition_deposit": 750},
                    "phd": {"application_fee": 100, "tuition_deposit": 0}
                },
                "faqs": {
                    "application_process": "The application process involves submitting an online form, required documents, and paying the application fee. You'll receive a confirmation email once submitted.",
                    "visa_requirements": "International students need to provide proof of financial support, acceptance letter, and valid passport to apply for a student visa.",
                    "housing_options": "We offer on-campus dormitories and can provide information about off-campus housing options.",
                    "contact": "You can reach the admissions office at admissions@university.edu or call +1 (555) 123-4567.",
                    "upload_help": "You can upload documents through our portal after creating an account. Accepted formats are PDF, JPG, and PNG."
                }
            }
    
    def analyze_query(self, query):
        doc = nlp(query.lower())
        
        # Extract entities and intents
        entities = [ent.text for ent in doc.ents]
        intents = []
        
        # Enhanced intent recognition with more keywords
        deadline_keywords = ['deadline', 'due', 'when', 'last date', 'cutoff', 'close', 'final date']
        document_keywords = ['document', 'paperwork', 'required', 'need', 'submit', 'upload', 'file', 'transcript', 'cv', 'resume', 'certificate']
        fee_keywords = ['fee', 'payment', 'cost', 'price', 'charge', 'tuition', 'deposit']
        status_keywords = ['status', 'progress', 'check', 'review', 'decision', 'update', 'track']
        help_keywords = ['help', 'assistance', 'support', 'guide', 'explain', 'how to', 'what is']
        greeting_keywords = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon']
        upload_keywords = ['upload', 'send', 'submit', 'attach', 'provide']
        contact_keywords = ['contact', 'email', 'phone', 'number', 'address', 'reach']
        
        if any(token.text in deadline_keywords for token in doc):
            intents.append('deadline')
        if any(token.text in document_keywords for token in doc):
            intents.append('documents')
        if any(token.text in fee_keywords for token in doc):
            intents.append('fees')
        if any(token.text in status_keywords for token in doc):
            intents.append('status')
        if any(token.text in help_keywords for token in doc):
            intents.append('help')
        if any(token.text in greeting_keywords for token in doc):
            intents.append('greeting')
        if any(token.text in upload_keywords for token in doc):
            intents.append('upload')
        if any(token.text in contact_keywords for token in doc):
            intents.append('contact')
            
        # Check for program types
        program_types = {
            'undergraduate': ['undergrad', 'bachelor', 'undergraduate', 'college'],
            'graduate': ['graduate', 'master', 'masters', 'ms', 'mba'],
            'phd': ['phd', 'doctorate', 'doctoral'],
            'scholarship': ['scholarship', 'financial aid', 'grant']
        }
        
        detected_programs = []
        for program, keywords in program_types.items():
            if any(keyword in query.lower() for keyword in keywords):
                detected_programs.append(program)
                
        return {
            'entities': entities,
            'intents': intents,
            'programs': detected_programs
        }
    
    def get_response(self, user_id, query):
        self.log_interaction(user_id, query)
        
        # Remove greeting for subsequent messages
        if len(self.user_sessions.get(user_id, {}).get('messages', [])) > 2:
            initial_greeting = False
        else:
            initial_greeting = True
            
        analysis = self.analyze_query(query)
        
        # Handle greetings first
        if 'greeting' in analysis['intents'] and initial_greeting:
            return random.choice(self.general_responses['greeting'])
            
        # Handle empty or unclear queries
        if not analysis['intents']:
            return random.choice(self.general_responses['fallback'])
            
        response = ""
        
        # Process each detected intent
        for intent in analysis['intents']:
            if intent == 'deadline':
                response += self.handle_deadline_query(query, analysis['programs']) + "\n\n"
            elif intent == 'documents':
                response += self.handle_documents_query(query, analysis['programs']) + "\n\n"
            elif intent == 'fees':
                response += self.handle_fees_query(query, analysis['programs']) + "\n\n"
            elif intent == 'status':
                response += self.handle_status_query(user_id) + "\n\n"
            elif intent == 'help':
                response += self.handle_help_query(query) + "\n\n"
            elif intent == 'upload':
                response += self.handle_upload_query() + "\n\n"
            elif intent == 'contact':
                response += self.handle_contact_query() + "\n\n"
        
        # If no specific intent matched but we have programs detected
        if not response and analysis['programs']:
            response = f"I can help with information about {', '.join(analysis['programs'])} programs. " \
                      "Would you like to know about deadlines, required documents, or fees?"
        
        return response.strip() if response else random.choice(self.general_responses['fallback'])
    
    def handle_deadline_query(self, query, detected_programs):
        if not detected_programs:
            return "Which program deadline are you interested in? (undergraduate/graduate/phd/scholarship)"
        
        responses = []
        for program in detected_programs:
            if program in self.admission_data['deadlines']:
                deadline = datetime.strptime(self.admission_data['deadlines'][program], "%Y-%m-%d")
                days_left = (deadline - datetime.now()).days
                responses.append(
                    f"The application deadline for {program} program is {deadline.strftime('%B %d, %Y')}. "
                    f"That's {days_left} days from today."
                )
            else:
                responses.append(f"I don't have deadline information for {program} program.")
        
        return "\n".join(responses)
    
    def handle_documents_query(self, query, detected_programs):
        if not detected_programs:
            return "Which program documents are you asking about? (undergraduate/graduate/phd)"
        
        responses = []
        for program in detected_programs:
            if program in self.admission_data['documents']:
                docs = "\n- ".join(self.admission_data['documents'][program])
                responses.append(f"Required documents for {program} program:\n- {docs}")
            else:
                responses.append(f"I don't have document requirements for {program} program.")
        
        return "\n\n".join(responses)
    
    def handle_fees_query(self, query, detected_programs):
        if not detected_programs:
            return "Which program fees are you asking about? (undergraduate/graduate/phd)"
        
        responses = []
        for program in detected_programs:
            if program in self.admission_data['fees']:
                fees = self.admission_data['fees'][program]
                responses.append(
                    f"Fee structure for {program} program:\n"
                    f"- Application fee: ${fees['application_fee']}\n"
                    f"- Tuition deposit (if admitted): ${fees['tuition_deposit']}"
                )
            else:
                responses.append(f"I don't have fee information for {program} program.")
        
        return "\n\n".join(responses)
    
    def handle_status_query(self, user_id):
        if user_id in self.user_sessions and 'documents' in self.user_sessions[user_id]:
            return "Your application is being processed. We've received " \
                  f"{len(self.user_sessions[user_id]['documents'])} documents from you."
        return "Your application is currently under review. We'll notify you when there's an update."
    
    def handle_help_query(self, query):
        if 'upload' in query.lower() or 'file' in query.lower():
            return self.general_responses['upload_help'] + " " + self.general_responses['file_types']
        
        help_topics = "\n".join([f"- {topic.replace('_', ' ').title()}" 
                            for topic in self.admission_data['faqs'].keys()])
        return "I can help with:\n" + help_topics + "\n\nPlease ask about any specific topic."
    
    def handle_upload_query(self):
        return self.general_responses['upload_help'] + " " + self.general_responses['file_types']
    
    def handle_contact_query(self):
        return self.admission_data['faqs'].get('contact', 
              "You can contact the admissions office at admissions@university.edu")
    
    def log_interaction(self, user_id, query):
        logging.info(f"User {user_id}: {query}")
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {'messages': []}
        self.user_sessions[user_id]['messages'].append(query)
    
    def allowed_file(self, filename):
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def handle_file_upload(self, user_id, file):
        if file and self.allowed_file(file.name):
            filename = file.name
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {'documents': []}
            self.user_sessions[user_id]['documents'].append(filename)
            
            return f"Document '{filename}' uploaded successfully! We'll process it shortly."
        return "Invalid file type. Please upload PDF, JPG, or PNG files."

# Initialize chatbot
chatbot = EnhancedAdmissionChatbot()

# Streamlit UI
def main():
    # Custom CSS for the chat interface
    st.markdown("""
    <style>
        .chat-container {
            max-height: 500px;
            overflow-y: auto;
            padding: 10px;
            border-radius: 10px;
            background-color: #f9f9f9;
            margin-bottom: 20px;
        }
        .user-message {
            background-color: #e3f2fd;
            padding: 8px 12px;
            border-radius: 10px;
            margin: 5px 0;
            text-align: right;
            margin-left: 20%;
        }
        .bot-message {
            background-color: #ffffff;
            padding: 8px 12px;
            border-radius: 10px;
            margin: 5px 0;
            text-align: left;
            margin-right: 20%;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .stTextInput>div>div>input {
            border-radius: 20px;
            padding: 10px 15px;
        }
        .stButton>button {
            border-radius: 20px;
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("🎓 University Admission Chatbot")
    st.markdown("Ask me anything about university admissions, deadlines, required documents, or fees.")

    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(random.randint(1000, 9999))

    # Display chat history
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Initial greeting
        if len(st.session_state.chat_history) == 0:
            greeting = random.choice(chatbot.general_responses['greeting'])
            st.session_state.chat_history.append(("bot", greeting))
        
        for sender, message in st.session_state.chat_history:
            if sender == "user":
                st.markdown(f'<div class="user-message">You: {message}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-message">Bot: {message}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # User input
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_input("Type your message:", key="input", placeholder="Ask about admission requirements...")
    with col2:
        send_button = st.button("Send")

    # Handle send button or enter key
    if send_button or user_input:
        if user_input:
            # Add user message to chat history
            st.session_state.chat_history.append(("user", user_input))
            
            # Get bot response
            bot_response = chatbot.get_response(st.session_state.user_id, user_input)
            
            # Add bot response to chat history
            st.session_state.chat_history.append(("bot", bot_response))
            
            # Clear input
            st.session_state.input = ""
            
            # Rerun to update the chat display
            st.rerun()

    # File uploader
    st.markdown("### Upload Documents")
    uploaded_file = st.file_uploader("Choose a file (PDF, JPG, PNG)", type=['pdf', 'jpg', 'jpeg', 'png'])
    if uploaded_file is not None:
        result = chatbot.handle_file_upload(st.session_state.user_id, uploaded_file)
        st.session_state.chat_history.append(("bot", result))
        st.rerun()

if __name__ == "__main__":
    main()cd .