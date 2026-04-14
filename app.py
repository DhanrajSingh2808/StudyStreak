import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuration & Setup ---
st.set_page_config(page_title="Mock Streak", page_icon="🔥", layout="centered")

# Define the exact columns for the app
EXPECTED_COLS = ["Date", "User", "Mock Title", "Math", "English", "Reasoning", "GA", "Total Score", "Image URL"]

# --- 2. Authentication & Connection ---
@st.cache_resource
def init_connection():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        # Connect to the sheet using the URL from secrets
        return client.open_by_url(st.secrets["private"]["sheet_url"]).sheet1
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

sheet = init_connection()

# --- 3. Helper Functions ---
@st.cache_data(ttl=60) # This tells the app to refresh data every 60 seconds automatically
def load_data():
    try:
        # Fetch all values from the sheet
        rows = sheet.get_all_values()
        if len(rows) > 1:
            # Create DataFrame using the first row as headers
            df = pd.DataFrame(rows[1:], columns=rows[0])
            
            # Ensure all expected columns exist (in case of typos in Sheet)
            for col in EXPECTED_COLS:
                if col not in df.columns:
                    df[col] = 0
            
            # Convert numeric columns to proper numbers
            numeric_cols = ["Math", "English", "Reasoning", "GA", "Total Score"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
            return df
        else:
            return pd.DataFrame(columns=EXPECTED_COLS)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=EXPECTED_COLS)

def upload_to_imgbb(image_file):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": st.secrets["private"]["imgbb_api_key"],
            "image": base64.b64encode(image_file.getvalue()).decode("utf-8")
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json()['data']['url']
    except Exception as e:
        st.error(f"Image Upload Error: {e}")
    return None

def calculate_leaderboard(df):
    if df.empty or 'Date' not in df.columns or df['Date'].isnull().all():
        return pd.DataFrame(columns=["User", "Current Streak 🔥", "Avg Total 🎯", "Total Mocks 📚"])
    
    leaderboard = []
    # Drop empty dates and convert to proper date objects
    temp_df = df.dropna(subset=['Date']).copy()
    temp_df['Date'] = pd.to_datetime(temp_df['Date']).dt.date
    today = datetime.now().date()
    
    for user in temp_df['User'].unique():
        user_data = temp_df[temp_df['User'] == user].sort_values(by="Date", ascending=False)
        avg_total = round(user_data['Total Score'].astype(float).mean(), 2)
        total_mocks = len(user_data)
        
        # Streak Logic
        streak = 0
        dates_logged = sorted(list(set(user_data['Date'].tolist())), reverse=True)
        
        if dates_logged:
            # Check if most recent is today or yesterday
            if dates_logged[0] >= today - timedelta(days=1):
                current_check = dates_logged[0]
                for d in dates_logged:
                    if d == current_check:
                        streak += 1
                        current_check -= timedelta(days=1)
                    else:
                        break
        
        leaderboard.append({
            "User": user,
            "Current Streak 🔥": streak,
            "Avg Total 🎯": avg_total,
            "Total Mocks 📚": total_mocks
        })
        
    return pd.DataFrame(leaderboard).sort_values(by="Current Streak 🔥", ascending=False)

# --- 4. Main App UI ---
st.title("🔥 Mock Streak Tracker")

# Customize this list for your group
USERS = ["Select Name", "Dhanraj", "Damneet", "Friend 3", "Friend 4"]
current_user = st.selectbox("Who is logging in?", USERS)

df = load_data()
# Add a refresh button in the sidebar or top
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 The Feed"])

with tab1:
    if current_user != "Select Name":
        st.subheader(f"Log Performance: {current_user}")
        
        with st.form("mock_form", clear_on_submit=True):
            log_date = st.date_input("Exam Date", datetime.now())
            mock_title = st.text_input("Mock Title", placeholder="e.g., CGL Tier-1 Mock 10")
            
            c1, c2 = st.columns(2)
            with c1:
                math = st.number_input("Math", min_value=0.0, step=0.5)
                reasoning = st.number_input("Reasoning", min_value=0.0, step=0.5)
            with c2:
                english = st.number_input("English", min_value=0.0, step=0.5)
                ga = st.number_input("General Awareness", min_value=0.0, step=0.5)
            
            screenshot = st.file_uploader("Upload Scorecard Screenshot", type=['png', 'jpg', 'jpeg'])
            submitted = st.form_submit_button("Submit & Extend Streak 🚀")
            
            if submitted:
                if not mock_title or screenshot is None:
                    st.error("Missing Mock Title or Screenshot!")
                else:
                    total = math + english + reasoning + ga
                    with st.spinner("Processing..."):
                        img_url = upload_to_imgbb(screenshot)
                    
                    if img_url:
                        new_row = [str(log_date), current_user, mock_title, math, english, reasoning, ga, total, img_url]
                        sheet.append_row(new_row)
                        st.success(f"Great job! Total Score: {total}")
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error("Screenshot upload failed.")
    else:
        st.info("Select your name to begin logging.")

with tab2:
    st.subheader("Leaderboard")
    lb_df = calculate_leaderboard(df)
    if lb_df.empty:
        st.info("No data available yet.")
    else:
        st.dataframe(lb_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Community Feed")
    if df.empty or 'Date' not in df.columns or df['Date'].isnull().all():
        st.info("Feed is empty. Be the first to post!")
    else:
        # Sort feed by date
        valid_feed = df.dropna(subset=['Date']).copy()
        valid_feed['Date'] = pd.to_datetime(valid_feed['Date']).dt.date
        recent_posts = valid_feed.sort_values(by="Date", ascending=False).head(15)
        
        for _, row in recent_posts.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['User']} | Total: {row['Total Score']}")
                st.caption(f"📅 {row['Date']} • {row['Mock Title']}")
                
                # Metric display
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Math", row.get('Math', 0))
                m2.metric("Eng", row.get('English', 0))
                m3.metric("Reas", row.get('Reasoning', 0))
                m4.metric("GA", row.get('GA', 0))
                
                if row.get('Image URL'):
                    st.image(row['Image URL'], use_column_width=True)
