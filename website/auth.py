import bcrypt
from database import get_users_collection

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def verify_password(plain_password: str, hashed_password: str | bytes) -> bool:
    """
    Checks a plain-text password against a stored hash.
    Safely handles both string and bytes inputs from MongoDB.
    """
    # 1. Plain password from user input is always a string, so encode it
    password_bytes = plain_password.encode('utf-8')

    # 2. Hashed password from DB might be a string OR bytes
    if isinstance(hashed_password, str):
        hash_bytes = hashed_password.encode('utf-8')
    else:
        hash_bytes = hashed_password  # It's already bytes, don't re-encode!

    return bcrypt.checkpw(password_bytes, hash_bytes)

def create_user(email: str, password: str):
    users = get_users_collection()

    if users.find_one({"email": email}):
        return False, "User already exists."

    hashed_pw = hash_password(password)

    users.insert_one({
        "email": email,
        "password": hashed_pw,
        "financial_profile": {
            "income": 0,
            "monthly_debt": 0,
            "savings": 0,
            "credit_score": 700
        }
    })

    return True, "User created successfully."

def authenticate_user(email: str, password: str):
    users = get_users_collection()
    user = users.find_one({"email": email})

    if not user:
        return False, "User not found."

    if verify_password(password, user["password"]):
        return True, user

    return False, "Incorrect password."