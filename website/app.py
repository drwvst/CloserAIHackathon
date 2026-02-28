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
            try:
                success, result = authenticate_user(email, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = result
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error(result)
            except Exception as exc:
                st.error(f"Login failed: {exc}")

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            try:
                success, message = create_user(email, password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as exc:
                st.error(f"Sign up failed: {exc}")


# CLIENTS PAGE (view and edit client information)
def clients_page():
    st.title("Client Management")
    user = st.session_state.get("user")
    user_id = user["_id"]

    # --- SECTION 1: ADD NEW CLIENT ---
    with st.expander("➕ Register New Client", expanded=False):
        with st.form("new_client_page_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            
            col1, col2 = st.columns(2)
            income = col1.number_input("Annual Income", min_value=0.0, step=1000.0)
            monthly_debt = col2.number_input("Monthly Debt Payments", min_value=0.0, step=100.0)
            savings = col1.number_input("Savings Available", min_value=0.0, step=500.0)
            credit_score = col2.slider("Credit Score", 300, 850, 700)
            
            preferences = st.text_area("Housing/Lifestyle/School Preferences")
            notes = st.text_area("Realtor Notes")

            if st.form_submit_button("Create Client"):
                if name.strip():
                    new_doc = {
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
                    get_clients_collection().insert_one(new_doc)
                    st.success(f"Client {name} added successfully!")
                    st.rerun()
                else:
                    st.error("Client name is required.")

    st.divider()

    # --- SECTION 2: VIEW & UPDATE EXISTING CLIENTS ---
    clients = _get_clients_for_user(user_id)
    if not clients:
        st.info("No clients found. Use the form above to add your first one.")
        return

    client_map = {f"{c['name']} ({c.get('email', 'N/A')})": c for c in clients}
    selected_label = st.selectbox("Select a client to view/edit", options=list(client_map.keys()))
    selected_client = client_map[selected_label]
    client_id = selected_client["_id"]

    # Initialize edit mode state
    if "edit_client_id" not in st.session_state:
        st.session_state.edit_client_id = None

    # --- EDIT MODE ---
    if st.session_state.edit_client_id == str(client_id):
        with st.form("update_client_form"):
            st.subheader(f"Updating {selected_client['name']}")
            u_name = st.text_input("Name", value=selected_client.get("name", ""))
            u_email = st.text_input("Email", value=selected_client.get("email", ""))
            u_phone = st.text_input("Phone", value=selected_client.get("phone", ""))
            
            p = selected_client.get("profile", {})
            c1, c2 = st.columns(2)
            u_income = c1.number_input("Income", value=float(p.get("income", 0)), step=1000.0)
            u_debt = c2.number_input("Monthly Debt", value=float(p.get("monthly_debt", 0)), step=100.0)
            u_savings = c1.number_input("Savings", value=float(p.get("savings", 0)), step=500.0)
            u_credit = c2.slider("Credit Score", 300, 850, int(p.get("credit_score", 700)))
            
            u_prefs = st.text_area("Preferences", value=selected_client.get("preferences", ""))
            u_notes = st.text_area("Notes", value=selected_client.get("notes", ""))

            col_sub, col_can = st.columns([1, 5])
            if col_sub.form_submit_button("Submit"):
                get_clients_collection().update_one(
                    {"_id": client_id},
                    {"$set": {
                        "name": u_name, "email": u_email, "phone": u_phone,
                        "profile": {"income": u_income, "monthly_debt": u_debt, "savings": u_savings, "credit_score": u_credit},
                        "preferences": u_prefs, "notes": u_notes, "updated_at": datetime.now(timezone.utc)
                    }}
                )
                st.session_state.edit_client_id = None
                st.rerun()
            if col_can.form_submit_button("Cancel"):
                st.session_state.edit_client_id = None
                st.rerun()

    # --- READ-ONLY VIEW ---
    else:
        c_head, c_btn = st.columns([4, 1])
        c_head.subheader(f"Details: {selected_client['name']}")
        if c_btn.button("Update Information", type="secondary"):
            st.session_state.edit_client_id = str(client_id)
            st.rerun()

        # Clean display of original fields
        st.write(f"**Email:** {selected_client.get('email')} | **Phone:** {selected_client.get('phone')}")
        p = selected_client.get("profile", {})
        st.write(f"**Income:** ${p.get('income', 0):,.0f} | **Debt:** ${p.get('monthly_debt', 0):,.0f} | **Savings:** ${p.get('savings', 0):,.0f}")
        st.write(f"**Credit Score:** {p.get('credit_score')}")
        st.info(f"**Preferences:** {selected_client.get('preferences')}")
        st.write(f"**Notes:** {selected_client.get('notes')}")


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.selected_client_id = None
    st.rerun()


def _get_clients_for_user(user_id: ObjectId):
    clients = get_clients_collection()
    return list(clients.find({"realtor_id": user_id}).sort("created_at", -1))


def _create_client_form(user_id: ObjectId):
    with st.sidebar.expander("+ Add New Client", expanded=False):
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
    user_id = st.session_state.user["_id"]
    clients = _get_clients_for_user(user_id)

    if not clients:
        st.warning("No clients found. Go to 'Manage Clients' to register one.")
        return

    # Sidebar Switcher
    client_labels = [c["name"] for c in clients]
    current_idx = 0
    for i, c in enumerate(clients):
        if str(c["_id"]) == st.session_state.selected_client_id:
            current_idx = i
            break
    
    selected_name = st.sidebar.selectbox("Active Client", options=client_labels, index=current_idx)
    
    # We define it here as 'active_client'
    active_client = next(c for c in clients if c["name"] == selected_name)
    st.session_state.selected_client_id = str(active_client["_id"])

    # Main Analysis UI
    st.subheader(f"Current Target: {active_client['name']}")

    # --- ADDING PROFILE SUMMARY (Optional but helpful) ---
    with st.expander("Quick View: Client Financials"):
        p = active_client.get("profile", {})
        st.write(f"**Income:** ${p.get('income', 0):,.0f} | **Debt:** ${p.get('monthly_debt', 0):,.0f} | **Credit:** {p.get('credit_score')}")

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
                    
                    # FIXED: Changed 'selected_client' to 'active_client'
                    report = generate_listing_report(active_client, listing, comps)
                    
                    # FIXED: Changed 'selected_client' to 'active_client'
                    _save_analysis(user_id, active_client["_id"], url.strip(), listing, report)
                    
                    st.success("Analysis saved to client history.")
                    st.markdown(report["report_markdown"])
                except Exception as exc:
                    st.error(f"Could not complete analysis: {exc}")

    st.divider()
    # FIXED: Changed 'selected_client' to 'active_client'
    _render_analysis_history(user_id, active_client["_id"])


def main_app():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Manage Clients"])

    if st.sidebar.button("Logout"):
        logout()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Manage Clients":
        clients_page()


if not st.session_state.authenticated:
    login_page()
else:
    main_app()
