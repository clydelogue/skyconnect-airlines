#!/usr/bin/env python3
"""
Generate 200 fake cases across ~150 customer profiles for SkyConnect Airlines.
Creates fresh profiles (since existing bulk profiles have search indexing issues),
then creates cases linked to them.

Rate limits: CreateProfile=100 TPS, CreateCase=2 TPS/10 burst, UpdateCase=2 TPS/2 burst
We throttle CreateCase to ~1.4 TPS to stay safe.

Usage: unset PYTHONHOME PYTHONPATH && /usr/bin/python3 -u scripts/generate-cases.py
"""

import boto3
import json
import random
import time
import sys

# ============================================================================
# CONFIG
# ============================================================================
DOMAIN_ID = "e71fc22e-8b4d-47c9-84d7-e7de24cf8ecb"
TEMPLATE_ID = "40d32841-c13c-44e4-809a-dfdbed1cc83d"  # SkyConnect Case
PROFILES_DOMAIN = "amazon-connect-loguclyd-demo"
REGION = "us-east-1"
TOTAL_CASES = 200
MAX_CASES_PER_CUSTOMER = 2
DELAY_BETWEEN_CASES = 0.7  # ~1.4 TPS
PROFILE_ARN_PREFIX = f"arn:aws:profile:{REGION}:560576351083:domains/{PROFILES_DOMAIN}/profiles/"

cases_client = boto3.client('connectcases', region_name=REGION)
profiles_client = boto3.client('customer-profiles', region_name=REGION)

# ============================================================================
# FIELD IDs
# ============================================================================
F = {
    "title": "title", "summary": "summary", "case_reason": "case_reason",
    "customer_id": "customer_id", "status": "status",
    "Priority": "8b1cf243-4427-4647-8648-c2d26889f915",
    "FlightNumber": "0901cf55-8ca4-4967-b578-6cb6d88fe101",
    "BagDescription": "85d47d9a-7e94-4f1a-a21a-3a0c96c3360d",
    "BagTagNumber": "fec43030-f5cc-48b6-98c1-c92bf0a9e819",
    "BagColor": "80c76191-991a-4df2-bf30-6b3c468f63ad",
    "BagType": "a090c324-c6f4-49d3-84c9-23dc3cd18627",
    "ContentsDescription": "d4ee3c8e-e3fa-4a24-81e2-76c73d71811a",
    "ContainsMedication": "11bed2bd-982a-48a8-9883-66b3c09f41f6",
    "EstimatedValue": "bfd932c8-0471-4cc0-bb92-9b454e8820fa",
    "DeliveryAddress": "2ee2a912-9a61-460f-9ff2-5c0eaf38cbdf",
    "BagPriority": "db63a574-6a20-4eb3-b4ff-8d1809fa3c82",
    "DamageDescription": "741b3f0a-c644-46a3-b69f-1ad071d57efb",
    "ClaimAmount": "9e8ef641-3a90-47bd-9b64-2f3b073ff722",
    "DamageLocation": "c6fbc999-6073-4d05-b1c2-61d5b8bc8b17",
    "ItemValue": "32c7e66c-f40c-428b-8c43-7fa0ccf2b317",
    "PurchaseDate": "8ba73133-8aa6-4da3-8e34-cb0ed956137c",
    "ContactInfo": "8efaa698-6864-4ab3-ab4d-70bfa46de77e",
}


def fv(field_name, value):
    """Create field value for CreateCase API."""
    fid = F[field_name]
    if isinstance(value, bool):
        return {"id": fid, "value": {"booleanValue": value}}
    return {"id": fid, "value": {"stringValue": str(value)}}


# ============================================================================
# NAME / DATA POOLS
# ============================================================================
FIRST_NAMES = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Elizabeth", "Sofia", "Avery",
    "Ella", "Grace", "Chloe", "Victoria", "Riley", "Lily", "Aurora", "Zoey",
    "Nora", "Hannah", "Stella", "Hazel", "Audrey", "Claire", "Lucy",
    "Liam", "Noah", "Oliver", "James", "Elijah", "William", "Henry", "Lucas",
    "Benjamin", "Theodore", "Jack", "Alexander", "Mason", "Ethan", "Daniel",
    "Jacob", "Michael", "Logan", "Jackson", "Sebastian", "Aiden", "Matthew",
    "Samuel", "David", "Joseph", "Carter", "Owen", "Wyatt", "John", "Luke",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Kim", "Chen", "Patel", "Shah", "Singh",
]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"]
CITIES = [
    ("Seattle", "WA", "981"), ("Los Angeles", "CA", "900"), ("New York", "NY", "100"),
    ("Denver", "CO", "802"), ("Chicago", "IL", "606"), ("Miami", "FL", "331"),
    ("Phoenix", "AZ", "850"), ("Atlanta", "GA", "303"), ("Dallas", "TX", "752"),
    ("Boston", "MA", "021"), ("Portland", "OR", "972"), ("San Francisco", "CA", "941"),
]
TIERS = ["SkyBasic", "SkySilver", "SkyGold", "SkyPlatinum", "SkyDiamond"]
TIER_W = [40, 30, 20, 7, 3]
TIER_MILES = {"SkyBasic": (0, 15000), "SkySilver": (15000, 50000),
              "SkyGold": (50000, 150000), "SkyPlatinum": (150000, 300000),
              "SkyDiamond": (300000, 1000000)}

ROUTES = [
    ("SC101", "SEA", "LAX"), ("SC102", "LAX", "SEA"), ("SC205", "SFO", "JFK"),
    ("SC206", "JFK", "SFO"), ("SC310", "SEA", "DEN"), ("SC311", "DEN", "SEA"),
    ("SC415", "LAX", "ORD"), ("SC416", "ORD", "LAX"), ("SC520", "SEA", "MIA"),
    ("SC521", "MIA", "SEA"), ("SC630", "SFO", "ATL"), ("SC631", "ATL", "SFO"),
    ("SC740", "JFK", "LAX"), ("SC741", "LAX", "JFK"), ("SC850", "DEN", "MIA"),
    ("SC851", "MIA", "DEN"), ("SC960", "ORD", "SFO"), ("SC961", "SFO", "ORD"),
    ("SC110", "SEA", "PHX"), ("SC111", "PHX", "SEA"), ("SC225", "LAX", "DFW"),
    ("SC226", "DFW", "LAX"), ("SC330", "JFK", "BOS"), ("SC331", "BOS", "JFK"),
]

BAG_DESCS = [
    "Large black hard-shell Samsonite suitcase with red ribbon on handle",
    "Medium navy blue soft-side Travelpro with TSA lock",
    "Small gray rolling carry-on with laptop compartment",
    "Large red hard-shell suitcase, 4 spinner wheels",
    "Brown leather duffel bag with shoulder strap",
    "Green hiking backpack, Osprey brand, 65L",
    "Black garment bag with suit inside",
    "Medium purple Rimowa polycarbonate suitcase",
    "Navy Tumi carry-on with business documents",
    "Large black suitcase with yellow luggage tag",
    "Medium silver hard-shell with stickers on outside",
    "Blue soft-side with front zippered pocket",
    "Pink floral pattern rolling suitcase, medium size",
    "Black North Face duffel with climbing gear",
    "Tan canvas and leather weekender bag",
]

CONTENTS = [
    "Business attire, toiletries, laptop charger, documents",
    "Vacation clothes, camera equipment, sunscreen",
    "Winter clothing, ski goggles, warm boots",
    "Wedding attire, gifts, formal shoes",
    "Work uniforms, personal items, books",
    "Children's clothing, toys, baby supplies",
    "Conference materials, business suits, presentation equipment",
    "Hiking gear, outdoor clothing, camping supplies",
    "Personal belongings, medication, reading materials",
    "Sports equipment, athletic wear, competition uniform",
]

ADDRESSES = [
    "742 Evergreen Terrace, Seattle, WA 98101",
    "221B Baker Street, San Francisco, CA 94102",
    "1600 Pennsylvania Ave, New York, NY 10001",
    "350 Fifth Avenue, Denver, CO 80202",
    "1 Infinite Loop, Los Angeles, CA 90001",
    "123 Main St, Chicago, IL 60601",
    "456 Oak Ave, Miami, FL 33101",
    "789 Pine Rd, Phoenix, AZ 85001",
    "1010 Maple Dr, Atlanta, GA 30301",
    "555 Cedar Ln, Dallas, TX 75201",
]

DAMAGE_DESCS = [
    "Large crack across the front shell of suitcase, contents exposed",
    "Handle completely broken off, unable to roll",
    "Zipper torn open along the side, contents spilling",
    "Deep scratch marks and dent on the corner",
    "Wheel snapped off, cannot roll the bag",
    "Water damage to contents, bag was left in rain on tarmac",
    "Strap torn, shoulder bag no longer functional",
    "TSA lock jammed after inspection, cannot open bag",
    "Telescoping handle stuck, won't extend or retract",
    "Large tear in fabric along the seam",
]

DELAY_SUMMARIES = [
    "Flight delayed 4+ hours due to weather, missed connecting flight",
    "Mechanical delay caused overnight stay, requesting hotel reimbursement",
    "Flight cancelled, rebooked on next day flight, need meal voucher",
    "3-hour tarmac delay, requesting compensation per DOT guidelines",
    "Repeated delays over 6 hours, missed important business meeting",
    "Delay caused missed cruise ship departure, significant financial loss",
    "Flight diverted to alternate airport, need ground transportation help",
    "Overnight delay, elderly passenger needs special accommodation",
    "Delay with no communication from crew, requesting formal explanation",
    "Mechanical issue discovered at gate, 5-hour delay, missed event",
]

BOOKING_SUMMARIES = [
    "Need to change outbound flight date due to family emergency",
    "Requesting seat upgrade from economy to business class",
    "Need to add infant passenger to existing booking",
    "Flight time changed by airline, new time doesn't work",
    "Need to change return flight to earlier date",
    "Requesting name correction on ticket (typo at booking)",
    "Need to add extra checked bag to international flight",
    "Requesting change from connecting to direct flight",
    "Want to add travel insurance to existing booking",
    "Need wheelchair assistance added to booking",
]

REFUND_SUMMARIES = [
    "Cancelled trip due to illness, requesting full refund with doctor's note",
    "Duplicate charge on credit card for same booking",
    "Ancillary fee charged but service not provided (WiFi)",
    "Overcharged for baggage fees, receipt shows different amount",
    "Trip cancelled by airline, refund not yet processed after 14 days",
    "Travel insurance claim for cancelled flight",
    "Requesting refund for unused portion of round-trip ticket",
    "Charged for seat selection but assigned different seat",
    "Requesting refund for lounge access that was closed",
    "Double-booked by system error, need refund for duplicate",
]

GENERAL_SUMMARIES = [
    "Question about SkyConnect frequent flyer program enrollment",
    "Inquiry about pet travel policy for domestic flights",
    "Requesting information about unaccompanied minor service",
    "Question about carry-on size restrictions for new aircraft",
    "Asking about military discount eligibility",
    "Inquiry about group booking for wedding party (20+ guests)",
    "Question about international travel document requirements",
    "Asking about SkyConnect lounge access with basic economy ticket",
    "Inquiry about lost and found at SEA terminal",
    "Question about WiFi availability on regional flights",
]


# ============================================================================
# CASE GENERATORS
# ============================================================================
def gen_lost_baggage(pid):
    r = random.choice(ROUTES)
    flight, orig, dest = r
    desc = random.choice(BAG_DESCS)
    has_meds = random.random() < 0.15
    prio = "priority_medical" if has_meds else random.choice(["standard"] * 3 + ["priority_business", "priority_vip"])
    return [
        fv("title", f"Lost Bag - {flight} ({orig}\u2192{dest})"),
        fv("summary", f"Passenger reports lost baggage on flight {flight} from {orig} to {dest}. {desc}. Last seen at {orig} check-in."),
        fv("case_reason", "lost_baggage"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", "high" if has_meds else random.choice(["medium", "high", "medium", "low"])),
        fv("FlightNumber", flight),
        fv("BagDescription", desc),
        fv("BagTagNumber", f"SC{random.randint(1000000000, 9999999999)}"),
        fv("BagColor", random.choice(["black", "navy", "red", "gray", "green", "brown", "other"])),
        fv("BagType", random.choice(["hardshell", "softside", "duffel", "garment", "backpack", "other"])),
        fv("ContentsDescription", random.choice(CONTENTS)),
        fv("ContainsMedication", has_meds),
        fv("EstimatedValue", random.choice(["under_500", "500_1000", "1000_2500", "over_2500"])),
        fv("DeliveryAddress", random.choice(ADDRESSES)),
        fv("BagPriority", prio),
    ]

def gen_damaged_item(pid):
    r = random.choice(ROUTES)
    damage = random.choice(DAMAGE_DESCS)
    return [
        fv("title", f"Damaged Baggage - {r[0]}"),
        fv("summary", f"Passenger reports damage to luggage on flight {r[0]}. {damage}"),
        fv("case_reason", "damaged_item"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", random.choice(["medium", "high", "medium", "low"])),
        fv("DamageDescription", damage),
        fv("DamageLocation", random.choice(["baggage_claim", "during_flight", "at_gate", "destination", "other"])),
        fv("ClaimAmount", f"${random.choice([150, 200, 300, 450, 500, 750, 1000, 1500])}"),
        fv("ItemValue", f"${random.choice([200, 350, 500, 750, 1000, 1500, 2000])}"),
        fv("PurchaseDate", f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}"),
    ]

def gen_flight_delay(pid):
    r = random.choice(ROUTES)
    return [
        fv("title", f"Flight Delay Complaint - {r[0]}"),
        fv("summary", f"Re: Flight {r[0]} ({r[1]}\u2192{r[2]}). {random.choice(DELAY_SUMMARIES)}"),
        fv("case_reason", "flight_delay"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", random.choice(["medium", "high", "low", "medium"])),
        fv("FlightNumber", r[0]),
    ]

def gen_booking_change(pid):
    r = random.choice(ROUTES)
    return [
        fv("title", f"Booking Change - {r[0]}"),
        fv("summary", f"Re: Flight {r[0]} ({r[1]}\u2192{r[2]}). {random.choice(BOOKING_SUMMARIES)}"),
        fv("case_reason", "booking_change"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", random.choice(["low", "medium", "low", "medium"])),
        fv("FlightNumber", r[0]),
    ]

def gen_refund(pid):
    return [
        fv("title", "Refund Request"),
        fv("summary", random.choice(REFUND_SUMMARIES)),
        fv("case_reason", "refund_request"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", random.choice(["medium", "high", "medium", "low"])),
    ]

def gen_general(pid):
    return [
        fv("title", "General Inquiry"),
        fv("summary", random.choice(GENERAL_SUMMARIES)),
        fv("case_reason", "general_inquiry"),
        fv("customer_id", PROFILE_ARN_PREFIX + pid),
        fv("Priority", "low"),
    ]

GENERATORS = {
    "lost_baggage": gen_lost_baggage,
    "damaged_item": gen_damaged_item,
    "flight_delay": gen_flight_delay,
    "booking_change": gen_booking_change,
    "refund_request": gen_refund,
    "general_inquiry": gen_general,
}


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 60, flush=True)
    print("SkyConnect Airlines - Generate 200 Cases", flush=True)
    print("=" * 60, flush=True)

    # ---- Step 1: Create 149 fresh profiles + Sarah Chen ----
    print("\n[1/3] Creating 149 customer profiles...", flush=True)
    profiles = [{"profileId": "fcc4384327bf43caa1e76176b39afa7f", "name": "Sarah Chen"}]
    used_emails = set()
    errors = 0

    for i in range(149):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        domain = random.choice(EMAIL_DOMAINS)
        email = f"{first.lower()}.{last.lower()}@{domain}"
        sfx = 1
        while email in used_emails:
            email = f"{first.lower()}.{last.lower()}{sfx}@{domain}"
            sfx += 1
        used_emails.add(email)

        city, state, zp = random.choice(CITIES)
        tier = random.choices(TIERS, weights=TIER_W, k=1)[0]
        lo, hi = TIER_MILES[tier]

        try:
            resp = profiles_client.create_profile(
                DomainName=PROFILES_DOMAIN,
                FirstName=first, LastName=last,
                EmailAddress=email,
                PhoneNumber=f"+1{random.randint(201,989)}{random.randint(2000000,9999999)}",
                Gender="MALE" if first in FIRST_NAMES[30:] else "FEMALE",
                Address={"Address1": f"{random.randint(1,9999)} Main St",
                         "City": city, "State": state,
                         "PostalCode": f"{zp}{random.randint(10,99)}", "Country": "US"},
                Attributes={"LoyaltyTier": tier, "SkyMiles": str(random.randint(lo, hi)),
                             "MemberId": f"SC-{random.randint(20150101,20260301)}-{random.randint(1,9999):04d}"}
            )
            profiles.append({"profileId": resp["ProfileId"], "name": f"{first} {last}"})
        except Exception as e:
            errors += 1
            print(f"   \u26a0\ufe0f  Profile #{i+1} ({first} {last}): {e}", flush=True)

        if (i + 1) % 50 == 0:
            print(f"   Created {len(profiles)-1}/149 profiles ({errors} errors)...", flush=True)

    print(f"   \u2705 {len(profiles)} profiles ready ({errors} errors)", flush=True)

    if len(profiles) < 50:
        print("   ERROR: Too few profiles. Aborting.", flush=True)
        sys.exit(1)

    # ---- Step 2: Plan case distribution ----
    print("\n[2/3] Planning case distribution...", flush=True)

    # ~40% lost baggage, 15% damaged, 15% delay, 15% booking, 10% refund, 5% general
    case_types = (["lost_baggage"] * 80 + ["damaged_item"] * 30 + ["flight_delay"] * 30 +
                  ["booking_change"] * 30 + ["refund_request"] * 20 + ["general_inquiry"] * 10)
    random.shuffle(case_types)

    # Assign profiles: most get 1 case, ~50 get 2
    random.shuffle(profiles)
    assignments = []
    profile_counts = {}
    pidx = 0

    for ctype in case_types:
        while profile_counts.get(pidx, 0) >= MAX_CASES_PER_CUSTOMER:
            pidx += 1
            if pidx >= len(profiles):
                pidx = 0  # wrap around
        assignments.append((profiles[pidx], ctype))
        profile_counts[pidx] = profile_counts.get(pidx, 0) + 1
        if random.random() < 0.7:
            pidx += 1
            if pidx >= len(profiles):
                pidx = 0

    unique = len(set(a[0]["profileId"] for a in assignments))
    type_counts = {}
    for _, ct in assignments:
        type_counts[ct] = type_counts.get(ct, 0) + 1

    print(f"   {len(assignments)} cases \u2192 {unique} unique customers", flush=True)
    for ct, count in sorted(type_counts.items()):
        print(f"      {ct}: {count}", flush=True)

    # ---- Step 3: Create cases ----
    est_min = len(assignments) * DELAY_BETWEEN_CASES / 60
    print(f"\n[3/3] Creating {len(assignments)} cases (~{est_min:.1f} min at 1.4 TPS)...", flush=True)

    # Mix of open (60%) and closed (40%)
    statuses = ["open"] * 120 + ["closed"] * 80
    random.shuffle(statuses)

    created = 0
    case_errors = 0

    for i, (profile, ctype) in enumerate(assignments):
        try:
            fields = GENERATORS[ctype](profile["profileId"])
            resp = cases_client.create_case(
                domainId=DOMAIN_ID,
                templateId=TEMPLATE_ID,
                fields=fields,
            )
            case_id = resp["caseId"]
            created += 1

            # Close ~40% of cases
            if i < len(statuses) and statuses[i] == "closed":
                time.sleep(0.35)
                try:
                    cases_client.update_case(
                        domainId=DOMAIN_ID,
                        caseId=case_id,
                        fields=[fv("status", "closed")],
                    )
                except Exception:
                    pass  # Non-critical

            if created % 20 == 0:
                elapsed = (time.time() - start_time) if 'start_time' in dir() else 0
                print(f"   \u2705 {created}/{len(assignments)} ({case_errors} errors) - latest: {profile['name']} / {ctype}", flush=True)

        except Exception as e:
            case_errors += 1
            err_str = str(e)
            if "Throttl" in err_str or "TooMany" in err_str:
                print(f"   \u26a0\ufe0f  Throttled at #{i+1}! Backing off 5s...", flush=True)
                time.sleep(5)
            else:
                print(f"   \u274c Error #{case_errors} ({profile['name']}, {ctype}): {err_str[:120]}", flush=True)

        time.sleep(DELAY_BETWEEN_CASES)

    print(f"\n{'=' * 60}", flush=True)
    print(f"COMPLETE! {created} cases created ({case_errors} errors)", flush=True)
    print(f"   {unique} unique customers", flush=True)
    for ct, count in sorted(type_counts.items()):
        print(f"   {ct}: {count}", flush=True)
    print(f"{'=' * 60}", flush=True)


if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed = time.time() - start_time
    print(f"\nTotal time: {elapsed/60:.1f} minutes", flush=True)
