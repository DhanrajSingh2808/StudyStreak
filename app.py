import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuration & Setup ---
st.set_page_config(page_title="Mock Streak", page_icon="🔥", layout="centered")

# Standardized headers (Make sure Row 1 of your sheet matches these exactly)
EXPECTED_COLS = ["Date", "User", "Mock Title", "Math", "English", "Reasoning", "GA", "Total Score", "Image URL"]
START_DATE = datetime(2026, 4, 14).date() 

# --- 2. Authentication & Connection ---
@st.cache_resource
def init_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_url(st.secrets["private"]["sheet_url"]).sheet1
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

sheet = init_connection()

# --- 3. Helper Functions ---
@st.cache_data(ttl=5)
def load_data():
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            
            # Clean Date Column
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            df = df.dropna(subset=['Date'])
            
            # Convert numbers
            numeric_cols = ["Math", "English", "Reasoning", "GA", "Total Score"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        return pd.DataFrame(columns=EXPECTED_COLS)
    except:
        return pd.DataFrame(columns=EXPECTED_COLS)

def upload_to_imgbb(image_file):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": st.secrets["private"]["imgbb_api_key"],
            "image": base64.b64encode(image_file.getvalue()).decode("utf-8")
        }
        response = requests.post(url, data=payload)
        return response.json()['data']['url'] if response.status_code == 200 else None
    except:
        return None

def get_streak_info(df, user):
    if df.empty or user == "Select Name":
        return 0, "Log your first mock to start the fire! 🚀"
    
    user_df = df[df['User'] == user].copy()
    dates = sorted(list(set(user_df['Date'].tolist())), reverse=True)
    
    streak = 0
    today = datetime.now().date()
    
    if dates:
        # Check if latest entry is today or yesterday
        if dates[0] >= today - timedelta(days=1):
            curr = dates[0]
            for d in dates:
                if d == curr:
                    streak += 1
                    curr -= timedelta(days=1)
                else: break
    
    msg = "Keep going! Selection is near. 👊" if streak > 0 else "Start your journey today! 🚀"
    return streak, msg

# --- 4. Main App UI ---
st.title("🔥 Mock Streak Tracker")

USERS = ["Select Name", "Dhanraj", "Damneet", "Friend 3", "Friend 4"]
current_user = st.selectbox("Who is logging in?", USERS)

df = load_data()

if current_user != "Select Name":
    streak, message = get_streak_info(df, current_user)
    st.info(f"**Current Streak:** {streak} Days | {message}")

if st.button("🔄 Sync Fresh Data"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 Feed", "📅 My Journey"])

# --- TAB 1: LOG MOCK ---
with tab1:
    if current_user != "Select Name":
        with st.form("mock_form", clear_on_submit=True):
            log_date = st.date_input("Exam Date", datetime.now())
            mock_title = st.text_input("Mock Title")
            c1, c2 = st.columns(2)
            with c1:
                math = st.number_input("Math", min_value=0.0, step=0.5)
                reas = st.number_input("Reasoning", min_value=0.0, step=0.5)
            with c2:
                eng = st.number_input("English", min_value=0.0, step=0.5)
                ga = st.number_input("GA", min_value=0.0, step=0.5)
            
            screenshot = st.file_uploader("Upload Scorecard", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("Log Score 🚀"):
                if mock_title and screenshot:
                    with st.spinner("Uploading..."):
                        img_url = upload_to_imgbb(screenshot)
                        if img_url:
                            total = math + eng + reas + ga
                            sheet.append_row([str(log_date), current_user, mock_title, math, eng, reas, ga, total, img_url])
                            st.success("Entry Saved!")
                            st.cache_data.clear()
                            st.rerun()

# --- TAB 2: LEADERBOARD ---
with tab2:
    lb_data = []
    active_users = [u for u in USERS if u != "Select Name"]
    for u in active_users:
        s, _ = get_streak_info(df, u)
        scores = df[df['User']==u]['Total Score']
        avg = round(scores.mean(), 1) if not scores.empty else 0
        lb_data.append({"User": u, "Streak 🔥": s, "Avg Score 🎯": avg})
    if lb_data:
        st.dataframe(pd.DataFrame(lb_data).sort_values("Streak 🔥", ascending=False), use_container_width=True, hide_index=True)

# --- TAB 3: FEED ---
with tab3:
    if not df.empty:
        feed_df = df.sort_values("Date", ascending=False).head(10)
        for _, row in feed_df.iterrows():
            with st.container(border=True):
                st.write(f"**{row['User']}** scored **{row['Total Score']}**")
                st.caption(f"{row['Date']} • {row['Mock Title']}")
                st.image(row['Image URL'], use_column_width=True)

# --- TAB 4: MY JOURNEY ---
with tab4:
    if current_user == "Select Name":
        st.warning("Select your name to view your journey.")
    else:
        # Filter and sort by date descending
        user_df = df[df['User'] == current_user].copy().sort_values("Date", ascending=False)
        logged_dates = user_df['Date'].unique()
        
        # 1. Attendance Grid
        st.subheader("Attendance Grid")
        today = datetime.now().date()
        total_days_shown = (today - START_DATE).days + 1
        
        # Create a responsive grid
        cols = st.columns(7)
        for i in range(total_days_shown):
            check_date = START_DATE + timedelta(days=i)
            with cols[i % 7]:
                icon = "🟢" if check_date in logged_dates else "⚪"
                st.markdown(f"**{icon}**\n<small>{check_date.strftime('%b %d')}</small>", unsafe_allow_html=True)
        
        st.divider()
        
        # 2. EXPANDABLE REVIEW LIST
        st.subheader("Review Previous Tests")
        if not user_df.empty:
            for _, row in user_df.iterrows():
                # Format: Date | Title | Score
                header = f"📅 {row['Date'].strftime('%d %b %Y')} | {row['Mock Title']} | Score: {row['Total Score']}"
                
                with st.expander(header):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Math", row['Math'])
                    m2.metric("English", row['English'])
                    m3.metric("Reasoning", row['Reasoning'])
                    m4.metric("GA", row['GA'])
                    
                    st.image(row['Image URL'], caption=f"Scorecard for {row['Mock Title']}", use_column_width=True)
        else:
            st.info("No logs found. Your streak starts with your first submission!")
