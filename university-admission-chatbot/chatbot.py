import streamlit as st
import random
from datetime import datetime
import spacy
import logging
import json
from streamlit.components.v1 import html
import sys
import os
from typing import Dict, List, Any, Optional
import threading
import queue
import time

# Configure logging first to catch all initialization issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

# Initialize Streamlit page config early
st.set_page_config(
    page_title="University Admission Chatbot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load NLP model with improved error handling
nlp = None
try:
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        import subprocess
        logging.info("Downloading spaCy language model...")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logging.error(f"Failed to load NLP model: {e}")
    st.error("Failed to initialize NLP capabilities. Please check the logs.")
    st.stop()

class EnhancedAdmissionChatbot:
    def __init__(self):
        self.admission_data = self.load_admission_data()
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
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
            'timeout': [
                "I'm still processing your request. Please wait a moment while I gather the information.",
                "I'm working on your question and will respond shortly.",
                "Just a moment while I retrieve the information you requested."
            ],
            'upload_help': "You can upload documents like transcripts, recommendation letters, or your CV by clicking the 'Upload File' button.",
            'file_types': "I accept PDF, JPG, and PNG files for uploads."
        }
        
    def load_admission_data(self) -> Dict[str, Any]:
        default_data = {
            "deadlines": {
                "undergraduate": "2024-12-15",
                "graduate": "2024-11-30",
                "phd": "2024-10-31",
                "scholarship": "2024-09-15"
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
        
        try:
            if os.path.exists('admission_data.json'):
                with open('admission_data.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default_data
        except Exception as e:
            logging.error(f"Error loading admission data: {e}")
            return default_data
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        if not nlp:
            return {'entities': [], 'intents': [], 'programs': []}
            
        try:
            doc = nlp(query.lower())
        except Exception as e:
            logging.error(f"NLP processing error: {e}")
            return {'entities': [], 'intents': [], 'programs': []}
        
        entities = [ent.text for ent in doc.ents]
        intents = []
        
        intent_keywords = {
            'deadline': ['deadline', 'due', 'when', 'last date', 'cutoff', 'close', 'final date'],
            'documents': ['document', 'paperwork', 'required', 'need', 'submit', 'upload', 'file', 'transcript', 'cv', 'resume', 'certificate'],
            'fees': ['fee', 'payment', 'cost', 'price', 'charge', 'tuition', 'deposit'],
            'status': ['status', 'progress', 'check', 'review', 'decision', 'update', 'track'],
            'help': ['help', 'assistance', 'support', 'guide', 'explain', 'how to', 'what is'],
            'greeting': ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon'],
            'upload': ['upload', 'send', 'submit', 'attach', 'provide'],
            'contact': ['contact', 'email', 'phone', 'number', 'address', 'reach']
        }
        
        for intent, keywords in intent_keywords.items():
            if any(token.text in keywords for token in doc):
                intents.append(intent)
            
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
    
    def get_response(self, user_id: str, query: str) -> str:
        try:
            logging.info(f"Processing query from {user_id}: {query}")
            
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {'messages': []}
            
            message_count = len(self.user_sessions[user_id]['messages'])
            initial_greeting = message_count <= 2
                
            # Create a queue to receive the result from the thread
            result_queue = queue.Queue()
            
            # Start the processing in a separate thread
            processing_thread = threading.Thread(
                target=self._process_query_thread,
                args=(user_id, query, initial_greeting, result_queue)
            )
            processing_thread.start()
            
            # Wait for the result with a 5-second timeout
            try:
                response = result_queue.get(timeout=5)
            except queue.Empty:
                # If timeout occurs, return a temporary response
                response = random.choice(self.general_responses['timeout'])
                # Continue waiting for the actual response in the background
                processing_thread.join()
                if not result_queue.empty():
                    response = result_queue.get()
            
            return response
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "I encountered an error processing your request. Please try again."
    
    def _process_query_thread(self, user_id: str, query: str, initial_greeting: bool, result_queue: queue.Queue):
        try:
            analysis = self.analyze_query(query)
            
            if 'greeting' in analysis['intents'] and initial_greeting:
                result_queue.put(random.choice(self.general_responses['greeting']))
                return
                
            if not analysis['intents']:
                result_queue.put(random.choice(self.general_responses['fallback']))
                return
                
            response = []
            
            for intent in analysis['intents']:
                handler = getattr(self, f'handle_{intent}_query', None)
                if handler:
                    if intent in ['deadline', 'documents', 'fees']:
                        response.append(handler(query, analysis['programs']))
                    elif intent == 'help':
                        response.append(handler(query))
                    else:
                        response.append(handler(user_id))
            
            if not response and analysis['programs']:
                programs = ', '.join(analysis['programs'])
                response.append(f"I can help with information about {programs} programs. Would you like to know about deadlines, required documents, or fees?")
            
            self.user_sessions[user_id]['messages'].append(query)
            
            final_response = "\n\n".join(filter(None, response)) or random.choice(self.general_responses['fallback'])
            result_queue.put(final_response)
        except Exception as e:
            logging.error(f"Error in processing thread: {e}")
            result_queue.put("I encountered an error processing your request. Please try again.")

    def handle_deadline_query(self, query: str, detected_programs: List[str]) -> str:
        try:
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
        except Exception as e:
            logging.error(f"Error handling deadline query: {e}")
            return "I encountered an error while checking deadlines."

    def handle_documents_query(self, query: str, detected_programs: List[str]) -> str:
        try:
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
        except Exception as e:
            logging.error(f"Error handling documents query: {e}")
            return "I encountered an error while checking document requirements."

    def handle_fees_query(self, query: str, detected_programs: List[str]) -> str:
        try:
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
        except Exception as e:
            logging.error(f"Error handling fees query: {e}")
            return "I encountered an error while checking fee information."

    def handle_status_query(self, user_id: str) -> str:
        try:
            if user_id in self.user_sessions and 'documents' in self.user_sessions[user_id]:
                doc_count = len(self.user_sessions[user_id]['documents'])
                return f"Your application is being processed. We've received {doc_count} documents from you."
            return "Your application is currently under review. We'll notify you when there's an update."
        except Exception as e:
            logging.error(f"Error handling status query: {e}")
            return "I encountered an error while checking your application status."

    def handle_help_query(self, query: str) -> str:
        try:
            if 'upload' in query.lower() or 'file' in query.lower():
                return f"{self.general_responses['upload_help']} {self.general_responses['file_types']}"
            
            help_topics = "\n".join([f"- {topic.replace('_', ' ').title()}" 
                                for topic in self.admission_data['faqs'].keys()])
            return f"I can help with:\n{help_topics}\n\nPlease ask about any specific topic."
        except Exception as e:
            logging.error(f"Error handling help query: {e}")
            return "I encountered an error while preparing help information."

    def handle_upload_query(self) -> str:
        try:
            return f"{self.general_responses['upload_help']} {self.general_responses['file_types']}"
        except Exception as e:
            logging.error(f"Error handling upload query: {e}")
            return "I encountered an error while explaining file uploads."

    def handle_contact_query(self) -> str:
        try:
            return self.admission_data['faqs'].get('contact', 
                  "You can contact the admissions office at admissions@university.edu")
        except Exception as e:
            logging.error(f"Error handling contact query: {e}")
            return "I encountered an error while retrieving contact information."

    def allowed_file(self, filename: str) -> bool:
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def handle_file_upload(self, user_id: str, file: Any) -> str:
        try:
            if file and self.allowed_file(file.name):
                filename = file.name
                if 'documents' not in self.user_sessions[user_id]:
                    self.user_sessions[user_id]['documents'] = []
                self.user_sessions[user_id]['documents'].append(filename)
                return f"Document '{filename}' uploaded successfully! We'll process it shortly."
            return "Invalid file type. Please upload PDF, JPG, or PNG files."
        except Exception as e:
            logging.error(f"Error handling file upload: {e}")
            return "I encountered an error processing your upload."

# Initialize chatbot in session state
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = EnhancedAdmissionChatbot()

def get_chat_html() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>University Admission Chatbot</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f7fa;
                color: #333;
            }
            .chat-container {
                max-width: 800px;
                margin: 20px auto;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                background-color: white;
                display: flex;
                flex-direction: column;
                height: 80vh;
            }
            .chat-header {
                background-color: #2c3e50;
                color: white;
                padding: 15px 20px;
                font-size: 18px;
                font-weight: 500;
            }
            .chat-messages {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                background-color: #f9f9f9;
            }
            .message {
                margin-bottom: 15px;
                max-width: 70%;
                padding: 12px 15px;
                border-radius: 18px;
                line-height: 1.4;
                position: relative;
                animation: fadeIn 0.3s ease;
            }
            .user-message {
                background-color: #e3f2fd;
                margin-left: auto;
                border-bottom-right-radius: 5px;
            }
            .bot-message {
                background-color: white;
                margin-right: auto;
                border-bottom-left-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            .chat-input {
                display: flex;
                padding: 15px;
                background-color: white;
                border-top: 1px solid #eee;
            }
            #message-input {
                flex: 1;
                padding: 12px 15px;
                border: 1px solid #ddd;
                border-radius: 25px;
                outline: none;
                font-size: 14px;
            }
            #send-button {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 0 20px;
                margin-left: 10px;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            #send-button:hover {
                background-color: #1a252f;
            }
            .typing-indicator {
                display: inline-block;
                padding: 10px 15px;
                background-color: white;
                border-radius: 18px;
                margin-bottom: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            .typing-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #999;
                margin: 0 2px;
                animation: typingAnimation 1.4s infinite ease-in-out;
            }
            .typing-dot:nth-child(1) {
                animation-delay: 0s;
            }
            .typing-dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            .typing-dot:nth-child(3) {
                animation-delay: 0.4s;
            }
            .upload-btn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 10px 15px;
                margin-left: 10px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s;
            }
            .upload-btn:hover {
                background-color: #2980b9;
            }
            #file-input {
                display: none;
            }
            @keyframes typingAnimation {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-5px); }
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                University Admission Assistant
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message bot-message">Hello! Welcome to University Admission Assistant. How can I help you today?</div>
            </div>
            <div class="chat-input">
                <input type="text" id="message-input" placeholder="Type your message here..." autocomplete="off">
                <button id="send-button">Send</button>
                <button class="upload-btn" id="upload-btn">Upload File</button>
                <input type="file" id="file-input">
            </div>
        </div>

        <script>
            const chatMessages = document.getElementById('chat-messages');
            const messageInput = document.getElementById('message-input');
            const sendButton = document.getElementById('send-button');
            const uploadBtn = document.getElementById('upload-btn');
            const fileInput = document.getElementById('file-input');
            
            // Generate a consistent user ID for the session
            const userId = 'user_' + Math.random().toString(36).substr(2, 9);
            
            function addMessage(text, isUser) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
                messageDiv.textContent = text;
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            function showTypingIndicator() {
                const typingDiv = document.createElement('div');
                typingDiv.className = 'typing-indicator';
                typingDiv.id = 'typing-indicator';
                typingDiv.innerHTML = `
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                `;
                chatMessages.appendChild(typingDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            function hideTypingIndicator() {
                const typingIndicator = document.getElementById('typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }
            
            function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;
                
                addMessage(message, true);
                messageInput.value = '';
                
                showTypingIndicator();
                
                // Send message to Streamlit
                window.parent.postMessage({
                    type: 'USER_MESSAGE',
                    message: message,
                    userId: userId
                }, '*');
            }
            
            function uploadFile(file) {
                addMessage(`Uploading ${file.name}...`, true);
                showTypingIndicator();
                
                // Send file info to Streamlit
                window.parent.postMessage({
                    type: 'FILE_UPLOAD',
                    fileName: file.name,
                    userId: userId
                }, '*');
            }
            
            // Event listeners
            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            uploadBtn.addEventListener('click', () => {
                fileInput.click();
            });
            
            fileInput.addEventListener('change', (e) => {
                if (fileInput.files.length > 0) {
                    uploadFile(fileInput.files[0]);
                }
            });
            
            // Listen for bot responses from Streamlit
            window.addEventListener('message', (event) => {
                if (event.data.type === 'BOT_RESPONSE') {
                    hideTypingIndicator();
                    addMessage(event.data.message, false);
                }
            });
        </script>
    </body>
    </html>
    """

def main():
    # Initialize session state with proper checks
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'component_value' not in st.session_state:
        st.session_state.component_value = None
    
    # Create a container for the chat interface
    with st.container():
        # Inject the HTML chat interface
        html(get_chat_html(), height=600)
    
    # JavaScript to communicate with Streamlit
    js = """
    <script>
        // Listen for messages from the chat interface
        window.addEventListener('message', function(event) {
            // Only accept messages from the same frame
            if (event.source !== window.parent) return;
            
            if (event.data.type === 'USER_MESSAGE' || event.data.type === 'FILE_UPLOAD') {
                // Send message to Streamlit
                Streamlit.setComponentValue(event.data);
            }
        });
    </script>
    """
    html(js)
    
    # Handle messages from the HTML interface with better error handling
    if st.session_state.component_value is not None:
        try:
            msg = st.session_state.component_value
            
            if not isinstance(msg, dict) or 'type' not in msg:
                logging.error(f"Invalid message format: {msg}")
                return
                
            if msg['type'] == 'USER_MESSAGE':
                user_id = msg.get('userId', 'default_user')
                message = msg.get('message', '')
                
                if not message:
                    return
                
                # Add user message to chat history
                st.session_state.chat_history.append(("user", message))
                
                # Get bot response
                bot_response = st.session_state.chatbot.get_response(user_id, message)
                
                # Add bot response to chat history
                st.session_state.chat_history.append(("bot", bot_response))
                
                # Send response back to JS
                js_response = f"""
                <script>
                    window.parent.postMessage({{
                        type: 'BOT_RESPONSE',
                        message: {json.dumps(bot_response)}
                    }}, '*');
                </script>
                """
                html(js_response)
                
            elif msg['type'] == 'FILE_UPLOAD':
                user_id = msg.get('userId', 'default_user')
                file_name = msg.get('fileName', '')
                
                if not file_name:
                    return
                
                # Handle file upload (simulated)
                result = st.session_state.chatbot.handle_file_upload(user_id, type('obj', (), {'name': file_name}))
                
                # Add upload confirmation to chat history
                st.session_state.chat_history.append(("bot", result))
                
                # Send response back to JS
                js_response = f"""
                <script>
                    window.parent.postMessage({{
                        type: 'BOT_RESPONSE',
                        message: {json.dumps(result)}
                    }}, '*');
                </script>
                """
                html(js_response)
            
            # Clear the component value
            st.session_state.component_value = None
            
        except Exception as e:
            logging.error(f"Error processing component message: {e}")
            st.error("An error occurred while processing your message.")

if __name__ == "__main__":
    # Additional check for Streamlit environment
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal error in main execution: {e}")
        st.error("A critical error occurred. Please check the logs and try again.")