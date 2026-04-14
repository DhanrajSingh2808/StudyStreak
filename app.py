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
@st.cache_data(ttl=60)
def load_data():
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            for col in EXPECTED_COLS:
                if col not in df.columns:
                    df[col] = 0
            numeric_cols = ["Math", "English", "Reasoning", "GA", "Total Score"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # FIX 1: Robust date parsing — handles DD/MM/YYYY, YYYY-MM-DD, etc.
            # Convert to string first to avoid any ambiguity, then parse
            df['Date'] = df['Date'].astype(str).str.strip()
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=False, errors='coerce').dt.date
            # FIX 2: Ensure all dates are native Python date objects (not numpy/pandas types)
            df['Date'] = df['Date'].apply(lambda x: x if x is not None else None)
            df = df.dropna(subset=['Date'])  # Drop rows where date couldn't be parsed
            return df
        return pd.DataFrame(columns=EXPECTED_COLS)
    except Exception as e:
        st.error(f"Data load error: {e}")
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
    # FIX 3: Convert to plain Python date to avoid type mismatch in comparisons
    dates = sorted(list(set([
        d if isinstance(d, type(datetime.now().date())) else d
        for d in user_df['Date'].tolist()
        if d is not None
    ])), reverse=True)

    streak = 0
    today = datetime.now().date()

    if dates and (dates[0] == today or dates[0] == today - timedelta(days=1)):
        curr = dates[0]
        for d in dates:
            if d == curr:
                streak += 1
                curr -= timedelta(days=1)
            else:
                break

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
                            # Store date as YYYY-MM-DD string for consistent parsing
                            sheet.append_row([str(log_date), current_user, mock_title, math, eng, reas, ga, total, img_url])
                            st.success("Entry Saved! Your streak is looking healthy.")
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.warning("Please fill in the Mock Title and upload a scorecard!")
    else:
        st.info("Please select your name above to log a mock.")

# --- TAB 2: LEADERBOARD ---
with tab2:
    st.subheader("Leaderboard")
    lb_data = []
    unique_users = [u for u in df['User'].unique() if u in USERS]
    for u in unique_users:
        s, _ = get_streak_info(df, u)
        avg = round(df[df['User'] == u]['Total Score'].mean(), 1)
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

        # FIX 4: Convert logged_dates to a set of plain Python date objects
        logged_dates = set(
            d if isinstance(d, type(datetime.now().date())) else d
            for d in user_df['Date'].tolist()
            if d is not None
        )

        st.subheader("Attendance Record")
        st.caption(f"Tracking progress since your start date: {START_DATE}")

        today = datetime.now().date()
        total_days = (today - START_DATE).days + 1

        cols_per_row = 7
        for i in range(0, total_days, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                day_idx = i + j
                if day_idx < total_days:
                    current_date = START_DATE + timedelta(days=day_idx)
                    # FIX 5: Direct set lookup — no type ambiguity
                    is_logged = current_date in logged_dates

                    with cols[j]:
                        color = "🟢" if is_logged else "⚪"
                        st.markdown(
                            f"<div style='text-align: center;'>{color}<br>"
                            f"<span style='font-size: 0.75em;'>{current_date.strftime('%d %b')}</span></div>",
                            unsafe_allow_html=True
                        )

        st.divider()

        # --- FIX 6: REVIEW SECTION — Clean date-wise expandable list ---
        st.subheader("📋 Review Previous Tests")

        if not user_df.empty:
            user_df_sorted = user_df.sort_values("Date", ascending=False).reset_index(drop=True)

            for _, row in user_df_sorted.iterrows():
                # Format the header: Date | Title | Score
                try:
                    date_str = row['Date'].strftime("%d %b %Y")
                except:
                    date_str = str(row['Date'])

                expander_label = f"📅 {date_str}  ·  {row['Mock Title']}  ·  Score: {row['Total Score']}"

                with st.expander(expander_label):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Math", row['Math'])
                    col2.metric("English", row['English'])
                    col3.metric("Reasoning", row['Reasoning'])
                    col4.metric("GA", row['GA'])
                    st.success(f"**Total Score: {row['Total Score']}**")
                    if row['Image URL']:
                        st.image(row['Image URL'], caption="Scorecard", use_column_width=True)
        else:
            st.info("Your history is currently empty. Complete a mock today to see your first entry!")
