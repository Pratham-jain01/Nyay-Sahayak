import streamlit as st
import json
import time

# --- Configuration ---
PAGE_TITLE = "Nyay Sahayak (Citizen Shield Prototype)"
PAGE_ICON = "⚖️"

# --- Gemini API Configuration ---
# Leave apiKey as ""
# The app will use a built-in proxy in the environment.
API_KEY = "" 
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- 1. The "Law Library" (Our Micro-Knowledge Base) ---
# This is our small, "toy" database of legal information for the prototype.
# In a real app, this would be a massive vector database.
KNOWLEDGE_BASE = {
    "defective_product": {
        "keywords": ["product", "defective", "broken", "item", "purchase", "not working", "consumer", "complaint", "refund", "replace"],
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
        2.  **File a Complaint:** If the issue is not resolved, you can file a complaint with the Consumer Dispute Redressal Commission (Consumer Court).
        3.  **No Lawyer Needed:** You can file the complaint yourself, and the fees are very low. You can do this online through the e-Daakhil portal.
        """
    },
    "bribe_corruption": {
        "keywords": ["bribe", "corruption", "official", "government", "officer", "asking for money", "unlawful", "RTI", "police", "passport"],
        "title": "Prevention of Corruption Act & Right to Information (RTI)",
        "text": """
        If a government official is demanding a bribe or forcing you to do something unlawful, do not pay or comply.
        
        **Your Rights & Actions:**
        1.  **Do Not Pay:** Giving a bribe is also an offense.
        2.  **Gather Evidence (Safely):** If possible, note the official's name, department, and the details of the demand. Do not put yourself in danger.
        3.  **File a Complaint:** You can file a complaint with your state's Anti-Corruption Bureau (ACB) or the Central Vigilance Commission (CVC). This is a serious criminal offense under the Prevention of Corruption Act.
        4.  **Use the RTI Act:** The Right to Information (RTI) Act, 2005 is your most powerful tool. You can file an RTI request online for a fee of just ₹10.
        
        **How to use RTI:**
        * Ask questions like: "What is the official procedure for this service?", "What is the mandated timeline to get this work done?", "Please provide the names and designations of the officers responsible for this delay."
        * This creates an official record and often scares corrupt officials into doing their job.
        """
    },
    "tenant_eviction": {
        "keywords": ["landlord", "tenant", "rent", "eviction", "lease", "agreement", "house", "owner", "kicked out"],
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
        3.  **Seek Legal Advice:** You may need to consult a lawyer or approach the local Rent Control court in your city.
        """
    }
}

# --- 2. The "Clerk" (The Retriever Function) ---
def find_relevant_knowledge(user_query):
    """
    Finds the most relevant knowledge base entry based on keywords.
    This is a simple keyword-matching function. A real app would use vector embeddings.
    """
    user_query = user_query.lower()
    scores = {}
    
    for key, item in KNOWLEDGE_BASE.items():
        score = 0
        for keyword in item["keywords"]:
            if keyword in user_query:
                score += 1
        scores[key] = score
        
    # Find the best-matching key
    best_key = max(scores, key=scores.get)
    if scores[best_key] > 0:
        return KNOWLEDGE_BASE[best_key]
    else:
        # Return a generic fallback if no keywords match
        return {
            "title": "General Inquiry",
            "text": "As an AI legal assistant, I can provide information on specific topics. Please try to be more specific about your problem. For example, you can ask about defective products, issues with landlords, or how to handle a bribe request."
        }

# --- 3. The "Lawyer" (The LLM API Call) ---
async def get_gemini_response(user_query, context):
    """
    Calls the Gemini API with the user's query and the retrieved context.
    Uses an exponential backoff for retries.
    """
    system_prompt = f"""
    You are 'Nyay Sahayak', a friendly and empathetic AI legal assistant for Indian citizens.
    Your goal is to explain complex legal topics in simple, clear, and actionable language.
    
    A user has asked a question. You MUST follow these rules:
    1.  Base your answer *only* on the provided legal context.
    2.  Do not make up any information, laws, or procedures that are not in the context.
    3.  Start by acknowledging the user's problem and showing empathy.
    4.  Structure your answer clearly. Use bullet points and **bold text** for key actions or rights.
    5.  Your tone should be helpful and empowering, not a "legal-ese" robot.
    6.  If the provided context is not sufficient to answer the question, politely state that you can only provide information based on the context you have, and then summarize the context you *do* have.
    7.  End with a clear, positive, and encouraging closing statement.
    
    --- PROVIDED LEGAL CONTEXT ---
    TITLE: {context['title']}
    CONTENT:
    {context['text']}
    ---
    """
    
    # Construct the user's prompt part
    user_prompt = f"""
    User's Question: "{user_query}"
    
    Please answer this question based *only* on the provided legal context.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": user_prompt}]
        }],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }

    max_retries = 5
    delay = 1
    for i in range(max_retries):
        try:
            async with st.session_state.http_session.post(API_URL, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # --- Defensive checks for API response structure ---
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                            return candidate["content"]["parts"][0]["text"]
                        else:
                            st.error("API response is missing the 'content' or 'parts' field. Please check the response structure.")
                            return None
                    else:
                        st.error("API response does not contain 'candidates'. Please check your API key or request.")
                        return None
                else:
                    st.error(f"API Error: {response.status} - {await response.text()}")
                    if response.status == 429 or response.status >= 500: # Retry on rate limiting or server error
                        st.warning(f"Rate limited or server error. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2 # Exponential backoff
                        continue
                    else:
                        return None # Don't retry on other client-side errors
        except Exception as e:
            st.error(f"An exception occurred: {e}")
            time.sleep(delay)
            delay *= 2
    
    st.error("Failed to get a response from the API after several retries.")
    return None

# --- HTTP Session Management (for performance) ---
# We use aiohttp for async API calls in Streamlit
try:
    import aiohttp
    
    # Function to get or create a session
    def get_session():
        if "http_session" not in st.session_state:
            st.session_state.http_session = aiohttp.ClientSession()
        return st.session_state.http_session

    # Function to close the session on script rerun or exit
    def close_session():
        if "http_session" in st.session_state:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(st.session_state.http_session.close())
            del st.session_state.http_session

    # This import is needed for st.rerun() context
    import asyncio
    st.session_state.http_session = get_session()
    
except ImportError:
    st.error("Please install aiohttp to run this app: `pip install aiohttp`")
    st.stop()


# --- 4. The "Interface" (Streamlit UI) ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Header ---
st.title(f"{PAGE_ICON} {PAGE_TITLE}")
st.markdown("I am an AI assistant for Indian citizens. Ask me how to handle a legal problem.")
st.markdown("*(Prototype: My knowledge is limited to consumer rights, bribe requests, and tenant issues.*)")

# --- Display chat messages from history ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Main app logic ---
async def main():
    # React to user input
    if prompt := st.chat_input("How can I help you?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # 1. "Clerk" finds the relevant law
        with st.spinner("Finding the right information..."):
            context = find_relevant_knowledge(prompt)

        # 2. "Lawyer" (LLM) generates the answer
        with st.spinner("Analyzing your situation..."):
            response_text = await get_gemini_response(prompt, context)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            if response_text:
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # Add a "source" section for the judge
                with st.expander("Source of Information (For Demo)"):
                    st.header(context['title'])
                    st.text(context['text'])
            else:
                st.error("I'm sorry, I had trouble generating a response. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
