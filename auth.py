import os
import time
import re
import requests
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def get_fresh_cookies():
    # Launches a real browser, logs into TigerNet automatically using
    # credentials from .env, waits for Duo approval, then extracts
    # and returns the session cookies for use in API requests
    
    netid = os.getenv("PRINCETON_NETID")
    password = os.getenv("PRINCETON_PASSWORD")
    
    # Make sure credentials are in .env before trying to login
    if not netid or not password:
        raise ValueError("PRINCETON_NETID and PRINCETON_PASSWORD must be set in .env")
    
    print("Starting browser login...")
    
    with sync_playwright() as p:
        # Launch a visible browser window so you can see what's happening
        # and approve the Duo push when it appears
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to TigerNet which will redirect to CAS login
        print("Navigating to TigerNet...")
        page.goto("https://tigernet.princeton.edu")
        
        # Handle the cookie consent popup if it appears
        # This popup blocks the login form from loading if not dismissed
        try:
            page.wait_for_selector("text=Accept all cookies", timeout=5000)
            page.click("text=Accept all cookies")
            print("Dismissed cookie consent popup")
        except:
            pass
        
        # Click the Login button on the TigerNet homepage
        try:
            page.wait_for_selector("text=Login", timeout=5000)
            page.click("text=Login")
            print("Clicked login button")
        except:
            pass
        
        # Wait for the CAS login form to appear after redirect
        print("Waiting for CAS login form...")
        page.wait_for_selector("#username", timeout=15000)
        
        # Fill in Princeton netid and password
        print(f"Filling in credentials for {netid}...")
        page.fill("#username", netid)
        page.fill("#password", password)
        
        # Try multiple possible selectors for the submit button
        print("Submitting login form...")
        try:
            page.click('button[name="_eventId_proceed"]', timeout=3000)
        except:
            try:
                page.click('button[type="submit"]', timeout=3000)
            except:
                try:
                    page.click('text=LOGIN', timeout=3000)
                except:
                    page.keyboard.press("Enter")
        
        print("Credentials submitted")
        print("\n*** Please approve the Duo push notification on your phone ***\n")
        
        # Poll the current URL every second waiting for TigerNet
        # Also automatically handles the "Is this your device?" screen
        # More reliable than wait_for_url because Duo's redirect path varies
        max_wait = 120
        for i in range(max_wait):
            time.sleep(1)
            current_url = page.url
            
            # Automatically click "Yes, this is my device" if it appears
            # This remembers the device so future logins skip this screen
            try:
                device_btn = page.query_selector("text=Yes, this is my device")
                if device_btn:
                    device_btn.click()
                    print("Clicked 'Yes, this is my device'")
                    time.sleep(2)
            except:
                pass
            
            # Check if we've successfully landed back on TigerNet
            if (
                "tigernet.princeton.edu" in current_url
                and "duosecurity" not in current_url
                and "fed.princeton" not in current_url
            ):
                print(f"Successfully logged into TigerNet after {i} seconds")
                break
            
            # Print a waiting message every 10 seconds
            if i % 10 == 0 and i > 0:
                print(f"Still waiting for Duo approval... ({i}s)")
        
        else:
            # Runs if loop completes without breaking
            # means we never landed on TigerNet
            raise Exception("Timed out waiting for Duo approval after 2 minutes")
        
        # Wait a moment for all cookies to be fully set after login
        time.sleep(2)
        
        # Extract all cookies from the browser session
        cookies = context.cookies()
        
        # Convert the list of cookie objects into a simple dictionary
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        
        # Close the browser — the scraper uses requests library from here on
        browser.close()
        
        print("Login successful — cookies extracted")
        
        # Return the two session cookies needed for API authentication
        return {
            "hivebrite_session": cookie_dict.get("_hivebrite_session", ""),
            "remember_user_token": cookie_dict.get("remember_user_token", ""),
        }


def get_csrf_token(hivebrite_session, remember_user_token):
    # Makes one request to the TigerNet people page to extract a fresh CSRF token
    # The CSRF token is embedded in the page HTML and changes each session
    # Without it every API request returns a 422 error
    
    headers = {
        "cookie": f"_hivebrite_session={hivebrite_session}; remember_user_token={remember_user_token}",
        "accept": "text/html"
    }
    
    # Fetch the people directory page which contains the CSRF token in its HTML
    print("Fetching CSRF token from TigerNet...")
    page_resp = requests.get(
        "https://tigernet.princeton.edu/people",
        headers=headers
    )
    
    # Try multiple regex patterns since Hivebrite uses different
    # attribute orderings across different page types
    patterns = [
        r'content="([^"]+)"\s+name="csrf-token"',
        r'name="csrf-token"\s+content="([^"]+)"',
        r'csrf-token["\s]+content="([^"]+)"',
        r'"csrf_token":"([^"]+)"',
        r'X-CSRF-Token["\s:]+([A-Za-z0-9+/=_\-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_resp.text)
        if match:
            csrf_token = match.group(1)
            print("CSRF token obtained successfully")
            return csrf_token
    
    # If none of the patterns matched print a snippet of the page
    # so we can see what format the token is actually in
    print("Could not find CSRF token — printing page snippet for debugging:")
    print(page_resp.text[:500])
    
    # Fall back to the value in .env
    print("Falling back to .env CSRF token")
    return os.getenv("CSRF_TOKEN", "")
