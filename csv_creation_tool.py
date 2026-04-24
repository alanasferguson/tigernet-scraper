import csv  # Python's built-in CSV reading and writing library
import os   # used to check if the output file already exists

# Name of the output file that will be created in the project directory
OUTPUT_FILE = "tigernet_export.csv"


def flatten_user(basic, profile):
    # Takes two separate API responses for one user and merges them into
    # a single flat dictionary where every key becomes a CSV column name
    
    # Start with an empty dictionary that we'll populate field by field
    row = {}
    
    # Pull basic identity fields directly from the directory listing response
    row["id"] = basic.get("id")                     # numeric Hivebrite user ID
    row["firstname"] = basic.get("firstname")       # first name
    row["lastname"] = basic.get("lastname")         # last name
    row["headline"] = basic.get("headline")         # professional headline if set
    row["last_seen_at"] = basic.get("last_seen_at") # ISO timestamp of last login
    row["deceased"] = basic.get("deceased")         # boolean flag for deceased members
    
    # Location is a nested object inside the basic response
    # Using "or {}" as a fallback so .get() doesn't crash if location is null
    loc = basic.get("last_location") or {}
    row["city"] = loc.get("city")                                      # city name
    row["state"] = loc.get("administrative_area_level_1")              # state or province code
    row["country"] = loc.get("country")                                # country name
    row["full_address"] = loc.get("address")                           # full formatted address string
    row["lat"] = loc.get("lat")                                        # latitude coordinate
    row["lng"] = loc.get("lng")                                        # longitude coordinate
    
    # The directory listing includes a "fields" array of custom attributes
    # Each element looks like: {"display_name": "Full Name", "value": "Ms. Ashley Lefrak '01"}
    for field in basic.get("fields", []):
        # Convert the display name into a clean column name
        # Example: "Full Name" -> "full_name", "Affinity Groups" -> "affinity_groups"
        col_name = field.get("display_name", "").strip().replace(" ", "_").lower()
        
        val = field.get("value")
        
        # Some fields return a list because they allow multiple selections
        # Join list values with a pipe character so they fit in one CSV cell
        # Example: ["Asian American Alumni", "Princeton Women's Network"] -> "Asian American Alumni|Princeton Women's Network"
        if isinstance(val, list):
            val = "|".join(str(v) for v in val if v)
        
        # Store the value under the cleaned column name
        row[col_name] = val
    
    # Only process the detailed profile if we successfully fetched it
    # Profile can be None if the API call failed for this user
    if profile:
        
        # Contact email addresses — up to three per user
        row["email"] = profile.get("email")   # primary email
        row["email2"] = profile.get("email2") # alternate email 1
        row["email3"] = profile.get("email3") # alternate email 2
        
        # Direct URL to the user's profile photo
        row["photo_url"] = profile.get("photo_url")
        
        # The "center" key contains an array of profile sections
        # Each section has a name like "Princeton Information" or "Alumni Service"
        # and a "data" array of individual fields
        for section in profile.get("center", []):
            
            # Loop through every field in this section
            for field in section.get("data", []):
                name = field.get("display_name", "").strip()
                val = field.get("value")
                
                # Skip fields with no value to keep the CSV clean
                if val is None:
                    continue
                
                # Join multi-value fields with pipe separator
                if isinstance(val, list):
                    val = "|".join(str(v) for v in val if v)
                
                # Clean the column name and cap at 50 characters
                # to avoid excessively long headers
                col = name.replace(" ", "_").lower()[:50]
                
                # Only set this field if we haven't already captured it
                # from the basic directory data — prevents overwriting
                if col not in row:
                    row[col] = val
        
        # Extract phone numbers and social links from the contact section
        # The contact section has a different structure from the center section
        for section in profile.get("contact", []):
            for field in section.get("data", []):
                name = field.get("name", "")   # internal field name
                val = field.get("value")        # field value
                
                # Capture phone number fields by their internal names
                if val and name in ["mobile_perso", "landline_perso", "landline_pro"]:
                    row[name] = val
                
                # Capture social media and website links
                if name in ["linkedin_profile_url", "twitter", "facebook_profile_url", "website"]:
                    row[name] = val or ""  # use empty string instead of None for social links
        
        # Extract education data from the center sections
        for section in profile.get("center", []):
            
            # Find the section with type "educations"
            if section.get("type") == "educations":
                edu_list = section.get("data", [])
                
                if edu_list:
                    # Take the first education entry as the primary degree
                    edu = edu_list[0]
                    
                    # Initialize education fields as None
                    row["degree_year"] = None
                    row["degree_type"] = None
                    row["major"] = None
                    
                    # Education fields are stored as dynamic_attributes
                    # Loop through them and match by display name
                    for attr in edu.get("dynamic_attributes", []):
                        dname = attr.get("display_name", "")
                        
                        if dname == "Degree Year":
                            row["degree_year"] = attr.get("value")
                        
                        elif dname == "Degree":
                            val = attr.get("value")
                            # Degree is returned as a list, take the first element
                            row["degree_type"] = val[0] if isinstance(val, list) and val else val
                        
                        elif dname == "Major":
                            val = attr.get("value")
                            # Major is also returned as a list, take the first element
                            row["major"] = val[0] if isinstance(val, list) and val else val
        
        # Extract current employer from the experience section
        for section in profile.get("center", []):
            
            # Find the section with type "experiences"
            if section.get("type") == "experiences":
                exp_list = section.get("data", [])
                
                if exp_list:
                    # Take the most recent experience entry (first in the list)
                    exp = exp_list[0]
                    
                    # Company is a nested object with id, name, logo_url
                    company = exp.get("company", {})
                    row["current_employer"] = company.get("name") if company else None
                    
                    # Job title or position name
                    row["current_position"] = exp.get("position")
    
    # Return the completed flat dictionary representing one CSV row
    return row


def get_fieldnames():
    # Returns the ordered list of column headers for the CSV output
    # The order here controls the column order in the final file
    # Grouped logically: identity, location, princeton info, education, career, contact
    return [
        # Identity fields
        "id", "firstname", "lastname", "headline", "last_seen_at", "deceased",
        # Location fields
        "city", "state", "country", "full_address", "lat", "lng",
        # Princeton-specific custom attributes
        "full_name", "primary_affiliation", "primary_class/degree_year",
        "affinity_groups", "student_activities", "regions", "preferred_paa",
        # Education fields extracted from profile
        "degree_year", "degree_type", "major",
        # Current employment
        "current_employer", "current_position",
        # Contact information
        "email", "email2", "email3", "mobile_perso",
        "linkedin_profile_url", "twitter", "facebook_profile_url", "website",
        # Profile photo
        "photo_url"
    ]


def write_rows(rows):
    # Appends a batch of user rows to the CSV output file
    # Uses append mode so we never overwrite data already written
    # This is critical for resuming after a crash mid-run
    
    fieldnames = get_fieldnames()
    
    # Check if the file already exists before opening it
    # We need this to decide whether to write the header row
    file_exists = os.path.exists(OUTPUT_FILE)
    
    # Open in append mode ("a") — adds to end of file rather than overwriting
    # newline="" is required by Python's csv module on all platforms
    # utf-8-sig encoding adds a BOM marker that makes Google Sheets
    # correctly interpret special characters like accented names
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"  # silently drop any keys not in fieldnames list
        )
        
        # Only write the header row if this is a brand new file
        # If the file already exists we're resuming and headers are already there
        if not file_exists:
            writer.writeheader()
        
        # Write all rows in this batch to the file
        writer.writerows(rows)