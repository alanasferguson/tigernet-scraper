import requests # makes HTTP requests to the API 
import time # used to track delays between requests 
import os # reads environment variables 
from dotenv import load_dotenv # loads .env file into the environment

load_dotenv()

# store domain as a global variable
BASE_URL = "https://tigernet.princeton.edu"

#
def get_headers():
   
   # Build and return the headers required for every TigerNet API request
   # Call each time so the .env values are picked up 
    return {

        # Session cookies to prove authenticated session
        # If cookie expires have token backup 
        "cookie": f"_hivebrite_session={os.getenv('HIVEBRITE_SESSION')}; remember_user_token={os.getenv('REMEMBER_USER_TOKEN')}",

        # Without token will hrow a 403 error
        "x-csrf-token": os.getenv("CSRF_TOKEN"),

        # AJAX request 
        "x-requested-with": "XMLHttpRequest",

        # JSON not HTML
        "accept": "application/json, text/plain, */*",
    }

# calls directory endpoint 
# gets one page of users 
# params: page (page you want), per_page (how many users per page), retries (how many times to retry on failure)
def get_user_list(page, per_page=100, retries=3):
    
    # Fetch a page of users fromt he irectory endpoint 
    # Takes a page so which page number to request
    # per_page: the number of users on a page
    # retries: How many times to retry on failure before giving up 
    # retries: how many times to retry on failure before giving up 

    # Used DevTools network inspection to find the directory listing endpoint 
    url = f"{BASE_URL}/frontoffice/api/users"
    # query parameters 
    params = {
        "page": page,
        "query[exclude_current_user]": "false", # make sure we as a user are included in results 
        "sort_by": "last_seen_at", # sort by most recently active 
        "order": "desc",
        "per_page": per_page
    }

    # retry loop 
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=get_headers(),
                params=params,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                print(f"Rate limited on page {page}, waiting 60s...")
                time.sleep(60)
            elif resp.status_code == 401:
                print("Session expired — update cookies in .env and restart")
                return None
            else:
                print(f"Error {resp.status_code} on page {page}, attempt {attempt + 1}/{retries}")
                time.sleep(5)
        except requests.exceptions.Timeout:
            print(f"Timeout on page {page}, attempt {attempt + 1}/{retries}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error on page {page}: {e}")
            time.sleep(5)

    print(f"Failed to fetch page {page} after {retries} attempts")
    return None

# individual user profile endpoints 
# params: a user_id 
# return: full profile JSON
def get_user_profile(user_id, retries=3):
    """
    Fetch full profile data for a single user by ID.
    Returns profile dict or None on failure.
    """
    url = f"{BASE_URL}/private/frontoffice/users/profiles/{user_id}"

    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=get_headers(),
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                print(f"Rate limited on user {user_id}, waiting 60s...")
                time.sleep(60)
            elif resp.status_code == 401:
                print("Session expired — update cookies in .env and restart")
                return None
            else:
                print(f"Error {resp.status_code} on user {user_id}, attempt {attempt + 1}/{retries}")
                time.sleep(3)
        except requests.exceptions.Timeout:
            print(f"Timeout on user {user_id}, attempt {attempt + 1}/{retries}")
            time.sleep(3)
        except Exception as e:
            print(f"Unexpected error on user {user_id}: {e}")
            time.sleep(3)

    print(f"Failed to fetch profile {user_id} after {retries} attempts")
    return None