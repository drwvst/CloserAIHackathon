import streamlit as st

st.set_page_config(page_title="CloserAI", layout="wide")

# -----------------------------
# Session Initialization
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "income": 0,
        "monthly_debt": 0,
        "savings": 0,
        "credit_score": 700
    }

# -----------------------------
# LOGIN PAGE
# -----------------------------
def login_page():
    st.title("CloserAI")
    st.subheader("Login to Continue")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Simple mock authentication
        if email and password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Please enter email and password.")


# -----------------------------
# MAIN APP
# -----------------------------
def main_app():
    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Go to",
        ["Analyze Property", "Profile"]
    )

    st.sidebar.button("Logout", on_click=logout)

    if page == "Analyze Property":
        analyze_page()

    elif page == "About / Profile":
        profile_page()


def logout():
    st.session_state.authenticated = False
    st.rerun()


# -----------------------------
# ANALYZE PAGE
# -----------------------------
def analyze_page():
    st.title("Analyze Property")

    st.radio(
        "Are you planning to rent or buy?",
        ["Rent", "Buy"],
        horizontal=True  # makes it look cleaner
        )

    url = st.text_input("Paste Listing URL")

    if st.button("Analyze"):
        if url:
            st.success("Scraper will run here later.")
        else:
            st.error("Please enter a URL.")


# -----------------------------
# PROFILE / ABOUT PAGE
# -----------------------------
def profile_page():
    st.title("Your Financial Profile")

    with st.form("profile_form"):
        income = st.number_input("Annual Income", value=st.session_state.user_data["income"])
        monthly_debt = st.number_input("Monthly Debt Payments", value=st.session_state.user_data["monthly_debt"])
        savings = st.number_input("Savings Available", value=st.session_state.user_data["savings"])
        credit_score = st.slider("Credit Score", 300, 850, st.session_state.user_data["credit_score"])

        submitted = st.form_submit_button("Save")

        if submitted:
            st.session_state.user_data = {
                "income": income,
                "monthly_debt": monthly_debt,
                "savings": savings,
                "credit_score": credit_score
            }
            st.success("Profile updated successfully.")


# -----------------------------
# ROUTING LOGIC
# -----------------------------
if not st.session_state.authenticated:
    login_page()
else:
    main_app()