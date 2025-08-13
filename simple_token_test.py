import requests

# Base URL for the API
BASE_URL = 'http://127.0.0.1:8000/api/'

# Token endpoint
token_url = f"{BASE_URL}token/"

# Credentials
credentials = {
    "username": "testuser",
    "password": "123"
}

print(f"Attempting to get token from: {token_url}")
print(f"Using credentials: {credentials}")

# Make the request
response = requests.post(token_url, data=credentials)

# Print the results
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")