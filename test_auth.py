import requests
import json

# Base URL for the API
BASE_URL = 'http://127.0.0.1:8000/api/'

def test_auth_flow():
    print("\n=== Testing Authentication Flow ===")
    
    # 1. Get token
    print("\n1. Getting token...")
    token_url = f"{BASE_URL}token/"
    credentials = {
        "username": "testuser",  # Replace with your admin username
        "password": "123"  # Replace with your admin password
    }
    
    response = requests.post(token_url, data=credentials)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access')
        refresh_token = token_data.get('refresh')
        print("✓ Token obtained successfully")
        print(f"User ID: {token_data.get('user_id')}")
        print(f"Username: {token_data.get('username')}")
        print(f"Is Staff: {token_data.get('is_staff')}")
    else:
        print(f"✗ Failed to get token: {response.status_code}")
        print(response.text)
        return
    
    # 2. Access protected endpoint
    print("\n2. Accessing protected endpoint (clients)...")
    clients_url = f"{BASE_URL}clients/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(clients_url, headers=headers)
    if response.status_code == 200:
        print("✓ Successfully accessed protected endpoint")
        clients_data = response.json()
        print(f"Total clients: {clients_data.get('count')}")
    else:
        print(f"✗ Failed to access protected endpoint: {response.status_code}")
        print(response.text)
    
    # 3. Test token refresh
    print("\n3. Testing token refresh...")
    refresh_url = f"{BASE_URL}token/refresh/"
    refresh_data = {"refresh": refresh_token}
    
    response = requests.post(refresh_url, data=refresh_data)
    if response.status_code == 200:
        new_access_token = response.json().get('access')
        print("✓ Successfully refreshed token")
    else:
        print(f"✗ Failed to refresh token: {response.status_code}")
        print(response.text)
        return
    
    # 4. Verify token
    print("\n4. Verifying token...")
    verify_url = f"{BASE_URL}token/verify/"
    verify_data = {"token": new_access_token}
    
    response = requests.post(verify_url, data=verify_data)
    if response.status_code == 200:
        print("✓ Token verified successfully")
    else:
        print(f"✗ Failed to verify token: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_auth_flow()