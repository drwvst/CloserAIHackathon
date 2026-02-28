import streamlit as st
from auth import authenticate_user, create_user
from database import get_users_collection

st.set_page_config(page_title="CloserAI", layout="wide")

# -----------------------------
# Session Initialization
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None  # stores full user document from MongoDB

# -----------------------------
# LOGIN PAGE
# -----------------------------
def login_page():
    st.title("CloserAI")
    st.subheader("Login to Continue")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            success, result = authenticate_user(email, password)
            if success:
                st.session_state.authenticated = True
                st.session_state.user = result
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error(result)

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            success, message = create_user(email, password)
            if success:
                st.success(message)
            else:
                st.error(message)

# -----------------------------
# MAIN APP
# -----------------------------
def main_app():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Analyze Property", "Profile"]
    )

    if st.sidebar.button("Logout"):
        logout()

    if page == "Analyze Property":
        analyze_page()
    elif page == "Profile":
        profile_page()

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# -----------------------------
# ANALYZE PAGE
# -----------------------------
def analyze_page():
    st.title("Analyze Property")

    st.radio(
        "Are you planning to rent or buy?",
        ["Rent", "Buy"],
        horizontal=True,
        key="housing_choice"
    )

    url = st.text_input("Paste Listing URL")

    if st.button("Analyze"):
        if url:
            run_analysis()
        else:
            st.error("Please enter a URL.")

# -----------------------------
# PROFILE PAGE (with MongoDB persistence)
# -----------------------------
def profile_page():
    st.title("Your Financial Profile")

    user_doc = st.session_state.get("user")
    if not user_doc:
        st.error("User data not found. Please log in again.")
        return

    # Use session state to track profile so the UI updates instantly
    profile = st.session_state.user.get("financial_profile", {})

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    # ----------------------------
    # EDITABLE FORM
    # ----------------------------
    if st.session_state.edit_mode:
        with st.form("profile_form"):
            income = st.number_input(
                "Annual Income", value=float(profile.get('income', 0)), step=1000.0
            )
            monthly_debt = st.number_input(
                "Monthly Debt Payments", value=float(profile.get('monthly_debt', 0)), step=100.0
            )
            savings = st.number_input(
                "Savings Available", value=float(profile.get('savings', 0)), step=100.0
            )
            credit_score = st.slider(
                "Credit Score", 300, 850, value=int(profile.get('credit_score', 700))
            )

            submitted = st.form_submit_button("Save Changes")

            if submitted:
                new_profile = {
                    "income": income,
                    "monthly_debt": monthly_debt,
                    "savings": savings,
                    "credit_score": credit_score
                }
                
                # 1. Update MongoDB
                users = get_users_collection()
                users.update_one(
                    {"_id": user_doc["_id"]},
                    {"$set": {"financial_profile": new_profile}}
                )

                # 2. Update session state
                st.session_state.user["financial_profile"] = new_profile
                st.session_state.edit_mode = False 
                
                # 3. Trigger a rerun to show the Read-Only view with new data
                st.rerun() 
        
        if st.button("Cancel"):
            st.session_state.edit_mode = False
            st.rerun()

    # ----------------------------
    # READ-ONLY VIEW
    # ----------------------------
    else:
        st.write(f"**Annual Income:** ${profile.get('income', 0):,.2f}")
        st.write(f"**Monthly Debt Payments:** ${profile.get('monthly_debt', 0):,.2f}")
        st.write(f"**Savings Available:** ${profile.get('savings', 0):,.2f}")
        st.write(f"**Credit Score:** {profile.get('credit_score', 700)}")

        if st.button("Update Information"):
            st.session_state.edit_mode = True
            st.rerun() # Force rerun to switch to the form view

# -----------------------------
# AI LOGIC
# -----------------------------
def run_analysis():
    user_profile = st.session_state.user.get("financial_profile", {})

    rent_or_buy = st.session_state.get("housing_choice", "Buy")
    income = user_profile.get("income", 0)
    monthly_debt = user_profile.get("monthly_debt", 0)
    savings = user_profile.get("savings", 0)
    credit_score = user_profile.get("credit_score", 700)

    # Demo output (replace with real AI logic)
    st.subheader("Analysis Results")
    st.write(f"Housing choice: {rent_or_buy}")
    st.write(f"Income: ${income}")
    st.write(f"Monthly Debt: ${monthly_debt}")
    st.write(f"Savings: ${savings}")
    st.write(f"Credit Score: {credit_score}")

    # Example simple affordability check
    max_monthly_payment = income / 12 * 0.36 - monthly_debt
    st.write(f"Max recommended monthly payment: ${max_monthly_payment:.2f}")
    st.success("AI analysis complete!")

# -----------------------------
# ROUTING LOGIC
# -----------------------------
if not st.session_state.authenticated:
    login_page()
else:
    main_app()