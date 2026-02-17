import streamlit as st
import google.generativeai as genai
import time
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="論理と仏教の対話",
    page_icon="🙏",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- CSS for Mobile Optimization ---
st.markdown(
    """
    <style>
    .stChatInput {
        position: fixed;
        bottom: 0;
        z-index: 1000;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- API Key Handling ---
def configure_api_key():
    api_key = None
    # Try fetching from Streamlit secrets
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        # Fallback: Input in sidebar (useful for local dev without secrets.toml)
        with st.sidebar:
            st.header("設定")
            api_key = st.text_input("Gemini API Key", type="password")
            if not api_key:
                st.warning("APIキーを入力してください。")
                return None
    return api_key

api_key = configure_api_key()

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"APIキーの設定に失敗しました: {e}")
        st.stop()
else:
    st.info("👈 サイドバーでAPIキーを設定するか、secrets.tomlを作成してください。")
    st.stop()


# --- Persona Definitions ---
PERSONA_LOGICIAN = """
あなたは冷徹な論理学者です。
感情や宗教的観念を排し、事実、統計、論理的整合性のみを重視して議論します。
相手の曖昧な定義や非科学的な主張を鋭く指摘してください。
口調は断定的で、理知的です。
"""

PERSONA_ELDER = """
あなたは慈悲深いテーラワーダ仏教の長老です。
論理を超えた心の平安、執着の手放し、無常、苦（ドゥッカ）の解決を重視して議論します。
相手の攻撃的な論理を柔和に受け流し、真理へと導くように諭してください。
口調は穏やかで、落ち着いています。
"""

model_name = "gemini-2.5-flash"

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_debating" not in st.session_state:
    st.session_state.is_debating = False
if "topic" not in st.session_state:
    st.session_state.topic = ""


# --- Helper Functions ---
def generate_response(persona, history, prompt_text):
    """Generates a response from the specific persona using Gemini."""
    try:
        model = genai.GenerativeModel(model_name)
        
        # Construct context from history for the model
        # We need to inform the model who it is and what the conversation has been so far.
        # However, for simplicity and stability in a multi-persona debate, 
        # we can feed the last few turns and the system instruction.
        
        # Create a simplified history string for context
        context_str = ""
        for msg in history[-4:]: # Keep last few context to allow flow but avoid overflow if long
            context_str += f"{msg['role']}: {msg['content']}\n"
        
        full_prompt = f"""
        {persona}
        
        これまでの議論の流れ:
        {context_str}
        
        相手の直前の発言（あるいはテーマ）に対して、あなたの立場から短く簡潔（150文字程度）に反論または意見を述べてください。
        直前の発言: {prompt_text}
        """

        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return "（思考が中断されました）"


# --- UI Layout ---
st.title("論理 vs 仏教 🧘‍♂️⚡️📐")
st.caption("AI同士の異種格闘技戦を観戦しよう")

# User Input
if not st.session_state.is_debating:
    with st.form("topic_form"):
        user_topic = st.text_input("議論のテーマを入力してください", placeholder="例：AIに意識は宿るか、幸福とは何か")
        submitted = st.form_submit_button("議論開始", use_container_width=True)
        
        if submitted and user_topic:
            st.session_state.topic = user_topic
            st.session_state.chat_history = [] # Reset history
            st.session_state.chat_history.append({"role": "user", "name": "観客", "content": f"テーマ: 「{user_topic}」について議論してください。"})
            st.session_state.is_debating = True
            st.rerun()

# Display Chat History
for msg in st.session_state.chat_history:
    avatar = "👤"
    if msg.get("name") == "論理学者":
        avatar = "📐"
    elif msg.get("name") == "長老":
        avatar = "🙏"
    
    with st.chat_message(msg["role"], avatar=avatar):
        if "name" in msg:
            st.write(f"**{msg['name']}**")
        st.write(msg["content"])


# --- Auto-Debate Logic ---
if st.session_state.is_debating:
    # Only limit to 3 rounds (6 turns after the prompt)
    turns = len(st.session_state.chat_history) - 1 # Subtract initial user prompt
    max_turns = 6 
    
    if turns < max_turns:
        # Determine whose turn it is
        # Turn 0 (len=1): Logician starts
        # Turn 1 (len=2): Elder replies
        # ...
        
        if turns % 2 == 0:
            current_role_name = "論理学者"
            current_persona = PERSONA_LOGICIAN
            last_content = st.session_state.chat_history[-1]["content"]
        else:
            current_role_name = "長老"
            current_persona = PERSONA_ELDER
            last_content = st.session_state.chat_history[-1]["content"]

        with st.spinner(f"{current_role_name}が思考中..."):
            time.sleep(1) # Small delay for UX pacing
            response_text = generate_response(current_persona, st.session_state.chat_history, last_content)
            
            # Append to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "name": current_role_name,
                "content": response_text
            })
            st.rerun() # Rerun to update UI for next turn
    else:
        st.session_state.is_debating = False
        st.success("議論が終了しました。")
        if st.button("新しいテーマで始める"):
            st.session_state.is_debating = False
            st.session_state.topic = ""
            st.rerun()
