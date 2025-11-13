import streamlit as st
import json
import requests  # <-- Using 'requests' for stability
import time

# --- Configuration ---
PAGE_TITLE = "Nyay Sahayak (Citizen Shield Prototype)"
PAGE_ICON = "⚖️"

# --- Gemini API Configuration ---
API_KEY = ""  # Leave as ""
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- 1. The "Law Library" (Our Micro-Knowledge Base) ---
KNOWLEDGE_BASE = {
    "defective_product": {
        "keywords": ["product", "defective", "broken", "item", "purchase", "not working", "consumer", "complaint", "refund", "replace", "laptop", "mixer", "phone"],
        "title": "Consumer Protection Act, 2019",
        "text": """
        If you have purchased a product or service that is defective, not as described, or of poor quality, you have rights under the Consumer Protection Act, 2019.
        
        **Your Rights:**
        1.  **Right to Safety:** To be protected against products that are hazardous to life and property.
        2.  **Right to be Informed:** To be given the facts needed to make an informed choice.
        3.  **Right to Choose:** To be able to select from a range of products and services.
        4.  **Right to be Heard:** Your complaint will be heard and given due consideration.
        
        **What to do:**
        1.  **Contact the Seller:** First, try to resolve the issue with the seller or service provider. Keep records of all communication (bills, emails, messages).
        2.  **File a Complaint:** If the issue is not resolved, you can file a complaint with the Consumer Dispute Redessal Commission (Consumer Court).
        3.  **No Lawyer Needed:** You can file the complaint yourself, and the fees are very low. You can do this online through the e-Daakhil portal.
        """
    },
    "bribe_corruption": {
        "keywords": ["bribe", "corruption", "official", "government", "officer", "asking for money", "unlawful", "RTI", "police", "passport", "file", "papers", "beaten"],
        "title": "Prevention of Corruption Act & Police Complaints",
        "text": """
        If a government official is demanding a bribe, forcing you to do something unlawful, or has mistreated you (like using force), do not just comply.
        
        **Your Rights & Actions:**
        1.  **For Bribes:** Do not pay. This is a serious criminal offense under the Prevention of Corruption Act. You can file a complaint with your state's Anti-Corruption Bureau (ACB).
        2.  **For Mistreatment/Force:** If an officer has used unnecessary force or "beaten" you, this is a grave offense. You have the right to file a formal complaint.
        3.  **How to Complain about Police:** You can file a complaint with a senior police officer (like the Superintendent of Police - SP) or the District Magistrate (DM). You can also approach the State Police Complaints Authority.
        4.  **Use the RTI Act:** The Right to Information (RTI) Act is your most powerful tool. You can file an RTI to ask questions like: "What is the official procedure...?", "What are the rules regarding use of force...?", "Please provide the names of officers on duty...". This creates an official record.
        """
    },
    "tenant_eviction": {
        "keywords": ["landlord", "tenant", "rent", "eviction", "lease", "agreement", "house", "owner", "kicked out", "locks changed", "water", "electricity", "notice"],
        "title": "Your Rights as a Tenant (General Principles)",
        "text": """
        If you are a tenant, your landlord cannot evict you without a valid reason and without following the proper legal procedure.
        
        **Your Rights:**
        1.  **A Valid Reason:** A landlord can only evict a tenant for specific reasons, such as not paying rent, subletting the property without permission, or for their own personal use (this must be proven in court).
        2.  **Proper Notice:** The landlord must give you a formal, written legal notice to vacate. The notice period is usually 15 to 30 days but depends on your rental agreement.
        3.  **No Forcible Eviction:** A landlord CANNOT forcibly throw you out, cut off your electricity or water, or change the locks. This is illegal.
        
        **What to do:**
        1.  **Check Your Agreement:** Review your rental agreement for the notice period and other terms.
        2.  **Do Not Vacate:** If the landlord is using illegal methods, do not leave.
        3.  **Gather Evidence:** Take photos or videos if your landlord cuts off utilities or changes locks.
        4.  **Seek Legal Advice:** You may need to consult a lawyer or approach the local Rent Control court in your city.
        """
    }
}

# --- 2. The "Clerk" (The Retriever Function) ---
def find_relevant_knowledge(user_query):
    """
    Finds the most relevant knowledge base entry based on keywords.
    """
    user_query = user_query.lower()
    scores = {}
    
    for key, item in KNOWLEDGE_BASE.items():
        score = 0
        for keyword in item["keywords"]:
            if keyword in user_query:
                score += 1
        scores[key] = score
        
    best_key = max(scores, key=scores.get)
    if scores[best_key] > 0:
        return KNOWLEDGE_BASE[best_key]
    else:
        # Return a generic fallback if no keywords match
        return {
            "title": "General Inquiry",
            "text": "As an AI legal assistant, I can provide information on specific topics. My knowledge is currently limited to: \n* Consumer rights for defective products.\n* Handling bribe requests or police mistreatment.\n* Landlord and tenant eviction issues.\n\nPlease ask a question about one of these topics."
        }

# --- 3. The "Lawyer" (The LLM API Call) ---
# SYNCHRONOUS FUNCTION using 'requests'
def get_gemini_response(user_query, context):
    """
    Calls the Gemini API using the 'requests' library (synchronous).
    """
    # System prompt to guide the AI
    system_prompt = f"""
    You are 'Nyay Sahayak', a friendly and empathetic AI legal assistant for Indian citizens.
    Your goal is to explain complex legal topics in simple, clear, and actionable language.
    
    A user has asked a question. You MUST follow these rules:
    1.  Base your answer *only* on the provided legal context.
    2.  Do not make up any information, laws, or procedures that are not in the context.
    3.  Start by acknowledging the user's problem and showing empathy. (e.g., "I'm very sorry to hear you are going through this. That sounds like a stressful situation.")
    4.  Structure your answer clearly. Use bullet points and **bold text** for key actions or rights.
    5.  Your tone should be helpful and empowering, not a "legal-ese" robot.
    6.  If the provided context is "General Inquiry", it means you don't have the specific knowledge. Politely state this and list the topics you *can* help with, using the text from the context.
    7.  End with a clear, encouraging closing statement (e.g., "I hope this information helps you understand your rights.")
    
    --- PROVIDED LEGAL CONTEXT ---
    TITLE: {context['title']}
    CONTENT:
    {context['text']}
    ---
    """
    
    # User's query
    user_prompt = f"""
    User's Question: "{user_query}"
    
    Please answer this question based *only* on the provided legal context.
    """
    
    # API payload
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    max_retries = 5
    delay = 1
    
    # Retry loop
    for i in range(max_retries):
        try:
            # Using requests.post() here
            response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                # Defensive checks for API response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                        return candidate["content"]["parts"][0]["text"]
                    else:
                        st.error("API response is missing the 'content' or 'parts' field.")
                        return None
                else:
                    st.error("API response does not contain 'candidates'.")
                    return None
            else:
                # Handle API errors
                st.error(f"API Error: {response.status_code} - {response.text}")
                if response.status_code == 429 or response.status_code >= 500:
                    st.warning(f"Rate limited or server error. Retrying in {delay}s...")
                    time.sleep(delay) # Use time.sleep
                    delay *= 2
                    continue
                else:
                    return None # Don't retry on other client errors
        except requests.exceptions.RequestException as e:
            st.error(f"Connection Error: {e}. Are you connected to the internet?")
            return None
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            time.sleep(delay) # Use time.sleep
            delay *= 2
    
    st.error("Failed to get a response from the API after several retries.")
    return None

# --- 4. The "Interface" (Streamlit UI) ---
# This part is now simple and synchronous (no 'async')

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Header ---
st.title(f"{PAGE_ICON} {PAGE_TITLE}")
st.markdown("I am an AI assistant for Indian citizens. Ask me how to handle a legal problem.")
st.markdown("*(Prototype: My knowledge is limited to consumer rights, police/bribe issues, and tenant issues.*)")

# --- Display chat messages from history ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Main App Logic (No 'async' needed) ---
if prompt := st.chat_input("How can I help you?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. "Clerk" finds the relevant law
    with st.spinner("Finding the right information..."):
        context = find_relevant_knowledge(prompt)

    # 2. "Lawyer" (LLM) generates the answer
    with st.spinner("Analyzing your situation..."):
        # This is now a simple, direct function call
        response_text = get_gemini_response(prompt, context)
    
    # Display assistant response
    with st.chat_message("assistant"):
        if response_text:
            st.markdown(response_text)
            # Add the successful response to history
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # Add a "source" section
            if context['title'] != "General Inquiry":
                with st.expander("Source of Information (For Demo)"):
                    st.header(context['title'])
                    st.text(context['text'])
        else:
            st.error("I'm sorry, I had trouble generating a response. Please try again.")
    
    # Rerun to clear the input box and show the latest messages
    st.rerun()
