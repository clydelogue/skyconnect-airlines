# SkyConnect Airlines — Connect Demo Instance Setup Overview

> **Last Updated**: March 5, 2026
> **Instance**: loguclyd-demo | **Region**: us-east-1 | **Account**: 560576351083

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [AWS Resources](#aws-resources)
  - [Connect Instance](#connect-instance)
  - [Customer Profiles](#customer-profiles)
  - [Cases](#cases)
  - [Lex Bot](#lex-bot)
  - [Contact Flows](#contact-flows)
  - [Routing](#routing)
  - [KMS Key](#kms-key)
- [Security Configuration](#security-configuration)
- [Data Population](#data-population)
- [Scripts Reference](#scripts-reference)
- [Access & Credentials](#access--credentials)
- [Rebuild / Reset Procedure](#rebuild--reset-procedure)
- [Lessons Learned & Gotchas](#lessons-learned--gotchas)
- [TODO / Future Work](#todo--future-work)

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  SkyConnect      │────▶│  Amazon Connect       │────▶│  Agent Workspace    │
│  Website (Chat)  │     │  Contact Flow + Lex   │     │  Profiles + Cases   │
└─────────────────┘     └──────────────────────┘     └─────────────────────┘
                               │                              │
                               ▼                              ▼
                        ┌──────────────┐            ┌──────────────────┐
                        │  Amazon Lex  │            │  Customer        │
                        │  ConnectDemo │            │  Profiles Domain │
                        │  Bot         │            │  (~2,150 profiles)│
                        └──────────────┘            └──────────────────┘
                                                           │
                                                           ▼
                                                    ┌──────────────────┐
                                                    │  Connect Cases   │
                                                    │  (200 cases)     │
                                                    └──────────────────┘
```

The demo simulates a **lost baggage** scenario for SkyConnect Airlines:
1. Customer visits the website and initiates a chat
2. Lex bot handles initial greeting and intent detection
3. Chat transfers to a human agent via BasicQueue
4. Agent sees the customer's profile (loyalty tier, SkyMiles, contact info) and linked cases in the Agent Workspace

---

## AWS Resources

### Connect Instance

| Property | Value |
|----------|-------|
| **Alias** | `loguclyd-demo` |
| **Instance ID** | `524d1a50-ebd2-49f9-8949-a9faf9076635` |
| **Region** | `us-east-1` |
| **Created** | March 3, 2026 |
| **Admin Console** | https://loguclyd-demo.my.connect.aws/ |
| **Agent Workspace** | https://loguclyd-demo.my.connect.aws/agent-app-v2/ |
| **AWS Console** | https://us-east-1.console.aws.amazon.com/connect/home?region=us-east-1 |

### Customer Profiles

| Property | Value |
|----------|-------|
| **Domain Name** | `amazon-connect-loguclyd-demo2` |
| **Profile Count** | ~2,150 (2,000 bulk + 1 Sarah Chen + 149 case-linked) |
| **KMS Key** | `arn:aws:kms:us-east-1:560576351083:key/0e763104-4e65-47ed-b3d3-7448ec5fe2a3` |
| **Key Customer** | Sarah Chen — `sarah.chen@email.com` (Profile ID: `1fc1ea045c974a3dbca103099643b653`) |

**Profile attributes:**
- `FirstName`, `LastName`, `EmailAddress`, `PhoneNumber`, `Gender`
- `Address` (Address1, City, State, PostalCode, Country)
- Custom: `LoyaltyTier` (SkyBasic/SkySilver/SkyGold/SkyPlatinum/SkyDiamond), `SkyMiles`, `MemberId`

**Tier distribution** (approximate for 2,000 bulk profiles):
| Tier | % | Count |
|------|---|-------|
| SkyBasic | 40% | ~800 |
| SkySilver | 25% | ~500 |
| SkyGold | 20% | ~400 |
| SkyPlatinum | 10% | ~200 |
| SkyDiamond | 5% | ~100 |

### Cases

| Property | Value |
|----------|-------|
| **Domain ID** | `e71fc22e-8b4d-47c9-84d7-e7de24cf8ecb` |
| **Domain Name** | `loguclyd-demo-cases` |
| **Template** | SkyConnect Case (`40d32841-c13c-44e4-809a-dfdbed1cc83d`) |
| **Layout** | SkyConnect Layout (`998be8b0-18eb-4c61-ba9e-73c31df36ffa`) |
| **Case Count** | 200 |
| **Case Rules** | 20 (conditional field visibility + required fields) |

**Case types and distribution:**
| Type | Count | Description |
|------|-------|-------------|
| Lost Baggage | 80 | Bag not arrived at destination |
| Damaged Item | 30 | Bag or contents damaged |
| Flight Delay | 30 | Flight delay compensation |
| Booking Change | 30 | Itinerary modifications |
| Refund Request | 20 | Refund for services |
| General Inquiry | 10 | Other questions |

**Custom case fields:**
- `FlightNumber` (Text) — Flight number for the report
- `BagDescription` (Text) — Physical description of the bag
- `BagTagNumber` (Text) — Airline bag tag number
- `ContentsDescription` (Text) — Summary of bag contents
- `DeliveryAddress` (Text) — Address for bag delivery
- `BagPriority` (SingleSelect) — Priority level
- `CaseReason` (SingleSelect) — Lost Baggage, Damaged Item, Flight Delay, Booking Change, Refund Request, General Inquiry

**Lost Baggage Case Template:**
- Template ID: `09e1a574-338f-4fcd-9678-59e4bba6403a`
- Includes all custom fields above

### Lex Bot

| Property | Value |
|----------|-------|
| **Bot Name** | `ConnectDemoBot` |
| **Bot ID** | `DXOXNJVQNK` |
| **Alias** | `ConnectAlias` (`RTB5Q1OAXY`) |
| **Alias ARN** | `arn:aws:lex:us-east-1:560576351083:bot-alias/DXOXNJVQNK/RTB5Q1OAXY` |
| **IAM Role** | `ConnectDemoLexRole` |
| **Intents** | Greeting, OrderStatus, FallbackIntent |

### Contact Flows

**SkyConnect Chat Flow:**
| Property | Value |
|----------|-------|
| **Flow ID** | `a23c0fc7-5ede-439e-85f2-05f67ee8ff05` |
| **Flow ARN** | `arn:aws:connect:us-east-1:560576351083:instance/524d1a50-ebd2-49f9-8949-a9faf9076635/contact-flow/a23c0fc7-5ede-439e-85f2-05f67ee8ff05` |
| **Type** | CONTACT_FLOW (chat) |
| **JSON Export** | `flows/skyconnect-chat-flow.json` |

**Flow logic:**
1. Welcome message → "Welcome to SkyConnect Airlines support..."
2. Check if `customerName` attribute is set
3. Personalized greeting (known) or generic greeting (unknown)
4. Lex bot handles input (Greeting → loop, OrderStatus → specialist message)
5. Set queue → BasicQueue
6. Transfer to queue → Agent picks up
7. Error handling → "All specialists busy" → Disconnect

### Routing

| Resource | ID | Notes |
|----------|----|-------|
| **BasicQueue** | `171d2b42-bc7c-4f28-baea-6bb65b152cd2` | Default queue for all contacts |
| **Default Routing Profile** | `68960be3-7cf8-4615-a495-ef1e48c7e5ea` | CHAT enabled |
| **Sample Inbound Flow** | `a7d608d9-5c78-4ee2-8869-f5b25a14c880` | Default flow |

### KMS Key

| Property | Value |
|----------|-------|
| **Key ARN** | `arn:aws:kms:us-east-1:560576351083:key/0e763104-4e65-47ed-b3d3-7448ec5fe2a3` |
| **Usage** | Customer Profiles domain encryption |
| **Key Policy** | Allows Connect SLR (`AWSServiceRoleForAmazonConnect_*`) to use for encrypt/decrypt |

---

## Security Configuration

### Admin User

| Property | Value |
|----------|-------|
| **Username** | `admin` |
| **User ID** | `31dae8ad-1f56-49fc-989c-010df8c9870b` |
| **Security Profile** | Admin (`77f6441b-a42b-48ed-8a8b-d23a45935551`) |

### Security Profiles

| Profile | ID | Permissions |
|---------|----|-------------|
| **Admin** | `77f6441b-a42b-48ed-8a8b-d23a45935551` | 179 permissions (full admin) |
| **CallCenterManager** | `a66c64ab-3392-441b-95bc-79e676f31e6f` | 64 permissions |
| **QualityAnalyst** | `1bbc68bc-d756-4d56-99ec-55e8daf3744b` | 4 permissions |
| **Agent** | `ac358602-4d55-40ef-9194-141b584ece95` | 3 permissions |

### Critical Customer Profiles Permissions

The Admin security profile **must** have these Customer Profiles permissions enabled:

| Permission | Required For |
|------------|-------------|
| `CustomerProfiles.View` | Viewing profiles in agent workspace |
| `CustomerProfiles.Edit` | Editing profile data |
| `CustomerProfiles.Create` | Creating new profiles |
| `CustomerProfiles.Segments.View/Create/Delete` | Customer segments |
| `CustomerProfiles.CalculatedAttributes.View/Edit/Create/Delete` | Calculated attributes |
| **Profile explorer — View** | ⚠️ **Renders the profile search UI in agent workspace** |
| **Predictive insights** | Predictive analytics features |

> ⚠️ **Profile explorer** is a separate permission from `CustomerProfiles.View`. Without it, the profile search panel doesn't appear in the agent workspace at all.

---

## Data Population

### Profile Generation

The `generate-profiles.py` script creates realistic US customer profiles:

- **2,000 bulk profiles** with randomized names, addresses, phone numbers, emails
- **149 case-linked profiles** created by `generate-cases.py` for case associations
- **1 Sarah Chen** profile (demo protagonist)
- All profiles include `LoyaltyTier`, `SkyMiles`, and `MemberId` custom attributes
- Emails are guaranteed unique
- Addresses use realistic US city/state/ZIP combinations

### Case Generation

The `generate-cases.py` script creates 200 cases across 6 case types:

- Creates 149 fresh profiles specifically for case linking
- Each case is linked to a profile via the `customer_id` field (profile ARN)
- Cases include type-specific fields (flight numbers, bag descriptions, etc.)
- Rate-limited to ~1.4 TPS to respect Connect Cases API limits
- ~150 unique customers, some with 2 cases

---

## Scripts Reference

All scripts are in the `scripts/` directory. Run from the repo root.

### Prerequisites

```bash
# AWS credentials (via Isengard)
ada credentials update --account 560576351083 --role Admin

# Python 3 with boto3
pip3 install boto3
```

### `generate-profiles.py` — Bulk profile creation

```bash
# Generate and upload 2,000 profiles (default)
unset PYTHONHOME PYTHONPATH && python3 scripts/generate-profiles.py

# Custom count
python3 scripts/generate-profiles.py --count 500

# Dry run (generate but don't upload)
python3 scripts/generate-profiles.py --dry-run --output profiles.json

# Options
#   --domain    Customer Profiles domain (default: amazon-connect-loguclyd-demo2)
#   --region    AWS region (default: us-east-1)
#   --threads   Parallel upload threads (default: 10)
#   --count     Number of profiles (default: 2000)
```

**Performance**: ~29 profiles/sec with 10 threads. 2,000 profiles in ~68 seconds.

### `generate-cases.py` — Case creation with profile linking

```bash
unset PYTHONHOME PYTHONPATH && python3 -u scripts/generate-cases.py
```

- Creates 149 profiles + 200 cases
- Takes ~6 minutes (rate-limited by Cases API at ~1.4 TPS)
- Hardcoded config: domain ID, template ID, Sarah Chen profile ID

### `setup-cases.py` — Cases schema setup (fields, layout, rules, template)

```bash
unset PYTHONHOME PYTHONPATH && python3 -u scripts/setup-cases.py
```

- Creates custom fields (FlightNumber, BagDescription, etc.)
- Creates the SkyConnect Layout
- Creates 20 case rules (conditional field visibility)
- Creates the SkyConnect Case template
- **Idempotent** — safe to re-run

### `setup-connect.sh` — Initial instance setup

```bash
bash scripts/setup-connect.sh
```

- Creates the SkyConnect Chat contact flow
- Creates Sarah Chen profile
- Creates Lost Baggage case fields and template
- **Note**: Uses older domain/config values — prefer the Python scripts above

### `delete-all-profiles.py` — Profile cleanup

```bash
unset PYTHONHOME PYTHONPATH && python3 scripts/delete-all-profiles.py
```

- Enumerates all profiles by LastName search
- Bulk deletes with parallel threads
- **Note**: Update `DOMAIN` constant before running

---

## Access & Credentials

### AWS Account Access

```bash
# Get credentials via Isengard
ada credentials update --account 560576351083 --role Admin
```

### Connect Admin Console

- **URL**: https://loguclyd-demo.my.connect.aws/
- **Username**: `admin`
- **Password**: `Keystone1!`

### AWS Console (Connect)

- **URL**: https://us-east-1.console.aws.amazon.com/connect/home?region=us-east-1
- Federate via Isengard → Account 560576351083 → Admin role

---

## Rebuild / Reset Procedure

If you need to wipe and rebuild the demo data:

### 1. Delete existing cases

```python
# Quick inline script or use the delete approach from generate-cases.py
import boto3, time
client = boto3.client('connectcases', region_name='us-east-1')
domain_id = 'e71fc22e-8b4d-47c9-84d7-e7de24cf8ecb'

# Search and delete all cases
cases = []
resp = client.search_cases(domainId=domain_id, maxResults=100)
cases.extend([c['caseId'] for c in resp.get('cases', [])])
while 'nextToken' in resp:
    resp = client.search_cases(domainId=domain_id, maxResults=100, nextToken=resp['nextToken'])
    cases.extend([c['caseId'] for c in resp.get('cases', [])])

for cid in cases:
    client.delete_case(domainId=domain_id, caseId=cid)
    time.sleep(0.1)
```

### 2. Delete existing profiles (if needed)

```bash
python3 scripts/delete-all-profiles.py
```

### 3. Regenerate profiles

```bash
python3 scripts/generate-profiles.py --count 2000
```

### 4. Regenerate cases

```bash
python3 -u scripts/generate-cases.py
```

### 5. Verify

- Log into Connect admin console
- Navigate to Customer Profiles → search for "Sarah Chen"
- Navigate to Cases → verify cases appear with linked profiles

### Nuclear Option: Recreate Customer Profiles Domain

If the Customer Profiles integration is broken (session policy errors):

1. **AWS Console** → Connect → loguclyd-demo → Customer Profiles → **Disable domain**
2. **AWS Console** → Customer Profiles → **Delete the old domain** (or via API: `delete_domain`)
3. **AWS Console** → Connect → loguclyd-demo → Customer Profiles → **Enable Customer Profiles**
   - Let the console create the domain (it will auto-name it `amazon-connect-<instance-alias>`)
   - Use KMS key: `arn:aws:kms:us-east-1:560576351083:key/0e763104-4e65-47ed-b3d3-7448ec5fe2a3`
4. **Enable Profile Explorer permission** in Admin security profile (see [Gotchas](#lessons-learned--gotchas))
5. Re-run profile and case generation scripts
6. Log out and back into Connect to get fresh session policy

---

## Lessons Learned & Gotchas

### 🔴 Customer Profiles domain MUST be created via AWS Console

Creating a domain via the `customer-profiles` API (`create_domain` / `put_integration`) does **not** establish the internal Connect-side integration mapping. This means Connect's session policy generator won't include `profile:SearchProfiles` permissions, resulting in 403 errors when agents try to search profiles.

**Fix**: Always create/enable Customer Profiles through the **AWS Console** → Connect → Customer Profiles page.

### 🔴 Domain name must match `amazon-connect-*` pattern

The Connect Service-Linked Role (SLR) policy `AmazonConnectServiceLinkedRolePolicy` only allows `profile:*` actions on resources matching `arn:aws:profile:*:*:domains/amazon-connect-*`. A domain named `loguclyd-demo` will fail with permission errors.

### 🔴 `update-security-profile` API REPLACES all permissions

The Connect `update-security-profile` API **replaces** the entire permissions list — it does NOT append. If you call it with only Customer Profiles permissions, you'll wipe out Users, SecurityProfiles, Queues, and everything else.

**Safe approach**: Always fetch existing permissions first, merge, then update:

```python
# Get current permissions
current = []
kwargs = {'InstanceId': instance_id, 'SecurityProfileId': profile_id, 'MaxResults': 100}
while True:
    resp = client.list_security_profile_permissions(**kwargs)
    current.extend(resp['Permissions'])
    if 'NextToken' in resp:
        kwargs['NextToken'] = resp['NextToken']
    else:
        break

# Merge with new permissions
all_perms = sorted(set(current) | set(new_permissions))

# Update
client.update_security_profile(
    SecurityProfileId=profile_id,
    InstanceId=instance_id,
    Permissions=all_perms
)
```

### 🟡 "Profile explorer" is a separate permission

`CustomerProfiles.View` lets the agent see profile data, but the **Profile Explorer** UI panel (the search interface) requires a separate permission called "Profile explorer" in the security profile. Without it, the profile search panel simply doesn't render.

Enable it via: **Connect Admin** → Security Profiles → Admin → Customer Profiles → check **Profile explorer** → Save.

### 🟡 Cases API rate limits

- `CreateCase`: 2 TPS with burst of 10
- `UpdateCase`: 2 TPS with burst of 2
- `DeleteCase`: Not documented but works at ~10 TPS
- The `generate-cases.py` script throttles to ~1.4 TPS to stay safe

### 🟡 Cases `moreInfo` layout supports max 1 section

The Connect Cases API limits the `moreInfo` layout area to a single section. Attempting to add multiple sections will fail.

### 🟡 Flow JSON requires specific action types

When creating contact flows via API:
- Use `TransferToQueue` (not `TransferContactToQueue`)
- Action identifiers must be unique strings (not UUIDs)
- The flow JSON schema is `Version: "2019-10-30"`

---

## TODO / Future Work

- [ ] Configure chat widget in Connect admin (needs the SkyConnect Chat Flow)
- [ ] Embed Connect chat widget JS in `website/index.html`
- [ ] Set up Amazon Q in Connect (AI agent for automated responses)
- [ ] Claim a phone number (optional — for voice demo)
- [ ] Clean up orphaned KMS key permissions (if any)
- [ ] Add Guides for step-by-step agent workflows
- [ ] Populate `knowledge/` directory for Q in Connect knowledge base
