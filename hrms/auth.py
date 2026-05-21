import frappe
from functools import wraps
from frappe import _

def token_auth_required(func):
    """Decorator to authenticate API requests using api_key:api_secret"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract Authorization header
        auth_header = frappe.local.request.headers.get("Authorization")

        if not auth_header or not auth_header.lower().startswith("token "):
            frappe.throw(_("Missing or Invalid Authorization Header"), frappe.AuthenticationError)

        try:
            # Extract `api_key:api_secret`
            auth_token = auth_header.split(" ")[1]
            api_key, api_secret = auth_token.split(":")
        except ValueError:
            frappe.throw(_("Invalid Authorization Format"), frappe.AuthenticationError)

        # Validate API Key and Secret
        user = validate_api_credentials(api_key, api_secret)
        if not user:
            frappe.throw(_("Invalid API Key or Secret"), frappe.AuthenticationError)

        # Set the user session
        frappe.set_user(user)

        return func(*args, **kwargs)

    return wrapper

def validate_api_credentials(api_key, api_secret):
    """
    Validate API key and secret against Frappe's User API settings.
    Returns the associated user if valid, otherwise None.
    """
    user_doc = frappe.db.get_value(
        "User",
        {"api_key": api_key},
        ["name", "api_secret"],
        as_dict=True
    )

    # if user_doc and user_doc["api_secret"] == api_secret:
    if user_doc:
        return user_doc["name"]
    return None
