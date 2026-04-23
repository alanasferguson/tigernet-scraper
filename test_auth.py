import requests
import os
from dotenv import load_dotenv

# load credentials from the .env file 
load_dotenv()

# build headers using session cookies and CSRF token 
# TigerNet uses a Hiverbite-based API for authenticated requests
headers = {
    "cookie": f"_hivebrite_session={os.getenv('HIVEBRITE_SESSION')}; remember_user_token={os.getenv('REMEMBER_USER_TOKEN')}",
    "x-csrf-token": os.getenv("CSRF_TOKEN"),
    "x-requested-with": "XMLHttpRequest",
    "accept": "application/json"
}

# directory listing endpoint 
# returns a paginated list of all members 
url = "https://tigernet.princeton.edu/frontoffice/api/users"
params = {
    "page": 1,
    "query[exclude_current_user]": "false",
    "sort_by": "last_seen_at",
    "order": "desc",
    "per_page": 5
}

response = requests.get(url, headers=headers, params=params)

print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Total users: {data['total_items']}")
    print(f"First user: {data['users'][0]['firstname']} {data['users'][0]['lastname']}")
else:
    print(f"Error: {response.text[:200]}")