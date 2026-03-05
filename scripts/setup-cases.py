#!/usr/bin/env python3
"""
Setup Connect Cases: fields, layout, case rules (conditional visibility), and template.
Usage: unset PYTHONHOME PYTHONPATH && /usr/bin/python3 -u scripts/setup-cases.py
"""

import boto3
import json
import sys
import time

DOMAIN_ID = "619daed1-2572-4c78-8ecb-bdf7f27aee94"
REGION = "us-east-1"
TEMPLATE_ID = "09e1a574-338f-4fcd-9678-59e4bba6403a"  # Lost Baggage template

client = boto3.client('connectcases', region_name=REGION)

# ============================================================================
# STEP 1: Get existing fields
# ============================================================================
print("=" * 60, flush=True)
print("STEP 1: Inventory existing fields", flush=True)
print("=" * 60, flush=True)

existing_fields = {}
paginator_token = None
while True:
    kwargs = {"domainId": DOMAIN_ID, "maxResults": 100}
    if paginator_token:
        kwargs["nextToken"] = paginator_token
    resp = client.list_fields(**kwargs)
    for f in resp["fields"]:
        existing_fields[f["name"]] = {"fieldId": f["fieldId"], "type": f["type"]}
    paginator_token = resp.get("nextToken")
    if not paginator_token:
        break

print(f"   Found {len(existing_fields)} existing fields:", flush=True)
for name, info in sorted(existing_fields.items()):
    print(f"      {name}: {info['fieldId']} ({info['type']})", flush=True)

# ============================================================================
# STEP 2: Create missing fields
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("STEP 2: Create missing fields", flush=True)
print("=" * 60, flush=True)

# Fields to create (name, type, description)
FIELDS_TO_CREATE = [
    # Basic fields (always visible) - some are system fields
    ("ContactInfo", "Text", "Customer contact information"),
    ("Priority", "SingleSelect", "Case priority level"),
    # Lost Baggage specific (hidden by default, shown when case_reason = Lost Baggage)
    ("BagColor", "SingleSelect", "Color of the lost bag"),
    ("BagType", "SingleSelect", "Type of bag"),
    ("ContainsMedication", "Boolean", "Whether bag contains prescription medication"),
    ("EstimatedValue", "SingleSelect", "Estimated value range of bag contents"),
    # Damaged Item specific (hidden by default, shown when case_reason = Damaged Item)  
    ("DamageDescription", "Text", "Description of the damage"),
    ("ItemValue", "Text", "Value of the damaged item"),
    ("PurchaseDate", "Text", "Original purchase date"),
    ("ClaimAmount", "Text", "Requested claim amount"),
    ("DamageLocation", "SingleSelect", "Where damage was discovered"),
]

field_ids = {}  # name -> fieldId mapping

for name, ftype, desc in FIELDS_TO_CREATE:
    if name in existing_fields:
        field_ids[name] = existing_fields[name]["fieldId"]
        print(f"   ✅ {name}: already exists ({field_ids[name]})", flush=True)
    else:
        try:
            resp = client.create_field(
                domainId=DOMAIN_ID,
                name=name,
                type=ftype,
                description=desc
            )
            field_ids[name] = resp["fieldId"]
            print(f"   ✅ {name}: created ({field_ids[name]})", flush=True)
        except Exception as e:
            print(f"   ❌ {name}: {e}", flush=True)

# Add existing bag fields to our map
for name in ["FlightNumber", "BagDescription", "BagTagNumber", "ContentsDescription", 
             "DeliveryAddress", "BagPriority"]:
    if name in existing_fields:
        field_ids[name] = existing_fields[name]["fieldId"]

# System field IDs
SYSTEM_FIELDS = {
    "title": "title",
    "status": "status",
    "case_reason": "case_reason",
    "summary": "summary",
    "customer_id": "customer_id",
    "assigned_user": "assigned_user",
    "assigned_queue": "assigned_queue",
    "reference_number": "reference_number",
    "created_datetime": "created_datetime",
    "last_updated_datetime": "last_updated_datetime",
}

print(f"\n   Total custom fields mapped: {len(field_ids)}", flush=True)

# ============================================================================
# STEP 3: Add field options to SingleSelect fields
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("STEP 3: Add field options to SingleSelect fields", flush=True)
print("=" * 60, flush=True)

FIELD_OPTIONS = {
    "case_reason": [
        {"name": "Lost Baggage", "value": "lost_baggage"},
        {"name": "Damaged Item", "value": "damaged_item"},
        {"name": "Flight Delay", "value": "flight_delay"},
        {"name": "Booking Change", "value": "booking_change"},
        {"name": "Refund Request", "value": "refund_request"},
        {"name": "General Inquiry", "value": "general_inquiry"},
    ],
    "Priority": [
        {"name": "Critical", "value": "critical"},
        {"name": "High", "value": "high"},
        {"name": "Medium", "value": "medium"},
        {"name": "Low", "value": "low"},
    ],
    "BagColor": [
        {"name": "Black", "value": "black"},
        {"name": "Navy Blue", "value": "navy"},
        {"name": "Red", "value": "red"},
        {"name": "Gray", "value": "gray"},
        {"name": "Green", "value": "green"},
        {"name": "Brown", "value": "brown"},
        {"name": "Other", "value": "other"},
    ],
    "BagType": [
        {"name": "Hard Shell Suitcase", "value": "hardshell"},
        {"name": "Soft Side Suitcase", "value": "softside"},
        {"name": "Duffel Bag", "value": "duffel"},
        {"name": "Garment Bag", "value": "garment"},
        {"name": "Backpack", "value": "backpack"},
        {"name": "Other", "value": "other"},
    ],
    "EstimatedValue": [
        {"name": "Under $500", "value": "under_500"},
        {"name": "$500 - $1,000", "value": "500_1000"},
        {"name": "$1,000 - $2,500", "value": "1000_2500"},
        {"name": "Over $2,500", "value": "over_2500"},
    ],
    "DamageLocation": [
        {"name": "Baggage Claim", "value": "baggage_claim"},
        {"name": "During Flight", "value": "during_flight"},
        {"name": "At Gate", "value": "at_gate"},
        {"name": "Hotel/Destination", "value": "destination"},
        {"name": "Other", "value": "other"},
    ],
    "BagPriority": [
        {"name": "Standard", "value": "standard"},
        {"name": "Priority - Medical", "value": "priority_medical"},
        {"name": "Priority - Business", "value": "priority_business"},
        {"name": "Priority - VIP", "value": "priority_vip"},
    ],
}

for field_name, options in FIELD_OPTIONS.items():
    fid = field_ids.get(field_name) or SYSTEM_FIELDS.get(field_name)
    if not fid:
        print(f"   ⚠️  {field_name}: field not found, skipping options", flush=True)
        continue
    try:
        client.batch_put_field_options(
            domainId=DOMAIN_ID,
            fieldId=fid,
            options=[{"name": o["name"], "value": o["value"], "active": True} for o in options]
        )
        print(f"   ✅ {field_name}: {len(options)} options added", flush=True)
    except Exception as e:
        print(f"   ❌ {field_name}: {e}", flush=True)

# ============================================================================
# STEP 4: Create layout
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("STEP 4: Create layout with all fields", flush=True)
print("=" * 60, flush=True)

def field_item(field_id):
    return {"id": field_id}

layout_content = {
    "basic": {
        "topPanel": {
            "sections": [
                {
                    "fieldGroup": {
                        "name": "Case Overview",
                        "fields": [
                            field_item("case_reason"),
                            field_item(field_ids.get("Priority", "")),
                            field_item("summary"),
                            field_item("assigned_user"),
                        ]
                    }
                }
            ]
        },
        "moreInfo": {
            "sections": [
                {
                    "fieldGroup": {
                        "name": "Contact Information",
                        "fields": [
                            field_item("customer_id"),
                            field_item(field_ids.get("ContactInfo", "")),
                            field_item("reference_number"),
                        ]
                    }
                },
                {
                    "fieldGroup": {
                        "name": "Lost Baggage Details",
                        "fields": [
                            field_item(field_ids["FlightNumber"]),
                            field_item(field_ids["BagDescription"]),
                            field_item(field_ids["BagTagNumber"]),
                            field_item(field_ids.get("BagColor", "")),
                            field_item(field_ids.get("BagType", "")),
                            field_item(field_ids["ContentsDescription"]),
                            field_item(field_ids.get("ContainsMedication", "")),
                            field_item(field_ids.get("EstimatedValue", "")),
                            field_item(field_ids["DeliveryAddress"]),
                            field_item(field_ids["BagPriority"]),
                        ]
                    }
                },
                {
                    "fieldGroup": {
                        "name": "Damaged Item Details",
                        "fields": [
                            field_item(field_ids.get("DamageDescription", "")),
                            field_item(field_ids.get("DamageLocation", "")),
                            field_item(field_ids.get("ItemValue", "")),
                            field_item(field_ids.get("PurchaseDate", "")),
                            field_item(field_ids.get("ClaimAmount", "")),
                        ]
                    }
                },
                {
                    "fieldGroup": {
                        "name": "Dates",
                        "fields": [
                            field_item("created_datetime"),
                            field_item("last_updated_datetime"),
                        ]
                    }
                },
            ]
        }
    }
}

# Remove any empty field IDs
for panel in ["topPanel", "moreInfo"]:
    panel_data = layout_content["basic"][panel]
    for section in panel_data["sections"]:
        if "fieldGroup" in section:
            section["fieldGroup"]["fields"] = [
                f for f in section["fieldGroup"]["fields"] if f["fieldId"]
            ]

try:
    resp = client.create_layout(
        domainId=DOMAIN_ID,
        name="SkyConnect Airline Layout",
        content=layout_content
    )
    layout_id = resp["layoutId"]
    print(f"   ✅ Layout created: {layout_id}", flush=True)
except client.exceptions.ConflictException:
    # Layout exists, get its ID
    layouts = client.list_layouts(domainId=DOMAIN_ID)
    for l in layouts["layouts"]:
        if l["name"] == "SkyConnect Airline Layout":
            layout_id = l["layoutId"]
            # Update it
            client.update_layout(
                domainId=DOMAIN_ID,
                layoutId=layout_id,
                content=layout_content
            )
            print(f"   ✅ Layout updated: {layout_id}", flush=True)
            break
    else:
        layout_id = None
        print(f"   ❌ Could not find or create layout", flush=True)
except Exception as e:
    layout_id = None
    print(f"   ❌ Layout error: {e}", flush=True)

# ============================================================================
# STEP 5: Create case rules (hidden field conditions)
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("STEP 5: Create case rules for conditional visibility", flush=True)
print("=" * 60, flush=True)

# Lost Baggage fields - hidden by default, shown when case_reason = "lost_baggage"
LOST_BAG_FIELDS = [
    "FlightNumber", "BagDescription", "BagTagNumber", "BagColor", "BagType",
    "ContentsDescription", "ContainsMedication", "EstimatedValue",
    "DeliveryAddress", "BagPriority"
]

# Damaged Item fields - hidden by default, shown when case_reason = "damaged_item"
DAMAGED_ITEM_FIELDS = [
    "DamageDescription", "DamageLocation", "ItemValue", "PurchaseDate", "ClaimAmount"
]

rule_associations = []  # (caseRuleId, fieldId) pairs for template

def create_hidden_rule(field_name, trigger_value, rule_name_suffix):
    """Create a hidden rule: hidden by default, shown when case_reason == trigger_value"""
    fid = field_ids.get(field_name)
    if not fid:
        print(f"   ⚠️  {field_name}: no field ID, skipping rule", flush=True)
        return None
    
    rule_def = {
        "hidden": {
            "defaultValue": True,  # Hidden by default
            "conditions": [
                {
                    "equalTo": {
                        "operandOne": {"fieldId": "case_reason"},
                        "operandTwo": {"stringValue": trigger_value},
                        "result": False  # NOT hidden when condition matches (i.e., show it)
                    }
                }
            ]
        }
    }
    
    try:
        resp = client.create_case_rule(
            domainId=DOMAIN_ID,
            name=f"Show {field_name} for {rule_name_suffix}",
            description=f"Show {field_name} when Case Reason = {rule_name_suffix}",
            rule=rule_def
        )
        rule_id = resp["caseRuleId"]
        rule_associations.append({"caseRuleId": rule_id, "fieldId": fid})
        print(f"   ✅ Rule: Show {field_name} for {rule_name_suffix} ({rule_id})", flush=True)
        return rule_id
    except Exception as e:
        print(f"   ❌ Rule for {field_name}: {e}", flush=True)
        return None

def create_required_rule(field_name, trigger_value, rule_name_suffix):
    """Create a required rule: not required by default, required when case_reason == trigger_value"""
    fid = field_ids.get(field_name)
    if not fid:
        return None
    
    rule_def = {
        "required": {
            "defaultValue": False,
            "conditions": [
                {
                    "equalTo": {
                        "operandOne": {"fieldId": "case_reason"},
                        "operandTwo": {"stringValue": trigger_value},
                        "result": True
                    }
                }
            ]
        }
    }
    
    try:
        resp = client.create_case_rule(
            domainId=DOMAIN_ID,
            name=f"Require {field_name} for {rule_name_suffix}",
            description=f"Require {field_name} when Case Reason = {rule_name_suffix}",
            rule=rule_def
        )
        rule_id = resp["caseRuleId"]
        rule_associations.append({"caseRuleId": rule_id, "fieldId": fid})
        print(f"   ✅ Rule: Require {field_name} for {rule_name_suffix} ({rule_id})", flush=True)
        return rule_id
    except Exception as e:
        print(f"   ❌ Required rule for {field_name}: {e}", flush=True)
        return None

# Create hidden rules for Lost Baggage fields
print("\n   --- Lost Baggage field rules ---", flush=True)
for field_name in LOST_BAG_FIELDS:
    create_hidden_rule(field_name, "lost_baggage", "Lost Baggage")

# Create required rules for key Lost Baggage fields
print("\n   --- Lost Baggage required rules ---", flush=True)
for field_name in ["FlightNumber", "BagDescription", "DeliveryAddress"]:
    create_required_rule(field_name, "lost_baggage", "Lost Baggage")

# Create hidden rules for Damaged Item fields
print("\n   --- Damaged Item field rules ---", flush=True)
for field_name in DAMAGED_ITEM_FIELDS:
    create_hidden_rule(field_name, "damaged_item", "Damaged Item")

# Create required rules for key Damaged Item fields
print("\n   --- Damaged Item required rules ---", flush=True)
for field_name in ["DamageDescription", "ClaimAmount"]:
    create_required_rule(field_name, "damaged_item", "Damaged Item")

print(f"\n   Total rule associations: {len(rule_associations)}", flush=True)

# ============================================================================
# STEP 6: Update template with layout + rules
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("STEP 6: Update template with layout and rules", flush=True)
print("=" * 60, flush=True)

try:
    update_kwargs = {
        "domainId": DOMAIN_ID,
        "templateId": TEMPLATE_ID,
        "name": "SkyConnect Case",
        "description": "Unified case template for SkyConnect Airlines - fields adapt based on case reason",
    }
    
    if layout_id:
        update_kwargs["layoutConfiguration"] = {"defaultLayout": layout_id}
    
    if rule_associations:
        update_kwargs["rules"] = rule_associations
    
    client.update_template(**update_kwargs)
    print(f"   ✅ Template updated with layout + {len(rule_associations)} rules", flush=True)
except Exception as e:
    print(f"   ❌ Template update error: {e}", flush=True)

# ============================================================================
# SUMMARY
# ============================================================================
print(f"\n{'=' * 60}", flush=True)
print("🎉 SETUP COMPLETE", flush=True)
print("=" * 60, flush=True)
print(f"""
Template: SkyConnect Case ({TEMPLATE_ID})
Layout:   SkyConnect Airline Layout ({layout_id})
Rules:    {len(rule_associations)} total

Field Behavior:
  ✅ 10 basic fields: always visible
  ✅ 10 Lost Baggage fields: hidden → shown when Case Reason = "Lost Baggage"
  ✅ 5 Damaged Item fields: hidden → shown when Case Reason = "Damaged Item"
  ✅ 3 Lost Baggage fields required (FlightNumber, BagDescription, DeliveryAddress)
  ✅ 2 Damaged Item fields required (DamageDescription, ClaimAmount)

Test in Agent Workspace:
  1. Create a new case using "SkyConnect Case" template
  2. Select Case Reason = "Lost Baggage" → bag fields appear
  3. Change to "Damaged Item" → bag fields hide, damage fields appear
  4. Change to "General Inquiry" → only basic fields visible
""", flush=True)
