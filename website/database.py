import os

from pymongo import MongoClient
import streamlit as st


@st.cache_resource
def get_database():
    client = MongoClient(st.secrets["MONGO_URI"], tlsAllowInvalidCertificates=True)
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
