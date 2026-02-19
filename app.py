import streamlit as st
import google.generativeai as genai
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="論理と仏教の対話",
    page_icon="🙏",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- CSS for Mobile Optimization ---
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
    }
    .persona-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid #3d3d5c;
        color: #e0e0e0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .persona-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- API Key Handling (Secrets Only) ---
api_key = None
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ APIキーが設定されていません。")
    st.info(
        "**Streamlit Cloud の場合:**\n"
        "アプリの Settings → Secrets に以下を追加してください:\n"
        "```\nGEMINI_API_KEY = \"your-api-key\"\n```\n\n"
        "**ローカル実行の場合:**\n"
        "`.streamlit/secrets.toml` ファイルを作成し、同様に記述してください。"
    )
    st.stop()

try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"APIキーの設定に失敗しました: {e}")
    st.stop()

# --- Constants ---
AVAILABLE_MODELS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 3 Flash": "gemini-3-flash",
}
AVAILABLE_MODEL_NAMES = list(AVAILABLE_MODELS.keys())
DEFAULT_MODEL_LABEL = "Gemini 2.5 Flash"

DEFAULT_PERSONA_A = (
    "あなたは冷徹な論理学者です。\n"
    "感情や宗教的観念を排し、事実、統計、論理的整合性のみを重視して議論します。\n"
    "相手の曖昧な定義や非科学的な主張を鋭く指摘してください。\n"
    "口調は断定的で、理知的です。"
)

DEFAULT_PERSONA_B = (
    "あなたは慈悲深いテーラワーダ仏教の長老です。\n"
    "論理を超えた心の平安、執着の手放し、無常、苦（ドゥッカ）の解決を重視して議論します。\n"
    "相手の攻撃的な論理を柔和に受け流し、真理へと導くように諭してください。\n"
    "口調は穏やかで、落ち着いています。"
)

# --- Session State Initialization ---
defaults = {
    "page": "議論場",
    "chat_history": [],
    "is_debating": False,
    "debate_finished": False,
    "topic": "",
    "persona_a_name": "論理学者",
    "persona_a_text": DEFAULT_PERSONA_A,
    "persona_a_model": DEFAULT_MODEL_LABEL,
    "persona_b_name": "長老",
    "persona_b_text": DEFAULT_PERSONA_B,
    "persona_b_model": DEFAULT_MODEL_LABEL,
    "max_rounds": 3,
    "current_round_start": 0,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- Sidebar Navigation ---
with st.sidebar:
    st.header("メニュー")
    
    if st.button("🏟️ 議論場", use_container_width=True):
        st.session_state.page = "議論場"
        st.rerun()
    if st.button(f"📐 {st.session_state.persona_a_name} AI", use_container_width=True):
        st.session_state.page = "persona_a"
        st.rerun()
    if st.button(f"🙏 {st.session_state.persona_b_name} AI", use_container_width=True):
        st.session_state.page = "persona_b"
        st.rerun()
    if st.button("⚙️ 設定", use_container_width=True):
        st.session_state.page = "設定"
        st.rerun()
    
    st.divider()
    st.caption(f"AI-A: {st.session_state.persona_a_name} ({st.session_state.persona_a_model})")
    st.caption(f"AI-B: {st.session_state.persona_b_name} ({st.session_state.persona_b_model})")
    st.caption(f"往復回数: {st.session_state.max_rounds}")


# --- Helper Functions ---
def generate_response(persona, model_label, history, prompt_text):
    """Generates a response from the specific persona using Gemini."""
    try:
        model_id = AVAILABLE_MODELS[model_label]
        model = genai.GenerativeModel(model_id)
        
        context_str = ""
        for msg in history[-6:]:
            name = msg.get("name", msg["role"])
            context_str += f"{name}: {msg['content']}\n"
        
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


# ============================================================
# Page: 議論場 (Debate Arena)
# ============================================================
def page_debate():
    st.title("論理 vs 仏教 🧘‍♂️⚡️📐")
    st.caption(
        f"「{st.session_state.persona_a_name}」({st.session_state.persona_a_model}) "
        f"vs 「{st.session_state.persona_b_name}」({st.session_state.persona_b_model})"
    )

    # Topic Input (show only when not debating AND not in post-debate state)
    if not st.session_state.is_debating and not st.session_state.debate_finished:
        with st.form("topic_form"):
            user_topic = st.text_input(
                "議論のテーマを入力してください",
                placeholder="例：AIに意識は宿るか、幸福とは何か",
            )
            submitted = st.form_submit_button("🔥 議論開始", use_container_width=True)
            
            if submitted and user_topic:
                st.session_state.topic = user_topic
                st.session_state.chat_history = []
                st.session_state.chat_history.append({
                    "role": "user",
                    "name": "観客",
                    "content": f"テーマ: 「{user_topic}」について議論してください。",
                })
                st.session_state.is_debating = True
                st.session_state.debate_finished = False
                st.session_state.current_round_start = 0
                st.rerun()

    # Display Chat History
    for msg in st.session_state.chat_history:
        avatar = "👤"
        if msg.get("name") == st.session_state.persona_a_name:
            avatar = "📐"
        elif msg.get("name") == st.session_state.persona_b_name:
            avatar = "🙏"
        
        with st.chat_message(msg["role"], avatar=avatar):
            if "name" in msg:
                st.write(f"**{msg['name']}**")
            st.write(msg["content"])

    # Auto-Debate Logic
    if st.session_state.is_debating:
        # Stop button - checked before each API call (between turns)
        if st.button("🛑 議論を中断", use_container_width=True):
            st.session_state.is_debating = False
            st.session_state.debate_finished = True
            st.rerun()

        # Count turns since the last debate start point
        turns_since_start = len(st.session_state.chat_history) - 1 - st.session_state.current_round_start
        max_turns = st.session_state.max_rounds * 2
        
        if turns_since_start < max_turns:
            # Determine whose turn based on total AI turns (exclude user messages)
            ai_messages = [m for m in st.session_state.chat_history if m["role"] == "assistant"]
            ai_turn_count = len(ai_messages)
            
            if ai_turn_count % 2 == 0:
                current_role_name = st.session_state.persona_a_name
                current_persona = st.session_state.persona_a_text
                current_model = st.session_state.persona_a_model
            else:
                current_role_name = st.session_state.persona_b_name
                current_persona = st.session_state.persona_b_text
                current_model = st.session_state.persona_b_model
            
            last_content = st.session_state.chat_history[-1]["content"]

            with st.spinner(f"{current_role_name}が思考中... ({current_model})"):
                time.sleep(1)
                response_text = generate_response(
                    current_persona, current_model,
                    st.session_state.chat_history, last_content
                )
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "name": current_role_name,
                    "content": response_text,
                })
                st.rerun()
        else:
            st.session_state.is_debating = False
            st.session_state.debate_finished = True
            st.rerun()

    # Post-Debate: User Participation
    if st.session_state.debate_finished and not st.session_state.is_debating:
        st.success("議論が終了しました。")
        
        st.subheader("💬 あなたの意見を投げかける")
        with st.form("user_opinion_form"):
            user_opinion = st.text_area(
                "ここまでの議論を踏まえて、あなたの意見や質問を入力してください。"
                "AI同士がそれを踏まえてさらに議論を続けます。",
                placeholder="例：二人の意見は一見対立しているようだが、実は…",
                height=150,
            )
            col1, col2 = st.columns(2)
            with col1:
                continue_debate = st.form_submit_button(
                    "🔥 議論を再開", use_container_width=True
                )
            with col2:
                new_topic = st.form_submit_button(
                    "🔄 新しいテーマ", use_container_width=True
                )

        if continue_debate and user_opinion:
            st.session_state.chat_history.append({
                "role": "user",
                "name": "観客",
                "content": user_opinion,
            })
            st.session_state.current_round_start = len(st.session_state.chat_history) - 1
            st.session_state.is_debating = True
            st.session_state.debate_finished = False
            st.rerun()
        
        if new_topic:
            st.session_state.chat_history = []
            st.session_state.topic = ""
            st.session_state.debate_finished = False
            st.session_state.current_round_start = 0
            st.rerun()


# ============================================================
# Page: Persona Editing
# ============================================================
def page_persona(persona_key: str):
    """Render persona viewing/editing page."""
    if persona_key == "a":
        name_key = "persona_a_name"
        text_key = "persona_a_text"
        model_key = "persona_a_model"
        default_text = DEFAULT_PERSONA_A
        default_name = "論理学者"
        icon = "📐"
    else:
        name_key = "persona_b_name"
        text_key = "persona_b_text"
        model_key = "persona_b_model"
        default_text = DEFAULT_PERSONA_B
        default_name = "長老"
        icon = "🙏"
    
    current_name = st.session_state[name_key]
    current_text = st.session_state[text_key]
    current_model = st.session_state[model_key]

    st.title(f"{icon} {current_name} AI の設定")

    # Current persona display
    st.subheader("現在の性格")
    st.markdown(
        f'<div class="persona-card">'
        f'<div class="persona-title">{icon} {current_name} （{current_model}）</div>'
        f'{current_text.replace(chr(10), "<br>")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Edit form
    st.subheader("性格を変更する")
    with st.form(f"edit_{persona_key}"):
        new_name = st.text_input("AI の名前", value=current_name)
        
        # Model selection
        current_model_index = AVAILABLE_MODEL_NAMES.index(current_model) if current_model in AVAILABLE_MODEL_NAMES else 0
        new_model = st.selectbox(
            "使用するモデル",
            options=AVAILABLE_MODEL_NAMES,
            index=current_model_index,
        )
        
        new_text = st.text_area(
            "性格・話し方の設定（システムプロンプト）",
            value=current_text,
            height=200,
        )
        col1, col2 = st.columns(2)
        with col1:
            save = st.form_submit_button("💾 保存", use_container_width=True)
        with col2:
            reset = st.form_submit_button("🔄 初期設定に戻す", use_container_width=True)

    if save:
        st.session_state[name_key] = new_name
        st.session_state[text_key] = new_text
        st.session_state[model_key] = new_model
        st.success(f"「{new_name}」の設定を保存しました！（モデル: {new_model}）")
        st.rerun()
    
    if reset:
        st.session_state[name_key] = default_name
        st.session_state[text_key] = default_text
        st.session_state[model_key] = DEFAULT_MODEL_LABEL
        st.success("初期設定に戻しました。")
        st.rerun()


# ============================================================
# Page: Settings
# ============================================================
def page_settings():
    st.title("⚙️ 設定")

    st.subheader("議論の往復回数")
    new_rounds = st.slider(
        "AI同士の往復回数を選択してください",
        min_value=1,
        max_value=10,
        value=st.session_state.max_rounds,
        help="1往復 = 各AIが1回ずつ発言します",
    )
    
    if new_rounds != st.session_state.max_rounds:
        st.session_state.max_rounds = new_rounds
        st.success(f"往復回数を **{new_rounds}回** に設定しました。")

    st.divider()
    st.subheader("現在の設定一覧")
    st.markdown(
        f"| 項目 | 値 |\n"
        f"|---|---|\n"
        f"| 往復回数 | {st.session_state.max_rounds} 回 (計 {st.session_state.max_rounds * 2} 発言) |\n"
        f"| AI-A | {st.session_state.persona_a_name} ({st.session_state.persona_a_model}) |\n"
        f"| AI-B | {st.session_state.persona_b_name} ({st.session_state.persona_b_model}) |"
    )


# ============================================================
# Router
# ============================================================
current_page = st.session_state.page

if current_page == "議論場":
    page_debate()
elif current_page == "persona_a":
    page_persona("a")
elif current_page == "persona_b":
    page_persona("b")
elif current_page == "設定":
    page_settings()
