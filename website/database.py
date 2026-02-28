import os

from pymongo import MongoClient
import streamlit as st


def _read_secret(key: str) -> str | None:
    """Read a secret safely from Streamlit secrets, then env vars as fallback."""
    try:
        value = st.secrets.get(key)
    except Exception:
        value = None

    if value:
        return value

    return os.getenv(key)


@st.cache_resource
def get_database():
    mongo_uri = _read_secret("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError(
            "Missing MONGO_URI. Add it to .streamlit/secrets.toml "
            "or set the MONGO_URI environment variable."
        )

    client = MongoClient(mongo_uri, tlsAllowInvalidCertificates=True)
    return client["homesense"]


def get_users_collection():
    db = get_database()
    return db["users"]


def get_clients_collection():
    db = get_database()
    return db["clients"]


def get_analyses_collection():
    db = get_database()
    return db["analyses"]
