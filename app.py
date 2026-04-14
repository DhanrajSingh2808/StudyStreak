import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- Configuration & Setup ---
st.set_page_config(page_title="Mock Streak", page_icon="🔥", layout="centered")

# --- Authentication & Connection ---
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(st.secrets["private"]["sheet_url"]).sheet1

sheet = init_connection()

# --- Helper Functions ---
def load_data():
    records = sheet.get_all_records()
    if records:
        return pd.DataFrame(records)
    else:
        return pd.DataFrame(columns=["Date", "User", "Mock Title", "Math", "English", "Reasoning", "GA", "Total Score", "Image URL"])

def upload_to_imgbb(image_file):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": st.secrets["private"]["imgbb_api_key"],
        "image": base64.b64encode(image_file.getvalue()).decode("utf-8")
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()['data']['url']
    return None

def calculate_leaderboard(df):
    if df.empty:
        return pd.DataFrame(columns=["User", "Current Streak 🔥", "Avg Total 🎯", "Total Mocks 📚"])
    
    leaderboard = []
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    today = datetime.now().date()
    
    for user in df['User'].unique():
        user_data = df[df['User'] == user].sort_values(by="Date", ascending=False)
        avg_total = round(user_data['Total Score'].mean(), 2)
        total_mocks = len(user_data)
        
        # Streak Logic
        streak = 0
        dates_logged = user_data['Date'].tolist()
        current_date_check = today
        if dates_logged[0] == today or dates_logged[0] == today - timedelta(days=1):
            for logged_date in dates_logged:
                if logged_date == current_date_check:
                    streak += 1
                    current_date_check -= timedelta(days=1)
                elif logged_date == current_date_check + timedelta(days=1):
                    continue
                else:
                    break
                    
        leaderboard.append({
            "User": user,
            "Current Streak 🔥": streak,
            "Avg Total 🎯": avg_total,
            "Total Mocks 📚": total_mocks
        })
        
    return pd.DataFrame(leaderboard).sort_values(by="Current Streak 🔥", ascending=False)

# --- Main App UI ---
st.title("🔥 Mock Streak Tracker")

USERS = ["Select", "Dhanraj", "Naman", "Nishant"]
current_user = st.selectbox("Who is logging in?", USERS)

df = load_data()

tab1, tab2, tab3 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 The Feed"])

with tab1:
    if current_user != "Select":
        st.subheader(f"Log your performance, {current_user}!")
        
        with st.form("mock_form", clear_on_submit=True):
            log_date = st.date_input("Date", datetime.now())
            mock_title = st.text_input("Mock Name", placeholder="e.g., SSC CGL Full Mock 5")
            
            # Sectional Inputs
            col1, col2 = st.columns(2)
            with col1:
                reasoning = st.number_input("Reasoning Score", min_value=0.0, step=0.5)
                ga = st.number_input("General Awareness", min_value=0.0, step=0.5)
            with col2:
                math = st.number_input("Math Score", min_value=0.0, step=0.5)
                english = st.number_input("English Score", min_value=0.0, step=0.5)
              
            
            screenshot = st.file_uploader("Upload Score Screenshot", type=['png', 'jpg', 'jpeg'])
            submitted = st.form_submit_button("Submit Score 🚀")
            
            if submitted:
                if not mock_title or screenshot is None:
                    st.error("Please fill in the Mock Name and upload a screenshot!")
                else:
                    total_score = math + english + reasoning + ga
                    with st.spinner("Uploading to the cloud..."):
                        img_url = upload_to_imgbb(screenshot)
                    
                    if img_url:
                        # Append to Sheet in correct column order
                        new_row = [str(log_date), current_user, mock_title, math, english, reasoning, ga, total_score, img_url]
                        sheet.append_row(new_row)
                        
                        st.success(f"Score logged! Total: {total_score}. Streak extended. 💪")
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error("Failed to upload image.")
    else:
        st.info("Select your name to log a mock.")

with tab2:
    st.subheader("Leaderboard")
    if df.empty:
        st.write("No mocks logged yet.")
    else:
        st.dataframe(calculate_leaderboard(df), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Recent Uploads")
    if df.empty:
        st.write("Feed is empty.")
    else:
        recent_df = df.sort_values(by="Date", ascending=False).head(10)
        for _, row in recent_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['User']} - Total: {row['Total Score']}")
                st.caption(f"📅 {row['Date']} | {row['Mock Title']}")
                
                # Show Breakdown
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Math", row['Math'])
                b2.metric("English", row['English'])
                b3.metric("Reasoning", row['Reasoning'])
                b4.metric("GA", row['GA'])
                
                st.image(row['Image URL'], use_column_width=True)
