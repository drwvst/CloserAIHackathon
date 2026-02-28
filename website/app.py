from datetime import datetime, timezone

import streamlit as st
from bson import ObjectId

from agent import generate_listing_report
from auth import authenticate_user, create_user
from database import get_analyses_collection, get_clients_collection
from ZillowScraper import get_area_comps, scrape_listing

st.set_page_config(page_title="CloserAI", layout="wide")


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_client_id" not in st.session_state:
    st.session_state.selected_client_id = None


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


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.selected_client_id = None
    st.rerun()


def _get_clients_for_user(user_id: ObjectId):
    clients = get_clients_collection()
    return list(clients.find({"realtor_id": user_id}).sort("created_at", -1))


def _create_client_form(user_id: ObjectId):
    with st.expander("+ Add New Client", expanded=False):
        with st.form("new_client_form"):
            name = st.text_input("Client Name")
            email = st.text_input("Client Email")
            phone = st.text_input("Client Phone")
            income = st.number_input("Annual Income", min_value=0.0, step=1000.0)
            monthly_debt = st.number_input("Monthly Debt Payments", min_value=0.0, step=100.0)
            savings = st.number_input("Savings Available", min_value=0.0, step=500.0)
            credit_score = st.slider("Credit Score", 300, 850, 700)
            preferences = st.text_area("Housing/Lifestyle/School Preferences")
            notes = st.text_area("Realtor Notes")

            submitted = st.form_submit_button("Create Client")
            if submitted:
                if not name.strip():
                    st.error("Client name is required.")
                    return
                doc = {
                    "realtor_id": user_id,
                    "name": name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "profile": {
                        "income": income,
                        "monthly_debt": monthly_debt,
                        "savings": savings,
                        "credit_score": credit_score,
                    },
                    "preferences": preferences.strip(),
                    "notes": notes.strip(),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                get_clients_collection().insert_one(doc)
                st.success("Client created.")
                st.rerun()


def _render_client_sidebar(user_id: ObjectId):
    st.sidebar.subheader("Clients")
    _create_client_form(user_id)
    clients = _get_clients_for_user(user_id)

    if not clients:
        st.sidebar.info("No clients yet. Add one to begin.")
        return None

    labels = [f"{c['name']} ({c.get('email','no email')})" for c in clients]
    idx = 0
    for i, c in enumerate(clients):
        if str(c["_id"]) == st.session_state.selected_client_id:
            idx = i
            break

    selected_label = st.sidebar.radio("Select a client", labels, index=idx)
    selected_client = clients[labels.index(selected_label)]
    st.session_state.selected_client_id = str(selected_client["_id"])

    if st.sidebar.button("Delete Selected Client", type="secondary"):
        get_clients_collection().delete_one({"_id": selected_client["_id"], "realtor_id": user_id})
        get_analyses_collection().delete_many({"client_id": selected_client["_id"], "realtor_id": user_id})
        st.session_state.selected_client_id = None
        st.success("Client deleted.")
        st.rerun()

    return selected_client


def _save_analysis(realtor_id: ObjectId, client_id: ObjectId, url: str, listing: dict, report: dict):
    analyses = get_analyses_collection()
    analyses.insert_one(
        {
            "realtor_id": realtor_id,
            "client_id": client_id,
            "url": url,
            "listing": listing,
            "result": report,
            "created_at": datetime.now(timezone.utc),
        }
    )


def _render_analysis_history(realtor_id: ObjectId, client_id: ObjectId):
    st.subheader("Saved Listing Analyses")
    analyses = list(
        get_analyses_collection()
        .find({"realtor_id": realtor_id, "client_id": client_id})
        .sort("created_at", -1)
    )

    if not analyses:
        st.info("No analyses saved for this client yet.")
        return

    for item in analyses:
        result = item.get("result", {})
        with st.expander(f"{item.get('url')} • Fit Score {result.get('fit_score', 'N/A')}"):
            st.caption(f"Model: {result.get('model_used', 'unknown')}")
            st.markdown(result.get("report_markdown", "No report available."))


def dashboard_page():
    st.title("Realtor Dashboard")
    user = st.session_state.get("user")
    user_id = user["_id"]

    selected_client = _render_client_sidebar(user_id)
    if not selected_client:
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Client Profile")
        st.write(f"**Name:** {selected_client.get('name', '')}")
        st.write(f"**Email:** {selected_client.get('email', '')}")
        st.write(f"**Phone:** {selected_client.get('phone', '')}")
        profile = selected_client.get("profile", {})
        st.write(f"**Income:** ${profile.get('income', 0):,.0f}")
        st.write(f"**Monthly Debt:** ${profile.get('monthly_debt', 0):,.0f}")
        st.write(f"**Savings:** ${profile.get('savings', 0):,.0f}")
        st.write(f"**Credit Score:** {profile.get('credit_score', 700)}")
        st.write("**Preferences:**")
        st.write(selected_client.get("preferences", ""))
        st.write("**Notes:**")
        st.write(selected_client.get("notes", ""))

    with col2:
        st.subheader("Analyze New Listing")
        url = st.text_input("Paste listing URL (Zillow/Realtor)", key="listing_url")
        if st.button("Run Analysis", type="primary"):
            if not url.strip():
                st.error("Please provide a listing URL.")
            else:
                with st.spinner("Scraping listing + generating agent report..."):
                    try:
                        listing = scrape_listing(url.strip())
                        comps = get_area_comps(listing.get("city"), listing.get("state"), max_results=5)
                        report = generate_listing_report(selected_client, listing, comps)
                        _save_analysis(user_id, selected_client["_id"], url.strip(), listing, report)
                        st.success("Analysis saved to client history.")
                        st.markdown(report["report_markdown"])
                    except Exception as exc:
                        st.error(f"Could not complete analysis: {exc}")

    st.divider()
    _render_analysis_history(user_id, selected_client["_id"])


def main_app():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard"])

    if st.sidebar.button("Logout"):
        logout()

    if page == "Dashboard":
        dashboard_page()


if not st.session_state.authenticated:
    login_page()
else:
    main_app()
