import os
import secrets

SECRET_KEY = secrets.token_hex(16)

# Generate secret key if it doesn't exist
def generate_secret_key():
    return secrets.token_hex(16)
