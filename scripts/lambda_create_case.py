"""
Lambda function: Create a Connect Case from the SkyConnect Airlines website.
Looks up customer profile by email, creates a case linked to that profile.
"""
import json
import boto3
import os

CASES_DOMAIN_ID = os.environ.get("CASES_DOMAIN_ID", "e71fc22e-8b4d-47c9-84d7-e7de24cf8ecb")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID", "40d32841-c13c-44e4-809a-dfdbed1cc83d")
PROFILES_DOMAIN = os.environ.get("PROFILES_DOMAIN", "amazon-connect-loguclyd-demo2")
REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "560576351083")

cases_client = boto3.client("connectcases", region_name=REGION)
profiles_client = boto3.client("customer-profiles", region_name=REGION)

# Field IDs from setup-cases.py — these are the custom field IDs in our Cases domain
# We'll look them up dynamically on cold start
FIELD_CACHE = {}


def get_field_id(field_name):
    """Look up a field ID by name, with caching."""
    if not FIELD_CACHE:
        # Load all fields
        next_token = None
        while True:
            kwargs = {"domainId": CASES_DOMAIN_ID, "maxResults": 100}
            if next_token:
                kwargs["nextToken"] = next_token
            resp = cases_client.list_fields(**kwargs)
            for f in resp["fields"]:
                FIELD_CACHE[f["name"]] = f["fieldId"]
            next_token = resp.get("nextToken")
            if not next_token:
                break
    return FIELD_CACHE.get(field_name)


def lookup_profile(email):
    """Search for a customer profile by email address."""
    try:
        resp = profiles_client.search_profiles(
            DomainName=PROFILES_DOMAIN,
            KeyName="_email",
            Values=[email],
            MaxResults=1,
        )
        items = resp.get("Items", [])
        if items:
            return items[0]["ProfileId"]
    except Exception as e:
        print(f"Profile lookup error: {e}")
    return None


def cors_response(status_code, body):
    """Return a response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    """Lambda handler."""
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return cors_response(200, {"message": "ok"})

    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {"error": "Invalid JSON body"})

    # Extract form data
    email = body.get("email", "")
    flight_number = body.get("flightNumber", "")
    bag_tag = body.get("bagTag", "")
    bag_description = body.get("bagDescription", "")
    contents = body.get("contents", "")
    delivery_address = body.get("deliveryAddress", "")
    has_medication = body.get("hasMedication", False)
    case_reason = body.get("caseReason", "Lost Baggage")

    if not email:
        return cors_response(400, {"error": "Email is required"})

    # Step 1: Look up customer profile
    profile_id = lookup_profile(email)
    if not profile_id:
        return cors_response(404, {"error": f"No profile found for {email}"})

    profile_arn = f"arn:aws:profile:{REGION}:{ACCOUNT_ID}:domains/{PROFILES_DOMAIN}/profiles/{profile_id}"

    # Step 2: Build case fields
    title = f"Lost Baggage — Flight {flight_number}" if flight_number else "Lost Baggage Report"
    priority = "High" if has_medication else "Medium"

    fields = [
        {"id": "title", "value": {"stringValue": title}},
        {"id": "customer_id", "value": {"stringValue": profile_arn}},
    ]

    # Add custom fields if they exist
    field_mappings = {
        "FlightNumber": flight_number,
        "BagTagNumber": bag_tag,
        "BagDescription": bag_description,
        "ContentsDescription": contents,
        "DeliveryAddress": delivery_address,
    }

    for field_name, value in field_mappings.items():
        if value:
            fid = get_field_id(field_name)
            if fid:
                fields.append({"id": fid, "value": {"stringValue": value}})

    # Add CaseReason (SingleSelect — use option values)
    case_reason_id = get_field_id("Case Reason")
    if case_reason_id:
        fields.append({"id": case_reason_id, "value": {"stringValue": "lost_baggage"}})

    # Add BagPriority (SingleSelect — use option values)
    bag_priority_id = get_field_id("BagPriority")
    if bag_priority_id:
        priority_value = "priority_medical" if has_medication else "standard"
        fields.append({"id": bag_priority_id, "value": {"stringValue": priority_value}})

    # Step 3: Create the case
    try:
        resp = cases_client.create_case(
            domainId=CASES_DOMAIN_ID,
            templateId=TEMPLATE_ID,
            fields=fields,
        )
        case_id = resp["caseId"]
        case_arn = resp["caseArn"]

        return cors_response(200, {
            "success": True,
            "caseId": case_id,
            "caseArn": case_arn,
            "profileId": profile_id,
            "title": title,
            "priority": priority,
        })

    except Exception as e:
        print(f"Case creation error: {e}")
        return cors_response(500, {"error": str(e)})
