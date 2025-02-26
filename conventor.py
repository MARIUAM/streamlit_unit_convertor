import streamlit as st
import hashlib
import json
from datetime import datetime
from textblob import TextBlob
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Security configuration
USER_DB = "users.json"
FEEDBACK_DB = "feedback.json"
ADMIN_USER = "admin@quantum.com"

# Unit conversions and quantum constants
unit_conversions = {
    "Energy": {"J": 1, "eV": 1.60218e-19, "Ha": 4.35974e-18},
    "Length": {"m": 1, "nm": 1e-9, "Å": 1e-10, "feet": 0.3048},
    "Time": {"s": 1, "fs": 1e-15, "day": 86400},
    "Frequency": {"Hz": 1, "THz": 1e12},
    "Mass": {"kg": 1, "amu": 1.66054e-27, "pounds": 0.453592},
    "Speed": {"m/s": 1, "mph": 0.44704, "km/h": 0.277778},
    "Temperature": {
        "C": {"to_base": lambda x: x, "from_base": lambda x: x},
        "F": {"to_base": lambda x: (x - 32) * 5/9, "from_base": lambda x: x * 9/5 + 32},
        "K": {"to_base": lambda x: x - 273.15, "from_base": lambda x: x + 273.15}
    }
}

QUANTUM_CONSTANTS = {
    "Planck Constant": 6.62607015e-34,
    "Reduced Planck Constant": 1.054571817e-34,
    "Bohr Radius": 5.29177210903e-11,
    "Hartree Energy": 4.3597447222071e-18,
    "Rydberg Constant": 10973731.568160
}

# Custom CSS with Neon Effects
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

:root {
    --neon-blue: #00f3ff;
    --neon-pink: #ff00ff;
    --dark-bg: #0a0a0f;
}

body {
    background-color: var(--dark-bg);
    color: white;
    font-family: 'Orbitron', sans-serif;
}

.stApp {
    background: linear-gradient(45deg, #0f0c29, #302b63, #24243e);
}

.neon-header {
    font-family: 'Orbitron', sans-serif;
    text-align: center;
    color: var(--neon-blue);
    text-shadow: 0 0 10px var(--neon-blue);
    animation: glow 1.5s ease-in-out infinite alternate;
}

@keyframes glow {
    from { text-shadow: 0 0 5px var(--neon-blue), 0 0 10px var(--neon-blue); }
    to { text-shadow: 0 0 20px var(--neon-blue), 0 0 30px var(--neon-blue); }
}

.neon-card {
    background: rgba(10, 10, 15, 0.9) !important;
    border: 1px solid var(--neon-blue);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 0 15px var(--neon-blue);
    transition: all 0.3s ease;
}

.neon-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 0 25px var(--neon-blue);
}

.neon-button {
    background: transparent !important;
    border: 2px solid var(--neon-blue) !important;
    color: var(--neon-blue) !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

.neon-button:hover {
    background: var(--neon-blue) !important;
    color: black !important;
    box-shadow: 0 0 15px var(--neon-blue);
}

.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
    text-align: center;
    padding: 10px;
    color: var(--neon-blue);
    font-family: 'Orbitron', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "history" not in st.session_state:
    st.session_state.history = []

# -------------------- Authentication Functions --------------------
def load_users():
    try:
        with open(USER_DB, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = {"password": hash_password(password), "role": "user"}
    save_users(users)
    return True

def authenticate_user(username, password):
    users = load_users()
    user = users.get(username)
    if user and user["password"] == hash_password(password):
        return user
    return None

# -------------------- Feedback System --------------------
def analyze_sentiment(feedback):
    analysis = TextBlob(feedback)
    return {
        "polarity": analysis.sentiment.polarity,
        "subjectivity": analysis.sentiment.subjectivity
    }

def save_feedback(username, feedback, rating):
    try:
        with open(FEEDBACK_DB, "r") as f:
            feedbacks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        feedbacks = []
    
    feedbacks.append({
        "id": hashlib.sha256(f"{username}{datetime.now()}".encode()).hexdigest()[:8],
        "username": username,
        "feedback": feedback,
        "rating": rating,
        "sentiment": analyze_sentiment(feedback),
        "timestamp": datetime.now().isoformat(),
        "visible": True
    })
    
    with open(FEEDBACK_DB, "w") as f:
        json.dump(feedbacks, f, indent=2)

def load_feedback():
    try:
        with open(FEEDBACK_DB, "r") as f:
            feedbacks = json.load(f)
            for f in feedbacks:
                if 'visible' not in f:
                    f['visible'] = True
            return feedbacks
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# -------------------- Conversion Functions --------------------
def convert_units(value, from_unit, to_unit, unit_type):
    if unit_type == "Temperature":
        try:
            base_value = unit_conversions[unit_type][from_unit]["to_base"](value)
            result = unit_conversions[unit_type][to_unit]["from_base"](base_value)
            return round(result, 6)
        except KeyError:
            return None
    else:
        factors = unit_conversions[unit_type]
        if from_unit in factors and to_unit in factors:
            return value * factors[to_unit] / factors[from_unit]
    return None

# -------------------- UI Components --------------------
def login_section():
    with st.sidebar.form("auth_form"):
        st.markdown("<h2 class='neon-header'>🔑 AUTHENTICATION</h2>", unsafe_allow_html=True)
        username = st.text_input("Email/Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("LOGIN", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login Successful!")
                else:
                    st.error("Invalid Credentials")
        with col2:
            if st.form_submit_button("REGISTER", use_container_width=True):
                if len(password) >= 8:
                    if register_user(username, password):
                        st.success("Registration Successful!")
                    else:
                        st.error("Username Already Exists")
                else:
                    st.error("Password Must Be 8+ Characters")

def conversion_history():
    with st.expander("📜 CONVERSION HISTORY", expanded=True):
        if st.session_state.history:
            for entry in reversed(st.session_state.history[-5:]):
                st.markdown(f"`{entry['time']}` - {entry['conversion']}")
        else:
            st.info("No Conversion History")

def feedback_section():
    with st.container():
        st.markdown("<h3 class='neon-header'>💬 SUBMIT FEEDBACK</h3>", unsafe_allow_html=True)
        with st.form("new_feedback"):
            feedback = st.text_area("Your Feedback", height=100)
            rating = st.slider("Rating", 1, 5, 4)
            if st.form_submit_button("SUBMIT", use_container_width=True):
                if st.session_state.authenticated:
                    save_feedback(st.session_state.username, feedback, rating)
                    st.success("Feedback Submitted! 🌟")
                else:
                    st.error("Please Login to Submit Feedback")

def review_section():
    st.markdown("<h2 class='neon-header'>🌟 COMMUNITY REVIEWS</h2>", unsafe_allow_html=True)
    feedbacks = load_feedback()
    
    if not feedbacks:
        st.info("No Reviews Available")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        min_rating = st.selectbox("Minimum Rating", [1,2,3,4,5], index=2)
    with col2:
        sort_order = st.selectbox("Sort By", ["Newest First", "Highest Rating"])
    
    filtered = [f for f in feedbacks if 
                f.get('rating', 0) >= min_rating and 
                f.get('visible', True)]
    
    if sort_order == "Highest Rating":
        filtered.sort(key=lambda x: x['rating'], reverse=True)
    else:
        filtered.sort(key=lambda x: x['timestamp'], reverse=True)
    
    for feedback in filtered:
        sentiment = feedback.get('sentiment', {'polarity': 0})
        polarity = sentiment.get('polarity', 0)
        sentiment_color = "#4CAF50" if polarity > 0 else "#F44336" if polarity < 0 else "#FF9800"
        
        with st.container():
            st.markdown(f"""
            <div class='neon-card'>
                <div style="color: {sentiment_color}; border-left: 3px solid {sentiment_color}; padding-left: 10px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>@{feedback.get('username', 'Anonymous')}</div>
                        <div>{feedback.get('rating', 0)}⭐</div>
                    </div>
                    <p style="margin: 10px 0;">{feedback.get('feedback', 'No feedback text')}</p>
                    <div style="font-size: 0.8em; color: #666;">
                        {datetime.fromisoformat(feedback['timestamp']).strftime("%d %b %Y %H:%M")}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def admin_panel():
    if st.session_state.username == ADMIN_USER:
        with st.expander("👑 NEON ADMIN DASHBOARD", expanded=True):
            st.markdown("<h2 class='neon-header'>ADMIN CONTROLS</h2>", unsafe_allow_html=True)
            
            # User Management
            users = load_users()
            df_users = pd.DataFrame([
                {"Username": k, "Role": v["role"]} 
                for k,v in users.items()
            ])
            
            edited_df = st.data_editor(
                df_users,
                column_config={
                    "Role": st.column_config.SelectboxColumn(
                        "Role",
                        options=["user", "admin"],
                        required=True
                    )
                },
                use_container_width=True
            )
            
            if st.button("💾 Save User Changes", use_container_width=True):
                for index, row in edited_df.iterrows():
                    users[row['Username']]['role'] = row['Role']
                save_users(users)
                st.success("User Roles Updated!")
            
            # Feedback Moderation
            st.markdown("---")
            st.markdown("<h3 class='neon-header'>📊 FEEDBACK ANALYTICS</h3>", unsafe_allow_html=True)
            feedbacks = load_feedback()
            
            if feedbacks:
                df = pd.DataFrame(feedbacks)
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Feedback", len(df))
                with col2:
                    st.metric("Average Rating", f"{df['rating'].mean():.1f}/5")
                
                fig = px.line(
                    df.groupby('date')['rating'].mean().reset_index(),
                    x='date',
                    y='rating',
                    title="Rating Trend"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Word Cloud
                st.markdown("### Feedback Word Cloud")
                text = ' '.join(df['feedback'].astype(str))
                wordcloud = WordCloud(width=800, height=400).generate(text)
                plt.figure(figsize=(10, 5))
                plt.imshow(wordcloud)
                plt.axis("off")
                st.pyplot(plt)
            else:
                st.info("No Feedback Available")

# -------------------- Main App --------------------
def main():
    st.markdown("<h1 class='neon-header'>💕 UNIT CONVERTER</h1>", unsafe_allow_html=True)
    
    if not st.session_state.authenticated:
        login_section()
        st.warning("🔐 Please Login to Access Features")
    else:
        with st.sidebar:
            st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
            st.success(f"👤 {st.session_state.username}")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🌀 CONVERTER", "💬 REVIEWS", "👑 ADMIN"])
        
        with tab1:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
                st.markdown("<h3 class='neon-header'>🧪 UNIT CONVERTER</h3>", unsafe_allow_html=True)
                
                unit_type = st.selectbox("Select Quantity Type", list(unit_conversions.keys()))
                value = st.number_input("Enter Value", min_value=0.0, format="%.6f")
                from_unit = st.selectbox("From Unit", list(unit_conversions[unit_type].keys()))
                to_unit = st.selectbox("To Unit", list(unit_conversions[unit_type].keys()))
                
                if st.button("✨ CONVERT", use_container_width=True):
                    result = convert_units(value, from_unit, to_unit, unit_type)
                    if result is not None:
                        conversion_str = f"{value} {from_unit} = {result:.6e} {to_unit}"
                        st.balloons()
                        st.success(conversion_str)
                        st.session_state.history.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "conversion": conversion_str
                        })
                    else:
                        st.error("Invalid Conversion")
                
                conversion_history()
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
                st.markdown("<h3 class='neon-header'>⚛️ QUANTUM TOOLS</h3>", unsafe_allow_html=True)
                
                with st.expander("CONSTANTS"):
                    for const, value in QUANTUM_CONSTANTS.items():
                        st.write(f"**{const}:** `{value:.4e}`")
                
                with st.expander("ENERGY CALCULATOR"):
                    frequency = st.number_input("Frequency (THz)", 1, 1000, 500)
                    energy = QUANTUM_CONSTANTS["Planck Constant"] * frequency * 1e12
                    st.metric("Energy (J)", f"{energy:.2e}")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        with tab2:
            st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
            review_section()
            feedback_section()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab3:
            st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
            admin_panel()
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Made by footer
    st.markdown("""
    <div class="footer">
        <hr>
        <h3>Made with ❤️ by Maryam Saleem</h3>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()