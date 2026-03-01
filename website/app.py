from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from bson import ObjectId

from agent import generate_listing_report
from auth import authenticate_user, create_user
from database import get_analyses_collection, get_clients_collection
from ZillowScraper import get_area_comps, scrape_listing

st.set_page_config(page_title="Agent", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_client_id" not in st.session_state:
    st.session_state.selected_client_id = None


def login_page():
    st.title("Agent²")
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

    # 1. Initialize the expanded state
    if "reg_expanded" not in st.session_state:
        st.session_state.reg_expanded = False

    # 2. SECTION 1: ADD NEW CLIENT
    if not st.session_state.reg_expanded:
        if st.button("➕ Register New Client"):
            st.session_state.reg_expanded = True
            st.rerun()
    else:
        with st.expander("Register New Client", expanded=True):
            with st.form("new_client_page_form", clear_on_submit=True):
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

                c_col1, c_col2 = st.columns([1, 4])
                submitted = c_col1.form_submit_button("Create")
                if c_col2.form_submit_button("Cancel"):
                    st.session_state.reg_expanded = False
                    st.rerun()

                if submitted:
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

                        st.session_state.reg_expanded = False
                        st.toast(f"Success! {name} added.", icon="✅")
                        st.rerun()
                    else:
                        st.error("Client name is required.")

    st.divider()

    clients = _get_clients_for_user(user_id)
    if not clients:
        st.info("No clients found. Open the registration tool above to add your first one.")
        return

    client_map = {f"{c['name']} ({c.get('email', 'N/A')})": c for c in clients}
    selected_label = st.selectbox("Select a client to view/edit", options=list(client_map.keys()))
    selected_client = client_map[selected_label]
    client_id = selected_client["_id"]

    st.divider()

    if "edit_client_id" not in st.session_state:
        st.session_state.edit_client_id = None

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
                        "profile": {"income": u_income, "monthly_debt": u_debt, "savings": u_savings,
                                    "credit_score": u_credit},
                        "preferences": u_prefs, "notes": u_notes, "updated_at": datetime.now(timezone.utc)
                    }}
                )
                st.session_state.edit_client_id = None
                st.rerun()
            if col_can.form_submit_button("Cancel"):
                st.session_state.edit_client_id = None
                st.rerun()
    else:
        c_head, c_edit, c_del = st.columns([3, 1, 1])
        c_head.subheader(f"Details: {selected_client['name']}")

        if c_edit.button("Update Info", use_container_width=True):
            st.session_state.edit_client_id = str(client_id)
            st.rerun()

        if c_del.button("Delete Client", type="primary", use_container_width=True):
            st.session_state.confirm_delete = str(client_id)

        if st.session_state.get("confirm_delete") == str(client_id):
            pass 

        st.divider()

        p = selected_client.get("profile", {})
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Annual Income", f"${p.get('income', 0):,.0f}")
        m2.metric("Monthly Debt", f"${p.get('monthly_debt', 0):,.0f}")
        m3.metric("Savings", f"${p.get('savings', 0):,.0f}")
        m4.metric("Credit Score", p.get('credit_score', 'N/A'))

        st.markdown("---")
        col_contact, col_pref = st.columns(2)

        with col_contact:
            st.markdown("### Contact Info")
            st.write(f"📧 **Email:** {selected_client.get('email', 'N/A')}")
            st.write(f"📞 **Phone:** {selected_client.get('phone', 'N/A')}")
            st.write(f"📅 **Added:** {selected_client.get('created_at').strftime('%Y-%m-%d') if selected_client.get('created_at') else 'N/A'}")

        with col_pref:
            st.markdown("### Client Preferences")
            if selected_client.get('preferences'):
                st.info(selected_client.get('preferences'))
            else:
                st.write("*No specific preferences recorded.*")

        st.markdown("### Realtor Notes")
        if selected_client.get('notes'):
            st.write(selected_client.get('notes'))
        else:
            st.write("*No notes available.*")


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.selected_client_id = None
    st.rerun()


def _get_clients_for_user(user_id: ObjectId):
    clients = get_clients_collection()
    return list(clients.find({"realtor_id": user_id}).sort("created_at", -1))


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
    st.subheader("Favorite Listings")

    analyses = list(
        get_analyses_collection()
        .find({"realtor_id": realtor_id, "client_id": client_id})
        .sort("created_at", -1)
    )

    if not analyses:
        st.info("No favorites yet. Analyze a property and click 'Add to Favorites'.")
        return

    for item in analyses:
        result = item.get("result", {})
        listing_data = item.get("listing", {})

        with st.container(border=True):
            col_info, col_del = st.columns([5, 1])

            with col_info:
                street = listing_data.get("street", "Unknown Address")
                city = listing_data.get("city", "")
                state = listing_data.get("state", "")
                st.markdown(f"**{street}, {city} {state}**")

                score = result.get("fit_score", "N/A")
                st.markdown(f"**Fit Score:** {score}/100")

            with col_del:
                if st.button("🗑️", key=f"del_{item['_id']}", use_container_width=True):
                    get_analyses_collection().delete_one({"_id": item["_id"]})
                    st.toast("Removed from favorites")
                    st.rerun()

            with st.expander("View Property Report"):
                st.markdown(result.get("report_markdown", "No report available."))


def dashboard_page():
    user_id = st.session_state.user["_id"]
    clients = _get_clients_for_user(user_id)

    if not clients:
        st.title("Realtor Dashboard")
        st.warning("No clients found. Go to 'Manage Clients' to register one.")
        return

    st.subheader("Selected Client")
    client_labels = [c["name"] for c in clients]
    current_idx = 0
    for i, c in enumerate(clients):
        if str(c["_id"]) == st.session_state.selected_client_id:
            current_idx = i
            break

    selected_name = st.selectbox(
        "Choose a client to analyze properties for:",
        options=client_labels,
        index=current_idx,
        label_visibility="collapsed"
    )

    active_client = next(c for c in clients if c["name"] == selected_name)
    st.session_state.selected_client_id = str(active_client["_id"])

    st.divider()
    st.markdown(f"### Financial Overview: {active_client['name']}")
    p = active_client.get("profile", {})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Annual Income", f"${p.get('income', 0):,.0f}")
    m2.metric("Monthly Debt", f"${p.get('monthly_debt', 0):,.0f}")
    m3.metric("Savings", f"${p.get('savings', 0):,.0f}")
    m4.metric("Credit Score", p.get('credit_score', 'N/A'))

    st.divider()
    st.subheader("Analyze New Listing")
    url = st.text_input("Paste listing URL (Zillow/Realtor)", key="listing_url",
                        placeholder="https://www.zillow.com/homedetails/...")

    if st.button("Run Property Analysis", type="primary"):
        if not url.strip():
            st.error("Please provide a listing URL.")
        else:
            with st.status("Analyzing...", expanded=True) as status:
                try:
                    listing = scrape_listing(url.strip())
                    comps = get_area_comps(listing.get("city"), listing.get("state"), max_results=5)
                    report = generate_listing_report(active_client, listing, comps)

                    st.session_state.temp_analysis = {
                        "url": url.strip(),
                        "listing": listing,
                        "result": report
                    }
                    status.update(label="Analysis Complete!", state="complete")
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")

    if "temp_analysis" in st.session_state:
        temp = st.session_state.temp_analysis
        st.divider()
        st.markdown("### New Analysis Preview")
        st.markdown(temp["result"]["report_markdown"])

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            if st.button("Add to Favorites", type="primary", use_container_width=True):
                _save_analysis(user_id, active_client["_id"], temp["url"], temp["listing"], temp["result"])
                del st.session_state.temp_analysis
                st.toast("Listing added to favorites!", icon="⭐")
                st.rerun()
        with btn_col2:
            if st.button("Discard Analysis", use_container_width=True):
                del st.session_state.temp_analysis
                st.rerun()

    st.divider()
    _render_analysis_history(user_id, active_client["_id"])


def _sidebar_nav():
    script_directory = Path(__file__).parent
    logo_path = script_directory / "Agents Squared Logo.png"

    st.markdown("""
        <style>
        [data-testid="stSidebar"] h1 { text-align: left; margin-top: -20px; }
        button:has(.logout-text) { background-color: #ff4b4b !important; color: white !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)

    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
    else:
        st.sidebar.markdown("# Agent$^2$")
    
    st.sidebar.markdown("---")
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    if st.sidebar.button("Dashboard", use_container_width=True, 
                         type="primary" if st.session_state.current_page == "Dashboard" else "secondary"):
        st.session_state.current_page = "Dashboard"
        st.rerun()

    if st.sidebar.button("Manage Clients", use_container_width=True, 
                         type="primary" if st.session_state.current_page == "Manage Clients" else "secondary"):
        st.session_state.current_page = "Manage Clients"
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        logout()


def main_app():
    _sidebar_nav()
    if st.session_state.current_page == "Dashboard":
        dashboard_page()
    elif st.session_state.current_page == "Manage Clients":
        clients_page()


if not st.session_state.authenticated:
    login_page()
else:
    main_app()