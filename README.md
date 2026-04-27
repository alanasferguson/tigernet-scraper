# TigerNet Scraper

An automated scraper for the TigerNet Princeton alumni directory. Authenticates through Princeton's CAS and Duo 2FA via Playwright, traverses all 130,021 alumni profiles through the Hivebrite JSON API, and exports a clean structured CSV. Built as a technical assessment for Small World Capital.

---

## How It Works

TigerNet is Princeton University's alumni directory, built on the Hivebrite platform. The scraper works in two phases:

**Phase 1 — Authentication.** A Playwright-controlled Chromium browser navigates to TigerNet, fills in CAS credentials from environment variables, waits for Duo 2FA approval, handles the device trust screen, and extracts session cookies. A CSRF token is then fetched from the TigerNet people page. The browser closes and all subsequent requests use the Python requests library directly.

**Phase 2 — Data Collection.** The scraper paginates through the directory endpoint `/frontoffice/api/users` at 100 users per page across 1,301 pages. For each user it makes a second request to `/private/frontoffice/users/profiles/{id}` to fetch the full profile. Both responses are merged and flattened into a single CSV row. Progress is checkpointed after every page so the run can be resumed if interrupted.

TigerNet's API was discovered through Chrome DevTools network inspection. The platform is built on Hivebrite which exposes clean JSON endpoints rather than requiring HTML parsing, making the data collection layer straightforward once authentication was solved.

---

## Prerequisites

- Python 3.8 or higher
- A valid Princeton University TigerNet account
- Access to your Princeton Duo 2FA device for login approval during each run

**Important:** TigerNet is a private alumni network restricted to Princeton University affiliates. You must have a valid Princeton netid and an active TigerNet account to run this scraper. There is no way to access the data without institutional credentials.

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/alanasferguson/tigernet-scraper
cd tigernet-scraper
```

**2. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**3. Install the Playwright browser**

```bash
playwright install chromium
```

This downloads the Chromium browser that Playwright uses to automate the login flow. It only needs to be run once.

---

## Configuration

**1. Create your credentials file**

```bash
cp .env.example .env
```

**2. Open `.env` and fill in your Princeton credentials**
PRINCETON_NETID=your_netid_here
PRINCETON_PASSWORD=your_password_here

The `.env` file is listed in `.gitignore` and must never be committed to version control. It contains your Princeton password and should be treated as sensitive.

The `.env.example` file shows the required format without real values and is safe to commit.

---

## Usage

Run the scraper with a single command:

```bash
python main.py
```

**What happens when you run it:**

1. A Chromium browser window opens and navigates to TigerNet
2. Your credentials are filled in automatically and the CAS form is submitted
3. The terminal prints: `*** Please approve the Duo push notification on your phone ***`
4. Approve the Duo push on your phone
5. If a "Is this your device?" screen appears it is clicked automatically
6. The browser extracts session cookies and closes
7. The scraper begins processing users and prints progress to the terminal:

Fetching page 1/1301 — 100 users on this page — 130021 total users
Processed 2333592: Ashley Lefrak
Processed 7247835: Klea Tryfoni
...
Wrote 100 rows to CSV
Progress saved — completed page 1/1301


8. Results are written to `tigernet_export.csv` incrementally after each page

The only manual step is approving the Duo push notification on your phone. This cannot be automated without bypassing Princeton's 2FA security controls.

---

## Expected Output

The scraper writes to `tigernet_export.csv` in the project root directory. Each row represents one alumni profile. The file is created on the first page and appended to incrementally — it is valid and readable at any point during the run.

**Output columns:**

| Column | Description |
|--------|-------------|
| id | Numeric Hivebrite user ID |
| firstname | First name |
| lastname | Last name |
| headline | Professional headline |
| last_seen_at | Last active timestamp |
| city | Current city |
| state | State or province code |
| country | Country |
| full_address | Full formatted address |
| lat / lng | Latitude and longitude coordinates |
| full_name | Full formatted name with class year suffix |
| primary_affiliation | e.g. Undergraduate Alumni, Graduate Alumni |
| primary_class/degree_year | Princeton graduation year |
| affinity_groups | Princeton affinity group memberships |
| student_activities | Princeton student activities |
| regions | Princeton Alumni Association region |
| preferred_paa | Preferred alumni association chapter |
| degree_year | Degree year |
| degree_type | e.g. Bachelor of Arts |
| major | Academic major |
| current_employer | Current company name |
| current_position | Current job title |
| email | Primary email address |
| email2 | Alternate email 1 |
| email3 | Alternate email 2 |
| mobile_perso | Personal mobile number |
| linkedin_profile_url | LinkedIn profile URL |
| twitter | X/Twitter profile URL |
| facebook_profile_url | Facebook profile URL |
| website | Personal website URL |
| photo_url | Profile photo URL |

Multi-value fields such as `affinity_groups` and `student_activities` are pipe-separated within a single cell. For example: `Asian American Alumni Association of Princeton|Princeton Women's Network`

**Runtime estimate:** At 0.5 seconds per user profile plus network overhead, a complete run of all 130,021 users takes approximately 20 to 25 hours.

---

## Resuming After Interruption

The scraper saves a `progress.json` checkpoint file after every completed page. This stores the last completed page number and the full list of already-processed user IDs.

If the script is interrupted for any reason — crash, session expiry, manual stop — simply run `python main.py` again. It will re-authenticate automatically via Playwright and resume from the last saved page without reprocessing users already in the CSV.

To start a completely fresh run from the beginning:

```bash
rm progress.json tigernet_export.csv
python main.py
```

---

## Architecture
**`main.py`**
The entry point and orchestration layer. Calls `auth.py` to obtain fresh session cookies at startup, then enters the main pagination loop. For each page it calls `tigernet_client.py` to fetch directory listings and individual profiles, passes results to `csv_creation_tool.py` for flattening, writes batches to CSV, and saves progress. Handles the resume logic by loading and updating `progress.json` after every page.

**`auth.py`**
Handles the full authentication flow using Playwright. Launches a visible Chromium browser, navigates to TigerNet, dismisses the cookie consent popup, clicks Login to trigger the CAS redirect, fills in credentials from `.env`, submits the form, polls for Duo approval, handles the device trust screen automatically, and extracts session cookies once redirected to TigerNet. Also contains `get_csrf_token()` which fetches a fresh CSRF token from the TigerNet people page using multi-pattern regex extraction.

**`tigernet_client.py`**
All API communication with TigerNet. Contains two functions. `get_user_list(page, per_page)` calls the paginated directory endpoint `/frontoffice/api/users` and returns a list of basic user objects. `get_user_profile(user_id)` calls `/private/frontoffice/users/profiles/{id}` and returns full profile data. Both functions build fresh headers on each call, implement retry logic with up to 3 attempts, handle 429 rate limit responses with a 60 second cooldown, and detect 401 session expiry with a clear message to restart.

**`csv_creation_tool.py`**
Data transformation and output. The `flatten_user(basic, profile)` function takes the two JSON responses per user and merges them into a single flat dictionary suitable for CSV output. Handles nested location objects, dynamic custom attribute sections, pipe-separated multi-value fields, education and experience extraction, phone and social link fields, and missing data gracefully. Uses UTF-8-sig encoding for Google Sheets compatibility. The `write_rows(rows)` function appends batches to the output CSV in append mode so already-written data is never overwritten.

---

## Known Limitations

**Princeton account required**
TigerNet is a private institutional network. Access requires a valid Princeton netid and active TigerNet membership. This is by design — the directory contains personal contact information for 130,000 people and is appropriately restricted.

**Duo push approval required once per run**
The one unavoidable human step is approving the Duo push notification on your phone at the start of each run. Princeton's Duo implementation uses push notifications rather than TOTP codes, making it impossible to fully automate without compromising institutional security controls. The scraper automates every other step including the device trust screen.

**Session expiry on long runs**
The `_hivebrite_session` cookie can expire during very long runs. If you see repeated 401 errors in the terminal, stop the script and restart it — it will re-authenticate automatically via Playwright and resume from the last checkpoint.

**Rate limiting**
The scraper runs at 0.5 seconds per user profile and 1 second between pages. Reducing these delays risks triggering TigerNet's rate limiting. If you see 429 errors the scraper will wait 60 seconds automatically before retrying.

**Partial profiles**
Some alumni have private profiles or minimal data filled in. The scraper handles missing fields with empty cells rather than errors. A profile that returns limited data will appear as a row with many empty columns rather than being skipped.

**Full run time**
A complete scrape of all 130,021 profiles takes approximately 20 to 25 hours. The scraper is designed to run unattended overnight with progress checkpointing. For testing or partial datasets, interrupt with `Ctrl+C` at any point — the CSV written so far is valid and complete.
