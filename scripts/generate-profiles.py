#!/usr/bin/env python3
"""
Generate and upload realistic customer profiles to Amazon Connect Customer Profiles.
Usage: PYTHONHOME= PYTHONPATH= /usr/bin/python3 scripts/generate-profiles.py [--count 2000] [--dry-run]
"""

import json
import random
import string
import sys
import time
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# REALISTIC US DATA
# ============================================================================

FIRST_NAMES_F = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Elizabeth", "Sofia", "Avery",
    "Ella", "Scarlett", "Grace", "Chloe", "Victoria", "Riley", "Aria", "Lily",
    "Aurora", "Zoey", "Nora", "Camila", "Hannah", "Lillian", "Addison",
    "Eleanor", "Natalie", "Luna", "Savannah", "Brooklyn", "Leah", "Zoe",
    "Stella", "Hazel", "Ellie", "Paisley", "Audrey", "Skylar", "Violet",
    "Claire", "Bella", "Lucy", "Anna", "Caroline", "Genesis", "Aaliyah",
    "Kennedy", "Kinsley", "Allison", "Maya", "Sarah", "Madelyn", "Adeline",
    "Alexa", "Ariana", "Elena", "Gabriella", "Naomi", "Alice", "Sadie",
    "Hailey", "Eva", "Emilia", "Autumn", "Quinn", "Nevaeh", "Piper",
    "Ruby", "Serenity", "Willow", "Everly", "Cora", "Kaylee", "Lydia",
    "Aubrey", "Arianna", "Eliana", "Peyton", "Melanie", "Gianna", "Isabelle",
    "Julia", "Valentina", "Nova", "Clara", "Vivian", "Reagan", "Mackenzie",
    "Madeline", "Brielle", "Delilah", "Isla", "Rylee", "Katherine", "Sophie",
    "Josephine", "Ivy", "Liliana", "Jade", "Maria", "Taylor", "Hadley",
    "Kylie", "Emery", "Adalynn", "Natalia", "Annabelle", "Faith", "Alexandra",
    "Ximena", "Ashley", "Brianna", "Raelynn", "Bailey", "Mary", "Ana",
    "Lila", "Athena", "Andrea", "Leilani", "Jasmine", "Lyla", "Margaret",
    "Alyssa", "Adalyn", "Arya", "Norah", "Khloe", "Kayla", "Eden"
]

FIRST_NAMES_M = [
    "Liam", "Noah", "Oliver", "James", "Elijah", "William", "Henry", "Lucas",
    "Benjamin", "Theodore", "Jack", "Levi", "Alexander", "Mason", "Ethan",
    "Daniel", "Jacob", "Michael", "Logan", "Jackson", "Sebastian", "Aiden",
    "Matthew", "Samuel", "David", "Joseph", "Carter", "Owen", "Wyatt",
    "John", "Luke", "Julian", "Dylan", "Grayson", "Jayden", "Gabriel",
    "Isaac", "Lincoln", "Anthony", "Hudson", "Thomas", "Charles", "Caleb",
    "Eli", "Aaron", "Ryan", "Nathan", "Adrian", "Christian", "Maverick",
    "Christopher", "Ezra", "Colton", "Connor", "Robert", "Josiah", "Jeremiah",
    "Cameron", "Landon", "Nolan", "Hunter", "Easton", "Jordan", "Nicholas",
    "Parker", "Brayden", "Ian", "Leo", "Austin", "Adam", "Brooks",
    "Jose", "Asher", "Jaxon", "Kevin", "Xavier", "Miles", "Dominic",
    "Greyson", "Everett", "Roman", "Weston", "Kai", "Sawyer", "Angel",
    "Cooper", "Axel", "Carson", "Emmett", "Declan", "Silas", "Ryder",
    "Diego", "Jason", "Damian", "Harrison", "Jace", "Riley", "Bentley",
    "Zachary", "Kayden", "Gavin", "Maxwell", "Eric", "Nathaniel", "Preston",
    "Tyler", "Marcus", "Patrick", "Grant", "Wesley", "Peter", "Colin",
    "Oscar", "Bennett", "Beckett", "Blake", "Tristan", "Tucker", "Shane",
    "Travis", "Spencer", "Timothy", "Craig", "Derek", "Sean", "Victor"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
    "Cooper", "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos",
    "Kim", "Cox", "Ward", "Richardson", "Watson", "Brooks", "Chavez",
    "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long",
    "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell",
    "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes", "Gonzales",
    "Fisher", "Vasquez", "Simmons", "Griffin", "Aguilar", "Wagner", "Hunt",
    "Chen", "Santos", "Park", "Yang", "Shah", "Chung", "Wu", "Tanaka",
    "Nakamura", "Sato", "Watanabe", "Singh", "Pham", "Tran", "Vo", "Le"
]

STREET_NAMES = [
    "Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine St", "Elm St",
    "Washington Ave", "Park Pl", "Lake Dr", "Hill Rd", "River Rd", "Forest Ave",
    "Sunset Blvd", "Highland Ave", "Meadow Ln", "Spring St", "Valley Dr",
    "Church St", "Franklin Ave", "Lincoln Way", "Jefferson St", "Adams Rd",
    "Broadway", "Market St", "Center St", "Union Ave", "Academy Dr",
    "Prospect Ave", "School St", "Court St", "Walnut St", "Chestnut Ave",
    "Laurel Dr", "Birch Ln", "Willow Way", "Dogwood Dr", "Magnolia Blvd",
    "Orchard Rd", "Cherry Ln", "Peach Tree Ln", "Sycamore St", "Poplar Ave",
    "Vine St", "Rose Ct", "Daisy Dr", "Iris Way", "Colonial Dr", "Heritage Ln",
    "Liberty Ave", "Independence Blvd", "Constitution Dr", "Eagle Rd",
    "Falcon Way", "Hawk Dr", "Osprey Ln", "Summit Ave", "Ridge Rd",
    "Canyon Dr", "Vista Way", "Harbor Blvd", "Bayview Dr", "Coastal Hwy"
]

# City, State, ZIP prefix (realistic combinations)
CITIES = [
    ("New York", "NY", "100"), ("Los Angeles", "CA", "900"), ("Chicago", "IL", "606"),
    ("Houston", "TX", "770"), ("Phoenix", "AZ", "850"), ("Philadelphia", "PA", "191"),
    ("San Antonio", "TX", "782"), ("San Diego", "CA", "921"), ("Dallas", "TX", "752"),
    ("San Jose", "CA", "951"), ("Austin", "TX", "787"), ("Jacksonville", "FL", "322"),
    ("Fort Worth", "TX", "761"), ("Columbus", "OH", "432"), ("Charlotte", "NC", "282"),
    ("San Francisco", "CA", "941"), ("Indianapolis", "IN", "462"), ("Seattle", "WA", "981"),
    ("Denver", "CO", "802"), ("Nashville", "TN", "372"), ("Oklahoma City", "OK", "731"),
    ("Portland", "OR", "972"), ("Las Vegas", "NV", "891"), ("Memphis", "TN", "381"),
    ("Louisville", "KY", "402"), ("Baltimore", "MD", "212"), ("Milwaukee", "WI", "532"),
    ("Albuquerque", "NM", "871"), ("Tucson", "AZ", "857"), ("Fresno", "CA", "937"),
    ("Sacramento", "CA", "958"), ("Mesa", "AZ", "852"), ("Atlanta", "GA", "303"),
    ("Kansas City", "MO", "641"), ("Omaha", "NE", "681"), ("Raleigh", "NC", "276"),
    ("Miami", "FL", "331"), ("Cleveland", "OH", "441"), ("Tampa", "FL", "336"),
    ("Arlington", "TX", "760"), ("Minneapolis", "MN", "554"), ("Pittsburgh", "PA", "152"),
    ("Cincinnati", "OH", "452"), ("St. Louis", "MO", "631"), ("Orlando", "FL", "328"),
    ("Boise", "ID", "837"), ("Richmond", "VA", "232"), ("Spokane", "WA", "992"),
    ("Charleston", "SC", "294"), ("Savannah", "GA", "314"), ("Boulder", "CO", "803"),
    ("Scottsdale", "AZ", "852"), ("Honolulu", "HI", "968"), ("Anchorage", "AK", "995"),
    ("Madison", "WI", "537"), ("Ann Arbor", "MI", "481"), ("Asheville", "NC", "288"),
    ("Burlington", "VT", "054"), ("Santa Fe", "NM", "875"), ("Bend", "OR", "977")
]

LOYALTY_TIERS = ["SkyBasic", "SkySilver", "SkyGold", "SkyPlatinum", "SkyDiamond"]
LOYALTY_WEIGHTS = [40, 25, 20, 10, 5]  # Distribution

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "aol.com", "protonmail.com", "mail.com", "zoho.com", "fastmail.com",
    "comcast.net", "verizon.net", "att.net", "cox.net", "charter.net"
]

# ============================================================================
# PROFILE GENERATOR
# ============================================================================

used_emails = set()

def generate_profile(index):
    """Generate a single realistic customer profile."""
    is_male = random.random() < 0.5
    first = random.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)

    # Email - ensure unique
    base_email = f"{first.lower()}.{last.lower()}"
    domain = random.choice(EMAIL_DOMAINS)
    email = f"{base_email}@{domain}"
    suffix = 1
    while email in used_emails:
        email = f"{base_email}{suffix}@{domain}"
        suffix += 1
    used_emails.add(email)

    # Address
    num = random.randint(1, 9999)
    street = random.choice(STREET_NAMES)
    apt = f", Apt {random.randint(1, 999)}" if random.random() < 0.3 else ""
    city, state, zip_prefix = random.choice(CITIES)
    zip_code = f"{zip_prefix}{random.randint(10, 99)}"

    # Phone
    area_code = random.randint(201, 989)
    phone = f"+1{area_code}{random.randint(2000000, 9999999)}"

    # Loyalty
    tier = random.choices(LOYALTY_TIERS, weights=LOYALTY_WEIGHTS, k=1)[0]
    miles_ranges = {
        "SkyBasic": (0, 15000), "SkySilver": (15000, 50000),
        "SkyGold": (50000, 150000), "SkyPlatinum": (150000, 300000),
        "SkyDiamond": (300000, 1000000)
    }
    lo, hi = miles_ranges[tier]
    miles = str(random.randint(lo, hi))

    return {
        "FirstName": first,
        "LastName": last,
        "EmailAddress": email,
        "PhoneNumber": phone,
        "Gender": "MALE" if is_male else "FEMALE",
        "Address": {
            "Address1": f"{num} {street}{apt}",
            "City": city,
            "State": state,
            "PostalCode": zip_code,
            "Country": "US"
        },
        "Attributes": {
            "LoyaltyTier": tier,
            "SkyMiles": miles,
            "MemberId": f"SC-{random.randint(20150101, 20260301)}-{random.randint(1, 9999):04d}"
        }
    }


def upload_profile(profile, domain_name, region):
    """Upload a single profile via boto3."""
    import boto3
    client = boto3.client('customer-profiles', region_name=region)
    try:
        result = client.create_profile(
            DomainName=domain_name,
            FirstName=profile["FirstName"],
            LastName=profile["LastName"],
            EmailAddress=profile["EmailAddress"],
            PhoneNumber=profile["PhoneNumber"],
            Gender=profile["Gender"],
            Address=profile["Address"],
            Attributes=profile["Attributes"]
        )
        return result["ProfileId"], None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Generate Connect Customer Profiles")
    parser.add_argument("--count", type=int, default=2000, help="Number of profiles (default: 2000)")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't upload")
    parser.add_argument("--domain", default="loguclyd-demo", help="Customer Profiles domain name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--threads", type=int, default=10, help="Parallel upload threads")
    parser.add_argument("--output", type=str, help="Save generated profiles to JSON file")
    args = parser.parse_args()

    print(f"🎲 Generating {args.count} customer profiles...")
    profiles = [generate_profile(i) for i in range(args.count)]
    print(f"   ✅ Generated {len(profiles)} profiles ({len(used_emails)} unique emails)")

    # Stats
    tier_counts = {}
    for p in profiles:
        t = p["Attributes"]["LoyaltyTier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"   📊 Tier distribution: {json.dumps(tier_counts, indent=6)}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(profiles, f, indent=2)
        print(f"   💾 Saved to {args.output}")

    if args.dry_run:
        print("\n🏁 Dry run complete. No profiles uploaded.")
        # Print a sample
        print("\n📋 Sample profile:")
        print(json.dumps(profiles[0], indent=2))
        return

    # Upload
    print(f"\n📤 Uploading {len(profiles)} profiles to '{args.domain}' ({args.threads} threads)...")
    
    import boto3
    success = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(upload_profile, p, args.domain, args.region): i
            for i, p in enumerate(profiles)
        }
        for future in as_completed(futures):
            idx = futures[future]
            profile_id, error = future.result()
            if profile_id:
                success += 1
            else:
                failed += 1
                if failed <= 5:
                    print(f"   ❌ Failed [{idx}] {profiles[idx]['FirstName']} {profiles[idx]['LastName']}: {error}")

            total = success + failed
            if total % 100 == 0:
                elapsed = time.time() - start_time
                rate = total / elapsed if elapsed > 0 else 0
                print(f"   Progress: {total}/{len(profiles)} ({rate:.0f}/sec) — ✅ {success} ❌ {failed}")

    elapsed = time.time() - start_time
    print(f"\n============================================")
    print(f"🎉 Upload Complete!")
    print(f"   ✅ Success: {success}")
    print(f"   ❌ Failed:  {failed}")
    print(f"   ⏱️  Time:    {elapsed:.1f}s ({len(profiles)/elapsed:.0f} profiles/sec)")
    print(f"============================================")


if __name__ == "__main__":
    # Force unbuffered output
    import functools
    print = functools.partial(print, flush=True)
    main()
