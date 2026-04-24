import time      # used to add delays between requests so we don't get rate limited
import json      # used to save and load progress so we can resume if the script crashes
import os        # used to check if progress file exists

# Import our two custom modules
from tigernet_client import get_user_list, get_user_profile    # handles all API calls to TigerNet
from csv_creation_tool import flatten_user, write_rows          # handles turning API data into CSV rows
from auth import get_fresh_cookies, get_csrf_token

# How many users to fetch per page — 100 is the maximum TigerNet allows
PER_PAGE = 100

# How long to wait between fetching each user's full profile
# 0.5 seconds is fast enough to be practical but slow enough to avoid getting blocked
DELAY_BETWEEN_USERS = 0.5

# How long to wait between fetching each page of the directory
# Slightly longer than the per-user delay to be safe
DELAY_BETWEEN_PAGES = 1.0

# File where we save our progress so we can resume if the script crashes
# Stores the last completed page number and list of already-processed user IDs
PROGRESS_FILE = "progress.json"


def load_progress():
    # Check if a progress file exists from a previous run
    if os.path.exists(PROGRESS_FILE):
        # If it does, load it and return where we left off
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    
    # If no progress file exists this is a fresh run — start from the beginning
    return {
        "last_completed_page": 0,        # last page we fully finished
        "processed_ids": []              # list of user IDs we already have data for
    }


def save_progress(last_completed_page, processed_ids):
    # Save our current progress to the progress file after every page
    # This is what lets us resume from the right place if something goes wrong
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "last_completed_page": last_completed_page,
            "processed_ids": processed_ids
        }, f)


def main():
    # Try to get fresh cookies via Playwright login
    # This handles the full CAS + Duo authentication automatically
    print("Logging into TigerNet...")
    
    try:
        # Launch browser, fill credentials, wait for Duo approval
        cookies = get_fresh_cookies()
        
        # Use the fresh session cookie to get a valid CSRF token
        csrf_token = get_csrf_token(
            cookies["hivebrite_session"],
            cookies["remember_user_token"]
        )
        
        # Write the fresh cookies back to .env so tigernet_client.py can use them
        # This updates the values in memory for this run
        os.environ["HIVEBRITE_SESSION"] = cookies["hivebrite_session"]
        os.environ["REMEMBER_USER_TOKEN"] = cookies["remember_user_token"]
        os.environ["CSRF_TOKEN"] = csrf_token
        
        print(f"Authentication successful")
        
    except Exception as e:
        # If Playwright login fails fall back to cookies already in .env
        print(f"Playwright login failed: {e}")
        print("Falling back to cookies in .env file...")
        
        # Check that fallback cookies exist
        if not os.getenv("HIVEBRITE_SESSION"):
            print("No cookies found in .env either — cannot proceed")
            print("Add PRINCETON_NETID and PRINCETON_PASSWORD to .env and try again")
            return
            
    # Load any existing progress from a previous run
    progress = load_progress()

    # Figure out which page to start from
    start_page = progress["last_completed_page"] + 1

    # Convert processed IDs to a set for fast lookup
    processed_ids = set(progress["processed_ids"])

    # Keep track of what page we're on
    page = start_page

    print(f"Starting from page {page}")
    print(f"Already processed {len(processed_ids)} users from previous runs")
        
  
    
    # Keep looping until we've gone through all pages
    while True:
        print(f"\nFetching page {page}...")
        
        # Call the directory endpoint to get one page of users
        data = get_user_list(page, PER_PAGE)
        
        # If the API call failed entirely something is seriously wrong
        # Print a message and stop — don't keep trying endlessly
        if data is None:
            print(f"Failed to fetch page {page} — stopping. Check your cookies and try again.")
            break
        
        # Pull the list of users out of the response
        users = data.get("users", [])
        
        # If the users list is empty we've gone past the last page
        if not users:
            print("No more users found — scrape complete!")
            break
        
        # Calculate total pages so we can show progress
        total_items = data.get("total_items", 0)
        total_pages = (total_items + PER_PAGE - 1) // PER_PAGE
        
        print(f"Page {page}/{total_pages} — {len(users)} users on this page — {total_items} total users")
        
        # This list will hold all the flattened rows for this page
        # We batch them up and write them all at once at the end of each page
        batch = []
        
        # Loop through each user on this page
        for basic in users:
            user_id = basic["id"]
            
            # Skip this user if we already processed them in a previous run
            if user_id in processed_ids:
                print(f"  Skipping {user_id} — already processed")
                continue
            
            # Wait a moment before each profile request
            # This is the main rate limiting mechanism
            time.sleep(DELAY_BETWEEN_USERS)
            
            # Fetch the full detailed profile for this user
            # This gives us email, education, experience, contact info etc
            profile = get_user_profile(user_id)
            
            # Flatten the basic directory data and detailed profile into one row
            # If the profile fetch failed profile will be None
            # flatten_user handles this gracefully — just leaves those fields empty
            row = flatten_user(basic, profile)
            
            # Add this row to our batch
            batch.append(row)
            
            # Mark this user as processed so we don't fetch them again
            processed_ids.add(user_id)
            
            # Print progress for each user so we can see the script is working
            print(f"  Processed {user_id}: {basic.get('firstname')} {basic.get('lastname')}")
        
        # Write the entire batch for this page to the CSV file at once
        # More efficient than writing one row at a time
        if batch:
            write_rows(batch)
            print(f"Wrote {len(batch)} rows to CSV")
        
        # Save our progress after every completed page
        # This is the checkpoint — if the script crashes after this line
        # we can restart and skip everything up to this page
        save_progress(page, list(processed_ids))
        print(f"Progress saved — completed page {page}/{total_pages}")
        
        # Check if we've finished all pages
        if page >= total_pages:
            print("\nAll pages complete! Scrape finished.")
            break
        
        # Move to the next page
        page += 1
        
        # Wait a moment between pages
        time.sleep(DELAY_BETWEEN_PAGES)


# This is the standard Python entry point pattern
# It means this code only runs when you execute the file directly
# not when it gets imported by another file
if __name__ == "__main__":
    main()