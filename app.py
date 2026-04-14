This is a great catch. A streak tracker should feel like a "Map" of your progress, not just a list of numbers. Since today is **April 14, 2026**, we will set that as your "Day Zero." Every day that passes will automatically add a new circle to your grid.

I have updated the attendance logic to be a **Growth Map**. It will start with one circle today and expand day by day.

### The Complete "Growth Map" Version (`app.py`)

```python
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
START_DATE = datetime(2026, 4, 14).date() # Your journey starts today!

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
            df['Date'] = pd.to_datetime(df['Date']).dt.date
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
        return 0, "Select your name to see your progress!"
    
    user_df = df[df['User'] == user].copy()
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

    messages = [
        (0, "The journey of a thousand miles begins with a single mock. Start now! 🚀"),
        (3, "First milestone hit! You're showing grit. Keep pushing. 👊"),
        (7, "One week down! You're outworking 90% of the aspirants. 📈"),
        (15, "Two weeks of discipline. You're becoming a machine! 🔥"),
        (30, "A full month of absolute dominance. The selection is yours! 👑")
    ]
    msg = next((m[1] for m in reversed(messages) if streak >= m[0]), messages[0][1])
    return streak, msg

# --- 4. Main App UI ---
st.title("🔥 Mock Streak Tracker")

USERS = ["Select Name", "Dhanraj", "Damneet", "Friend 3", "Friend 4"]
current_user = st.selectbox("Who is logging in?", USERS)

df = load_data()

if current_user != "Select Name":
    streak, message = get_streak_info(df, current_user)
    st.info(f"**Current Streak:** {streak} Days | {message}")

if st.button("🔄 Refresh Dashboard"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 The Feed", "📅 My Journey"])

# --- TAB 1: LOG MOCK ---
with tab1:
    if current_user != "Select Name":
        with st.form("mock_form", clear_on_submit=True):
            log_date = st.date_input("Exam Date", datetime.now())
            mock_title = st.text_input("Mock Title (e.g. SSC CGL Mock 12)")
            c1, c2 = st.columns(2)
            with c1:
                math = st.number_input("Math", min_value=0.0, step=0.5)
                reas = st.number_input("Reasoning", min_value=0.0, step=0.5)
            with c2:
                eng = st.number_input("English", min_value=0.0, step=0.5)
                ga = st.number_input("GA", min_value=0.0, step=0.5)
            
            screenshot = st.file_uploader("Upload Scorecard", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("Log Entry & Extend Streak 🚀"):
                if mock_title and screenshot:
                    with st.spinner("Syncing to Cloud..."):
                        img_url = upload_to_imgbb(screenshot)
                        if img_url:
                            total = math + eng + reas + ga
                            sheet.append_row([str(log_date), current_user, mock_title, math, eng, reas, ga, total, img_url])
                            st.success("Entry Saved! Your streak is looking healthy.")
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()

# --- TAB 2: LEADERBOARD ---
with tab2:
    st.subheader("Leaderboard")
    lb_data = []
    unique_users = [u for u in df['User'].unique() if u in USERS]
    for u in unique_users:
        s, _ = get_streak_info(df, u)
        avg = round(df[df['User']==u]['Total Score'].mean(), 1)
        lb_data.append({"User": u, "Streak 🔥": s, "Avg Score 🎯": avg})
    if lb_data:
        st.dataframe(pd.DataFrame(lb_data).sort_values("Streak 🔥", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No data logged in the leaderboard yet.")

# --- TAB 3: COMMUNITY FEED ---
with tab3:
    st.subheader("The Grind Feed")
    if not df.empty:
        feed_df = df.copy().sort_values("Date", ascending=False).head(15)
        for _, row in feed_df.iterrows():
            with st.container(border=True):
                st.write(f"**{row['User']}** logged a total of **{row['Total Score']}**")
                st.caption(f"{row['Date']} • {row['Mock Title']}")
                st.image(row['Image URL'], use_column_width=True)

# --- TAB 4: MY JOURNEY (CALENDAR & REVIEW) ---
with tab4:
    if current_user == "Select Name":
        st.warning("Please select your name above to view your journey.")
    else:
        user_df = df[df['User'] == current_user].copy()
        logged_dates = user_df['Date'].unique()
        
        st.subheader("Attendance Record")
        st.caption(f"Tracking progress since your start date: {START_DATE}")

        # Generate circles from April 14 to Today
        today = datetime.now().date()
        total_days = (today - START_DATE).days + 1
        
        # Display as a grid of circles
        cols_per_row = 7
        for i in range(0, total_days, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                day_idx = i + j
                if day_idx < total_days:
                    current_date = START_DATE + timedelta(days=day_idx)
                    is_logged = current_date in logged_dates
                    
                    with cols[j]:
                        color = "🟢" if is_logged else "⚪"
                        st.markdown(f"<div style='text-align: center;'>{color}<br><span style='font-size: 0.8em;'>{current_date.strftime('%b %d')}</span></div>", unsafe_allow_html=True)
        
        st.divider()
        
        # PROMINENT REVIEW SECTION
        st.subheader("Review Previous Tests")
        if not user_df.empty:
            # Format the list for the selectbox: [DATE] Title (Score)
            user_df = user_df.sort_values("Date", ascending=False)
            options = []
            for idx, row in user_df.iterrows():
                label = f"📅 {row['Date'].strftime('%d %b')} | {row['Mock Title']} (Score: {row['Total Score']})"
                options.append((label, idx))
            
            selected_label, selected_idx = st.selectbox(
                "Select a test to deep-dive into the analytics:",
                options,
                format_func=lambda x: x[0]
            )
            
            # Show the details for the selected test
            test_data = user_df.loc[selected_idx]
            with st.container(border=True):
                st.markdown(f"## {test_data['Date'].strftime('%A, %d %B %Y')}")
                st.markdown(f"### 📝 {test_data['Mock Title']}")
                st.divider()
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Math", test_data['Math'])
                m2.metric("English", test_data['English'])
                m3.metric("Reasoning", test_data['Reasoning'])
                m4.metric("GA", test_data['GA'])
                
                st.success(f"**Total Score Achieved: {test_data['Total Score']}**")
                st.image(test_data['Image URL'], caption="Official Scorecard", use_column_width=True)
        else:
            st.info("Your history is currently empty. Complete a mock today to see your first entry!")
```

### What's improved:

1.  **The Growth Grid:**
    * It starts exactly on **April 14**. 
    * As each day passes (April 15, 16, etc.), a new circle will automatically appear.
    * If you log a mock, it turns green. If you miss it, it stays white.
    * It shows the date under the circle (e.g., "Apr 14") so you always know where you are in the week.

2.  **Prominent Review Section:**
    * The dropdown now lists tests with the date **first** and prominently: ` 14 Apr | CGL Mock 1 (Score: 145)`.
    * When you select a test, the date appears as a big header (`## Tuesday, 14 April 2026`) so it feels like looking at a diary entry.

3.  **Witty Motivation:**
    * The streak messages now scale from Day 0 up to Day 30+, shifting from "Start now" to "Absolute dominance."
