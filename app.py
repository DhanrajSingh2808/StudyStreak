import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuration & Setup ---
st.set_page_config(page_title="Mock Streak", page_icon="🔥", layout="centered")

# Standardized headers
EXPECTED_COLS = ["Date", "User", "Mock Title", "Math", "English", "Reasoning", "GA", "Total Score", "Image URL"]
START_DATE = datetime(2026, 4, 14).date()

# ─────────────────────────────────────────────
# INJECT GLOBAL STYLES + ANIMATIONS
# ─────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>
/* ── Root Tokens ── */
:root {
  --bg:        #0a0a0c;
  --surface:   #13131a;
  --glass:     rgba(255,255,255,0.04);
  --border:    rgba(255,120,30,0.18);
  --ember:     #ff6a00;
  --flame:     #ff9c40;
  --glow:      #ffb347;
  --cold:      #2e2e3a;
  --text:      #f0ede8;
  --muted:     #7a7a8c;
  --success:   #4cff91;
  --font-head: 'Bebas Neue', sans-serif;
  --font-body: 'DM Sans', sans-serif;
}

/* ── Base Reset ── */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--font-body) !important;
}

[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(255,106,0,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 40% 30% at 80% 80%, rgba(255,60,0,0.06) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--ember); border-radius: 4px; }

/* ── Typography ── */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: var(--font-head) !important;
  letter-spacing: 0.04em;
}

/* ── Sidebar / Selectbox ── */
[data-testid="stSelectbox"] > div > div {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 12px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
  background: var(--surface);
  border-radius: 14px;
  padding: 6px 8px;
  border: 1px solid var(--border);
  gap: 6px;
}
[data-testid="stTabs"] button[role="tab"] {
  color: var(--muted) !important;
  font-family: var(--font-body) !important;
  font-weight: 500 !important;
  border-radius: 10px !important;
  transition: all .25s ease !important;
  border: none !important;
  padding: 8px 18px !important;
  white-space: nowrap !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, var(--ember), #c43a00) !important;
  color: #fff !important;
  box-shadow: 0 0 18px rgba(255,106,0,0.5) !important;
}
[data-testid="stTabs"] button[role="tab"]:hover {
  color: var(--flame) !important;
}

/* ── Buttons ── */
.stButton > button {
  background: linear-gradient(135deg, var(--ember) 0%, #c43a00 100%) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  font-family: var(--font-body) !important;
  font-weight: 600 !important;
  letter-spacing: 0.03em !important;
  transition: all .3s ease !important;
  box-shadow: 0 4px 20px rgba(255,106,0,0.3) !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 30px rgba(255,106,0,0.55) !important;
}
.stButton > button:active {
  transform: translateY(0px) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  font-family: var(--font-body) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: var(--ember) !important;
  box-shadow: 0 0 0 2px rgba(255,106,0,0.2) !important;
}

/* ── Form container ── */
[data-testid="stForm"] {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px;
  backdrop-filter: blur(12px);
}

/* ── Info / Alert boxes ── */
[data-testid="stAlert"] {
  background: var(--glass) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  backdrop-filter: blur(8px) !important;
  color: var(--text) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
  border-radius: 16px !important;
  overflow: hidden !important;
  border: 1px solid var(--border) !important;
}
[data-testid="stDataFrame"] th {
  background: var(--surface) !important;
  color: var(--flame) !important;
  font-family: var(--font-head) !important;
  letter-spacing: 0.06em !important;
}
[data-testid="stDataFrame"] td {
  background: var(--glass) !important;
  color: var(--text) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--glass) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  backdrop-filter: blur(8px) !important;
}
[data-testid="stExpander"] summary {
  color: var(--text) !important;
  font-weight: 500 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px !important;
  backdrop-filter: blur(8px);
}
[data-testid="stMetric"] label {
  color: var(--muted) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--glow) !important;
  font-family: var(--font-head) !important;
  font-size: 1.8rem !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--glass) !important;
  border: 1px dashed var(--border) !important;
  border-radius: 14px !important;
  color: var(--muted) !important;
}

/* ── Divider ── */
hr {
  border-color: var(--border) !important;
}

/* ── Container / Card ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--glass) !important;
  border: 1px solid var(--border) !important;
  border-radius: 18px !important;
  backdrop-filter: blur(10px) !important;
}

/* ── Labels ── */
label, [data-testid="stWidgetLabel"] p {
  color: var(--muted) !important;
  font-size: 0.8rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
  color: var(--ember) !important;
}

/* ── Streak Banner (custom HTML) ── */
@keyframes ember-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(255,106,0,0.4), 0 0 60px rgba(255,106,0,0.15); }
  50%       { box-shadow: 0 0 35px rgba(255,150,0,0.6), 0 0 80px rgba(255,100,0,0.25); }
}
@keyframes flame-flicker {
  0%   { transform: scaleY(1)   rotate(-1deg); }
  25%  { transform: scaleY(1.04) rotate(1.5deg); }
  50%  { transform: scaleY(0.97) rotate(-0.5deg); }
  75%  { transform: scaleY(1.03) rotate(2deg); }
  100% { transform: scaleY(1)   rotate(-1deg); }
}
@keyframes float-up {
  0%   { opacity: 1;  transform: translateY(0)    scale(1); }
  100% { opacity: 0;  transform: translateY(-80px) scale(0.3); }
}
@keyframes count-up {
  from { opacity: 0; transform: scale(0.6) translateY(10px); }
  to   { opacity: 1; transform: scale(1)   translateY(0); }
}
@keyframes slide-in {
  from { opacity: 0; transform: translateX(-20px); }
  to   { opacity: 1; transform: translateX(0); }
}
@keyframes cell-pop {
  0%   { transform: scale(0.5); opacity: 0; }
  70%  { transform: scale(1.15); }
  100% { transform: scale(1);   opacity: 1; }
}
@keyframes glow-pulse {
  0%, 100% { filter: drop-shadow(0 0 4px #ff6a00) drop-shadow(0 0 8px #ff9c40); }
  50%       { filter: drop-shadow(0 0 8px #ffb347) drop-shadow(0 0 20px #ff6a00); }
}

/* ── Attendance grid cells ── */
.flame-active {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  margin: 3px;
  cursor: default;
  animation: cell-pop 0.5s cubic-bezier(.34,1.56,.64,1) both;
}
.flame-active .fa-icon {
  font-size: 1.35rem;
  line-height: 1;
  filter: drop-shadow(0 0 5px #ff6a00) drop-shadow(0 0 10px #ff4500);
  animation: flame-flicker 2s ease-in-out infinite, glow-pulse 2.5s ease-in-out infinite;
  transform-origin: bottom center;
  display: block;
}
.flame-active .fa-label {
  font-size: 0.48rem;
  color: #ff9c40;
  font-family: 'DM Sans', sans-serif;
  margin-top: 1px;
  letter-spacing: 0.02em;
}
.flame-cold {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  margin: 3px;
  opacity: 0.28;
  cursor: default;
}
.flame-cold .fc-icon {
  width: 20px; height: 20px;
  border-radius: 50%;
  background: #2e2e3a;
  border: 1px solid #3a3a4a;
  display: block;
}
.flame-cold .fc-label {
  font-size: 0.48rem;
  color: #4a4a5a;
  font-family: 'DM Sans', sans-serif;
  margin-top: 2px;
}

/* ── Card animation classes (avoid inline animation: which gets stripped) ── */
.anim-card { animation: slide-in 0.4s ease both; }
.anim-d0  { animation-delay: 0s; }
.anim-d1  { animation-delay: 0.07s; }
.anim-d2  { animation-delay: 0.14s; }
.anim-d3  { animation-delay: 0.21s; }
.anim-d4  { animation-delay: 0.28s; }
.anim-d5  { animation-delay: 0.35s; }
.anim-d6  { animation-delay: 0.42s; }
.anim-d7  { animation-delay: 0.49s; }
.anim-d8  { animation-delay: 0.56s; }
.anim-d9  { animation-delay: 0.63s; }

/* ── Ember particles ── */
.ember {
  position: absolute;
  border-radius: 50%;
  background: var(--ember);
  animation: float-up linear infinite;
  pointer-events: none;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 2. Authentication & Connection
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# 3. Helper Functions
# ─────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_data():
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            df = df.dropna(subset=['Date'])
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
        return 0, "Log your first mock to start the fire!"
    user_df = df[df['User'] == user].copy()
    dates = sorted(list(set(user_df['Date'].tolist())), reverse=True)
    streak = 0
    today = datetime.now().date()
    if dates:
        if dates[0] >= today - timedelta(days=1):
            curr = dates[0]
            for d in dates:
                if d == curr:
                    streak += 1
                    curr -= timedelta(days=1)
                else:
                    break
    msg = "Keep going! 👊" if streak > 0 else "Start your streak!"
    return streak, msg


def flame_active_cell(date_label):
    """CSS+emoji flame cell for logged days — no SVG, Streamlit-safe."""
    return f"""<div class="flame-active">
      <span class="fa-icon">🔥</span>
      <span class="fa-label">{date_label}</span>
    </div>"""

def flame_cold_cell(date_label):
    """Grey dot for unlogged days."""
    return f"""<div class="flame-cold">
      <div class="fc-icon"></div>
      <span class="fc-label">{date_label}</span>
    </div>"""


# ─────────────────────────────────────────────
# 4. Header
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 8px 0 4px;">
  <p style="font-family:'Bebas Neue'; font-size:3.2rem; letter-spacing:0.1em;
            background: linear-gradient(135deg,#ffed4a,#ff9c40,#ff4500);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            margin:0; line-height:1;">
    🔥 MOCK STREAK
  </p>
  <p style="color:#7a7a8c; font-size:0.85rem; letter-spacing:0.15em; text-transform:uppercase; margin:4px 0 0;">
    TRACK · COMPETE · DOMINATE
  </p>
</div>
""", unsafe_allow_html=True)

USERS = ["Select Name", "Dhanraj", "Nishant", "Naman", "Anon"]
current_user = st.selectbox("", USERS, label_visibility="collapsed",
                             placeholder="— Select your name —")

df = load_data()


# ─────────────────────────────────────────────
# 5. Streak Banner
# ─────────────────────────────────────────────
if current_user != "Select Name":
    streak, message = get_streak_info(df, current_user)

    # Pick banner colour intensity based on streak
    if streak >= 7:
        glow_color = "rgba(255,100,0,0.7)"
        ring_color = "#ff6a00"
    elif streak >= 3:
        glow_color = "rgba(255,130,0,0.5)"
        ring_color = "#ff8c00"
    else:
        glow_color = "rgba(255,160,0,0.3)"
        ring_color = "#ffb347"

    # Ember particle HTML (purely decorative)
    ember_particles = "".join([
        f"""<div class="ember" style="
              width:{3+i%4}px; height:{3+i%4}px;
              left:{10+i*11}%;
              bottom:{5+i%3*8}px;
              opacity:{0.6+i%3*0.15};
              animation-duration:{1.5+i*0.4}s;
              animation-delay:{i*0.25}s;">
            </div>"""
        for i in range(8)
    ])

    st.markdown(f"""
    <div style="
      position:relative; overflow:hidden;
      background: linear-gradient(135deg, rgba(255,80,0,0.12) 0%, rgba(20,15,10,0.9) 100%);
      border: 1px solid {ring_color};
      border-radius: 20px;
      padding: 22px 28px;
      margin: 12px 0 18px;
      animation: ember-pulse 3s ease-in-out infinite;
      backdrop-filter: blur(10px);
    ">
      {ember_particles}
      <div style="display:flex; align-items:center; justify-content:space-between; position:relative; z-index:1;">
        <div>
          <p style="margin:0; font-family:'Bebas Neue'; font-size:0.85rem;
                    letter-spacing:0.2em; color:#7a7a8c; text-transform:uppercase;">
            Current Streak
          </p>
          <p style="margin:0; font-family:'Bebas Neue'; font-size:4rem;
                    background: linear-gradient(135deg,#ffed4a,#ff6a00);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                    line-height:1; animation: count-up 0.6s cubic-bezier(.34,1.56,.64,1) both;">
            {streak} DAYS
          </p>
          <p style="margin:4px 0 0; color:#c0b8b0; font-size:0.88rem; animation: slide-in 0.5s 0.3s ease both; opacity:0; animation-fill-mode:forwards;">
            {message}
          </p>
        </div>
        <div style="font-size:4.5rem; animation: flame-flicker 1.8s ease-in-out infinite;
                    transform-origin: bottom center; filter: drop-shadow(0 0 12px #ff6a00);">
          🔥
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="
      background: rgba(255,255,255,0.03); border:1px dashed rgba(255,106,0,0.2);
      border-radius:16px; padding:18px; text-align:center; color:#7a7a8c;
      font-size:0.9rem; letter-spacing:0.05em; margin-bottom:16px;
    ">
      Select your name above to ignite your streak 🔥
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sync button (compact)
# ─────────────────────────────────────────────
col_sync, _ = st.columns([1, 4])
with col_sync:
    if st.button("⟳ Sync"):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────
# 6. Tabs
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Mock", "🏆 Leaderboard", "📸 Feed", "📅 My Journey"])


# ── TAB 1: LOG MOCK ──────────────────────────
with tab1:
    if current_user == "Select Name":
        st.markdown("""
        <div style="text-align:center; padding:40px; color:#7a7a8c;">
          <div style="font-size:3rem; margin-bottom:12px;">🔒</div>
          <p style="font-family:'Bebas Neue'; font-size:1.4rem; letter-spacing:0.1em;">
            SELECT YOUR NAME TO LOG A MOCK
          </p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <p style="font-family:'Bebas Neue'; font-size:1.5rem; letter-spacing:0.08em;
                  color:#ff9c40; margin-bottom:8px;">
          LOG TODAY'S MOCK, {current_user.upper()}
        </p>""", unsafe_allow_html=True)

        with st.form("mock_form", clear_on_submit=True):
            log_date = st.date_input("Exam Date", datetime.now())
            mock_title = st.text_input("Mock Title", placeholder="e.g. SSC CGL Full test 1 #12")

            st.markdown("<p style='color:#7a7a8c; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; margin:12px 0 4px;'>Section Scores</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                math = st.number_input("Math", min_value=0.0, step=0.5)
                reas = st.number_input("Reasoning", min_value=0.0, step=0.5)
            with c2:
                eng = st.number_input("English", min_value=0.0, step=0.5)
                ga = st.number_input("GA", min_value=0.0, step=0.5)

            screenshot = st.file_uploader("📎 Attach Scorecard", type=['png', 'jpg', 'jpeg'])

            submitted = st.form_submit_button("🚀 Submit Score")
            if submitted:
                if mock_title and screenshot:
                    with st.spinner("Uploading to the scoreboard..."):
                        img_url = upload_to_imgbb(screenshot)
                        if img_url:
                            total = math + eng + reas + ga
                            sheet.append_row([str(log_date), current_user, mock_title,
                                              math, eng, reas, ga, total, img_url])
                            st.success("🔥 Entry logged! Keep the fire burning.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Image upload failed. Try again.")
                else:
                    st.warning("Fill in the mock title and attach a scorecard to submit.")


# ── TAB 2: LEADERBOARD ───────────────────────
with tab2:
    st.markdown("""
    <p style="font-family:'Bebas Neue'; font-size:1.5rem; letter-spacing:0.08em;
              color:#ff9c40; margin-bottom:8px;">
      WHO'S ON FIRE?
    </p>""", unsafe_allow_html=True)

    lb_data = []
    active_users = [u for u in USERS if u != "Select Name"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    for u in active_users:
        s, _ = get_streak_info(df, u)
        scores = df[df['User'] == u]['Total Score']
        avg = round(scores.mean(), 1) if not scores.empty else 0
        total_logs = len(df[df['User'] == u])
        lb_data.append({"User": u, "🔥 Streak": s, "🎯 Avg Score": avg, "📋 Tests": total_logs})

    lb_df = pd.DataFrame(lb_data).sort_values("🔥 Streak", ascending=False).reset_index(drop=True)

    # Render custom leaderboard cards
    for i, row in lb_df.iterrows():
        medal = medals[i] if i < len(medals) else "•"
        is_me = row['User'] == current_user
        border = "rgba(255,106,0,0.6)" if is_me else "rgba(255,255,255,0.07)"
        bg = "rgba(255,106,0,0.08)" if is_me else "rgba(255,255,255,0.03)"
        name_color = "#ff9c40" if is_me else "#f0ede8"

        streak_bar_pct = min(row['🔥 Streak'] * 10, 100)

        delay_class = f"anim-d{min(i, 9)}"
        box_shadow = "box-shadow:0 0 20px rgba(255,106,0,0.2);" if is_me else ""
        st.markdown(f"""
        <div class="anim-card {delay_class}" style="background:{bg};border:1px solid {border};border-radius:16px;padding:16px 20px;margin-bottom:10px;backdrop-filter:blur(8px);{box_shadow}">
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center; gap:14px;">
              <span style="font-size:1.6rem;">{medal}</span>
              <div>
                <p style="margin:0; font-family:'Bebas Neue'; font-size:1.25rem;
                          letter-spacing:0.06em; color:{name_color};">
                  {row['User']}{'  ← YOU' if is_me else ''}
                </p>
                <p style="margin:0; color:#7a7a8c; font-size:0.78rem;">
                  {row['📋 Tests']} tests logged
                </p>
              </div>
            </div>
            <div style="text-align:right;">
              <p style="margin:0; font-family:'Bebas Neue'; font-size:1.8rem;
                        background:linear-gradient(135deg,#ffed4a,#ff6a00);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                {row['🔥 Streak']} 🔥
              </p>
              <p style="margin:0; color:#7a7a8c; font-size:0.78rem;">avg {row['🎯 Avg Score']}</p>
            </div>
          </div>
          <div style="margin-top:10px; height:4px; background:rgba(255,255,255,0.06); border-radius:4px;">
            <div style="height:100%; width:{streak_bar_pct}%;
                        background:linear-gradient(90deg,#ff4500,#ffb347);
                        border-radius:4px; transition:width 1s ease;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 3: FEED ──────────────────────────────
with tab3:
    st.markdown("""
    <p style="font-family:'Bebas Neue'; font-size:1.5rem; letter-spacing:0.08em;
              color:#ff9c40; margin-bottom:8px;">
      RECENT MOCKS
    </p>""", unsafe_allow_html=True)

    if not df.empty:
        feed_df = df.sort_values("Date", ascending=False).head(10)
        for idx, (_, row) in enumerate(feed_df.iterrows()):
            user_scores = df[df['User'] == row['User']]['Total Score']
            personal_best = user_scores.max() if not user_scores.empty else 0
            is_pb = row['Total Score'] >= personal_best and len(user_scores) > 1

            pb_badge = """<span style="background:linear-gradient(135deg,#ffed4a,#ff9c40);
                            color:#000; font-size:0.65rem; font-weight:700;
                            padding:2px 8px; border-radius:20px; letter-spacing:0.05em;
                            margin-left:8px;">PB 🏆</span>""" if is_pb else ""

            delay_class = f"anim-d{min(idx, 9)}"
            st.markdown(f"""
            <div class="anim-card {delay_class}" style="
              background: rgba(255,255,255,0.03); border:1px solid rgba(255,106,0,0.15);
              border-radius:18px; overflow:hidden; margin-bottom:16px;
            ">
              <div style="padding:16px 20px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                  <div>
                    <p style="margin:0; font-family:'Bebas Neue'; font-size:1.15rem;
                              letter-spacing:0.05em; color:#f0ede8;">
                      {row['User']} {pb_badge}
                    </p>
                    <p style="margin:2px 0 0; color:#7a7a8c; font-size:0.78rem;">
                      {row['Mock Title']} · {row['Date'].strftime('%d %b %Y') if hasattr(row['Date'], 'strftime') else row['Date']}
                    </p>
                  </div>
                  <div style="text-align:right;">
                    <p style="margin:0; font-family:'Bebas Neue'; font-size:2rem;
                              background:linear-gradient(135deg,#ffed4a,#ff6a00);
                              -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                              line-height:1;">
                      {row['Total Score']}
                    </p>
                    <p style="margin:0; color:#7a7a8c; font-size:0.72rem;">TOTAL</p>
                  </div>
                </div>
              </div>
              <img src="{row['Image URL']}" style="width:100%; display:block;
                    max-height:280px; object-fit:cover; border-top:1px solid rgba(255,106,0,0.1);">
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:50px; color:#7a7a8c;">
          <div style="font-size:2.5rem; margin-bottom:12px;">🏜️</div>
          <p>No entries yet. Log your first mock to light the feed!</p>
        </div>""", unsafe_allow_html=True)


# ── TAB 4: MY JOURNEY ────────────────────────
with tab4:
    if current_user == "Select Name":
        st.markdown("""
        <div style="text-align:center; padding:40px; color:#7a7a8c;">
          <div style="font-size:3rem; margin-bottom:12px;">🔒</div>
          <p style="font-family:'Bebas Neue'; font-size:1.4rem; letter-spacing:0.1em;">
            SELECT YOUR NAME TO VIEW YOUR JOURNEY
          </p>
        </div>""", unsafe_allow_html=True)
    else:
        user_df = df[df['User'] == current_user].copy().sort_values("Date", ascending=False)
        logged_dates = set(user_df['Date'].unique())
        today = datetime.now().date()
        total_days = (today - START_DATE).days + 1

        # ── Stats row ──
        total_tests = len(user_df)
        best_score = int(user_df['Total Score'].max()) if total_tests else 0
        avg_score = round(user_df['Total Score'].mean(), 1) if total_tests else 0
        streak_now, _ = get_streak_info(df, current_user)

        st.markdown(f"""
        <p style="font-family:'Bebas Neue'; font-size:1.5rem; letter-spacing:0.08em;
                  color:#ff9c40; margin-bottom:8px;">
          {current_user.upper()}'S JOURNEY
        </p>""", unsafe_allow_html=True)

        s1, s2, s3, s4 = st.columns(4)
        for col, label, val, suffix in [
            (s1, "Tests", total_tests, ""),
            (s2, "Best", best_score, "pts"),
            (s3, "Average", avg_score, "pts"),
            (s4, "Streak", streak_now, "🔥"),
        ]:
            with col:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,106,0,0.2);
                            border-radius:14px; padding:14px 12px; text-align:center;">
                  <p style="margin:0; color:#7a7a8c; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.1em;">{label}</p>
                  <p style="margin:4px 0 0; font-family:'Bebas Neue'; font-size:1.9rem;
                            background:linear-gradient(135deg,#ffed4a,#ff6a00);
                            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                    {val}{suffix}
                  </p>
                </div>
                """, unsafe_allow_html=True)

        # ── Attendance Grid ──
        st.markdown("""
        <p style="font-family:'Bebas Neue'; font-size:1.2rem; letter-spacing:0.1em;
                  color:#ff9c40; margin: 22px 0 10px;">
          ATTENDANCE GRID
        </p>""", unsafe_allow_html=True)

        # Build grid HTML
        grid_html = '<div style="display:flex; flex-wrap:wrap; gap:2px;">'
        for i in range(total_days):
            check_date = START_DATE + timedelta(days=i)
            date_label = check_date.strftime('%d')
            if check_date in logged_dates:
                grid_html += flame_active_cell(date_label)
            else:
                grid_html += flame_cold_cell(date_label)
        grid_html += '</div>'

        st.markdown(grid_html, unsafe_allow_html=True)

        # Legend
        st.markdown(f"""
        <div style="display:flex; gap:16px; margin:8px 0 20px; font-size:0.75rem; color:#7a7a8c;">
          <span>🔥 Logged</span>
          <span style="opacity:0.4;">⚫ Missed</span>
          <span style="color:#ff6a00;">{len(logged_dates)} / {total_days} days</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr style="border-color:rgba(255,106,0,0.15);">', unsafe_allow_html=True)

        # ── Review list ──
        st.markdown("""
        <p style="font-family:'Bebas Neue'; font-size:1.2rem; letter-spacing:0.1em;
                  color:#ff9c40; margin-bottom:10px;">
          PREVIOUS MOCKS
        </p>""", unsafe_allow_html=True)

        if not user_df.empty:
            for _, row in user_df.iterrows():
                date_str = row['Date'].strftime('%d %b %Y') if hasattr(row['Date'], 'strftime') else str(row['Date'])
                header = f"📅  {date_str}  ·  {row['Mock Title']}  ·  {row['Total Score']} pts"
                with st.expander(header):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Math", row['Math'])
                    m2.metric("English", row['English'])
                    m3.metric("Reasoning", row['Reasoning'])
                    m4.metric("GA", row['GA'])
                    st.image(row['Image URL'], caption=f"Scorecard — {row['Mock Title']}", use_column_width=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:32px; color:#7a7a8c;">
              No entries yet. Start logging to see your history!
            </div>""", unsafe_allow_html=True)
