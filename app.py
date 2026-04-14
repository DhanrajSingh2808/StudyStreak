import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuration & Setup ---
st.set_page_config(page_title="Mock Streak", page_icon="🔥", layout="centered")

EXPECTED_COLS = ["Date", "User", "Mock Title", "Math", "English", "Reasoning", "GA", "Total Score", "Image URL"]

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
@st.cache_data(ttl=60)
def load_data():
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            for col in EXPECTED_COLS:
                if col not in df.columns: df[col] = 0
            
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

def get_user_stats(df, user):
    if df.empty or user == "Select Name":
        return 0, "Select your name to see your progress!"
    
    user_df = df[df['User'] == user].copy()
    user_df['Date'] = pd.to_datetime(user_df['Date']).dt.date
    dates = sorted(list(set(user_df['Date'].tolist())), reverse=True)
    
    streak = 0
    today = datetime.now().date()
    
    if dates and (dates[0] == today or dates[0] == today - timedelta(days=1)):
        curr = dates[0]
        for d in dates:
            if d == curr:
                streak += 1
                curr -= timedelta(days=1)
            else: break

    # Motivational Messages
    if streak == 0: msg = "The best time to start was yesterday. The second best time is **now**! 🚀"
    elif streak < 3: msg = "Good start! The first few days are the hardest. **Keep showing up.** 👊"
    elif streak < 7: msg = "You're building a habit. Stay consistent, the results will follow! 📈"
    elif streak < 15: msg = "Incredible momentum! You are outworking the competition. 🔥"
    else: msg = "UNSTOPPABLE. You've become a machine. Let's get that selection! 👑"
    
    return streak, msg

# --- 4. Main App UI ---
st.title("🔥 Mock Streak Tracker")

USERS = ["Select Name", "Dhanraj", "Damneet", "Friend 3", "Friend 4"]
current_user = st.selectbox("Who is logging in?", USERS)

df = load_data()

# Sidebar / Top Streak Display
if current_user != "Select Name":
    streak, message = get_user_stats(df, current_user)
    st.info(f"**Current Streak:** {streak} Days | {message}")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 The Feed", "📅 My Calendar"])

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
            if st.form_submit_button("Submit & Extend Streak 🚀"):
                if mock_title and screenshot:
                    with st.spinner("Saving..."):
                        img_url = upload_to_imgbb(screenshot)
                        if img_url:
                            total = math + eng + reas + ga
                            sheet.append_row([str(log_date), current_user, mock_title, math, eng, reas, ga, total, img_url])
                            st.success("Logged! Your streak just grew.")
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()

# --- TAB 2: LEADERBOARD ---
with tab2:
    st.subheader("Leaderboard")
    # (Simplified leaderboard logic for brevity)
    lb_data = []
    for u in df['User'].unique():
        s, _ = get_user_stats(df, u)
        lb_data.append({"User": u, "Streak 🔥": s, "Avg Score": round(df[df['User']==u]['Total Score'].mean(), 1)})
    st.dataframe(pd.DataFrame(lb_data).sort_values("Streak 🔥", ascending=False), use_container_width=True, hide_index=True)

# --- TAB 3: FEED ---
with tab3:
    st.subheader("Community Feed")
    if not df.empty:
        feed_df = df.copy().sort_values("Date", ascending=False).head(10)
        for _, row in feed_df.iterrows():
            with st.container(border=True):
                st.write(f"**{row['User']}** scored **{row['Total Score']}**")
                st.caption(f"{row['Date']} • {row['Mock Title']}")
                st.image(row['Image URL'], use_column_width=True)

# --- TAB 4: MY CALENDAR ---
with tab4:
    if current_user == "Select Name":
        st.warning("Please select your name above to view your history.")
    else:
        st.subheader(f"History for {current_user}")
        user_df = df[df['User'] == current_user].copy()
        user_df['Date'] = pd.to_datetime(user_df['Date']).dt.date
        
        # Visual Grid (Current Month)
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        logged_dates = user_df['Date'].unique()
        
        st.write("### Your Attendance")
        # Creating a simple visual row of last 14 days
        cols = st.columns(7)
        for i in range(14):
            check_date = today - timedelta(days=13-i)
            with cols[i % 7]:
                if check_date in logged_dates:
                    st.write(f"✅\n{check_date.day}")
                else:
                    st.write(f"⚪\n{check_date.day}")
        
        st.divider()
        
        # Date Selector to see Details
        st.write("### Review a Specific Test")
        available_dates = sorted(user_df['Date'].unique(), reverse=True)
        if available_dates:
            selected_date = st.selectbox("Select a date to view your scorecard", available_dates)
            day_mocks = user_df[user_df['Date'] == selected_date]
            
            for _, row in day_mocks.iterrows():
                with st.expander(f"📊 {row['Mock Title']} (Score: {row['Total Score']})"):
                    col1, col2 = st.columns(2)
                    col1.metric("Math", row['Math'])
                    col1.metric("Reasoning", row['Reasoning'])
                    col2.metric("English", row['English'])
                    col2.metric("GA", row['GA'])
                    st.image(row['Image URL'], caption="Scorecard Screenshot", use_column_width=True)
        else:
            st.info("No mocks logged yet. Your calendar is waiting for its first ✅!")
