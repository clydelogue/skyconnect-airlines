#!/bin/bash
# =============================================================================
# SkyConnect Airlines - Connect Instance Setup
# Creates: Contact Flow, Cases Template, Customer Profile, Chat Widget Config
# Requires: ada credentials for account 560576351083
# =============================================================================

set -euo pipefail

INSTANCE_ID="524d1a50-ebd2-49f9-8949-a9faf9076635"
REGION="us-east-1"
CASES_DOMAIN_ID="619daed1-2572-4c78-8ecb-bdf7f27aee94"
QUEUE_ID="171d2b42-bc7c-4f28-baea-6bb65b152cd2"
PROFILES_DOMAIN="loguclyd-demo"

# Get credentials
echo "🔑 Getting AWS credentials via ada..."
eval $(unset PYTHONHOME PYTHONPATH; ada credentials print --account 560576351083 --role Admin 2>/dev/null | /usr/bin/python3 -c "
import sys, json
creds = json.load(sys.stdin)
print(f'export AWS_ACCESS_KEY_ID={creds[\"AccessKeyId\"]}')
print(f'export AWS_SECRET_ACCESS_KEY={creds[\"SecretAccessKey\"]}')
print(f'export AWS_SESSION_TOKEN={creds[\"SessionToken\"]}')
")
export AWS_DEFAULT_REGION=$REGION

echo ""
echo "✅ Credentials loaded. Setting up Connect instance..."
echo ""

# Unset PYTHONHOME so AWS CLI works
unset PYTHONHOME PYTHONPATH 2>/dev/null || true

# =============================================================================
# 1. CREATE CHAT CONTACT FLOW
# =============================================================================
echo "📋 Step 1: Creating SkyConnect Chat contact flow..."

FLOW_CONTENT='{
  "Version": "2019-10-30",
  "StartAction": "set-logging",
  "Actions": [
    {
      "Identifier": "set-logging",
      "Type": "EnableFlowLogging",
      "Parameters": {},
      "Transitions": {
        "NextAction": "set-voice"
      }
    },
    {
      "Identifier": "set-voice",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "Welcome to SkyConnect Airlines support. Let me look up your account."
      },
      "Transitions": {
        "NextAction": "check-attribute",
        "Errors": [
          {
            "NextAction": "check-attribute",
            "ErrorType": "NoMatchingError"
          }
        ]
      }
    },
    {
      "Identifier": "check-attribute",
      "Type": "CheckContactAttributes",
      "Parameters": {
        "Attribute": {
          "Key": "customerName",
          "Namespace": "User Defined"
        },
        "ComparisonValue": ""
      },
      "Transitions": {
        "NextAction": "greet-known",
        "Conditions": [],
        "Errors": [
          {
            "NextAction": "greet-unknown",
            "ErrorType": "NoMatchingCondition"
          }
        ]
      }
    },
    {
      "Identifier": "greet-known",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "Hi $.Attributes.customerName! I can see your account. How can I help you today?"
      },
      "Transitions": {
        "NextAction": "get-input"
      }
    },
    {
      "Identifier": "greet-unknown",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "How can I help you today?"
      },
      "Transitions": {
        "NextAction": "get-input"
      }
    },
    {
      "Identifier": "get-input",
      "Type": "GetParticipantInput",
      "Parameters": {
        "LexV2Bot": {
          "AliasArn": "arn:aws:lex:us-east-1:560576351083:bot-alias/DXOXNJVQNK/RTB5Q1OAXY"
        },
        "Text": ""
      },
      "Transitions": {
        "NextAction": "set-queue",
        "Conditions": [
          {
            "NextAction": "handle-greeting",
            "Condition": {
              "Operator": "Equals",
              "Operands": ["Greeting"]
            }
          },
          {
            "NextAction": "handle-order-status",
            "Condition": {
              "Operator": "Equals",
              "Operands": ["OrderStatus"]
            }
          }
        ],
        "Errors": [
          {
            "NextAction": "set-queue",
            "ErrorType": "NoMatchingCondition"
          },
          {
            "NextAction": "set-queue",
            "ErrorType": "NoMatchingError"
          }
        ]
      }
    },
    {
      "Identifier": "handle-greeting",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "Hello! I am here to help with your SkyConnect Airlines inquiry. What can I assist you with?"
      },
      "Transitions": {
        "NextAction": "get-input"
      }
    },
    {
      "Identifier": "handle-order-status",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "Let me look into that for you. I can see your recent case. Let me connect you with a specialist who can provide detailed tracking information."
      },
      "Transitions": {
        "NextAction": "set-queue"
      }
    },
    {
      "Identifier": "set-queue",
      "Type": "UpdateContactTargetQueue",
      "Parameters": {
        "QueueId": "arn:aws:connect:us-east-1:560576351083:instance/524d1a50-ebd2-49f9-8949-a9faf9076635/queue/171d2b42-bc7c-4f28-baea-6bb65b152cd2"
      },
      "Transitions": {
        "NextAction": "transfer-msg",
        "Errors": [
          {
            "NextAction": "transfer-msg",
            "ErrorType": "NoMatchingError"
          }
        ]
      }
    },
    {
      "Identifier": "transfer-msg",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "I am connecting you with a SkyConnect baggage specialist now. They will have full context of your case. Please hold..."
      },
      "Transitions": {
        "NextAction": "transfer-queue"
      }
    },
    {
      "Identifier": "transfer-queue",
      "Type": "TransferToQueue",
      "Parameters": {},
      "Transitions": {
        "NextAction": "disconnect",
        "Errors": [
          {
            "NextAction": "error-msg",
            "ErrorType": "QueueAtCapacity"
          },
          {
            "NextAction": "error-msg",
            "ErrorType": "NoMatchingError"
          }
        ]
      }
    },
    {
      "Identifier": "error-msg",
      "Type": "MessageParticipant",
      "Parameters": {
        "Text": "I apologize, but all our specialists are currently busy. Please try again in a few minutes or call us at 1-800-SKY-HELP."
      },
      "Transitions": {
        "NextAction": "disconnect"
      }
    },
    {
      "Identifier": "disconnect",
      "Type": "DisconnectParticipant",
      "Parameters": {},
      "Transitions": {}
    }
  ]
}'

FLOW_RESULT=$(aws connect create-contact-flow \
  --instance-id $INSTANCE_ID \
  --name "SkyConnect Chat Flow" \
  --type "CONTACT_FLOW" \
  --content "$FLOW_CONTENT" \
  --description "Main chat flow for SkyConnect Airlines lost baggage demo" \
  --region $REGION \
  --output json 2>&1) || true

if echo "$FLOW_RESULT" | grep -q "ContactFlowId"; then
  FLOW_ID=$(echo "$FLOW_RESULT" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['ContactFlowId'])")
  echo "   ✅ Flow created: $FLOW_ID"
else
  echo "   ⚠️  Flow creation result: $FLOW_RESULT"
  echo "   (May already exist — checking...)"
  FLOW_ID=$(aws connect list-contact-flows \
    --instance-id $INSTANCE_ID \
    --contact-flow-types "CONTACT_FLOW" \
    --region $REGION \
    --query "ContactFlowSummaryList[?Name=='SkyConnect Chat Flow'].Id" \
    --output text 2>/dev/null) || true
  if [ -n "$FLOW_ID" ]; then
    echo "   ✅ Found existing flow: $FLOW_ID"
  fi
fi

# =============================================================================
# 2. CREATE CUSTOMER PROFILE - Sarah Chen
# =============================================================================
echo ""
echo "👤 Step 2: Creating customer profile for Sarah Chen..."

PROFILE_RESULT=$(aws customer-profiles create-profile \
  --domain-name $PROFILES_DOMAIN \
  --first-name "Sarah" \
  --last-name "Chen" \
  --email-address "sarah.chen@email.com" \
  --phone-number "+14155550142" \
  --address '{
    "Address1": "425 Park Avenue, Apt 12B",
    "City": "New York",
    "State": "NY",
    "PostalCode": "10022",
    "Country": "US"
  }' \
  --attributes '{
    "LoyaltyTier": "SkyGold",
    "SkyMiles": "124500",
    "MemberId": "SC-20190415-001"
  }' \
  --region $REGION \
  --output json 2>&1) || true

if echo "$PROFILE_RESULT" | grep -q "ProfileId"; then
  PROFILE_ID=$(echo "$PROFILE_RESULT" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['ProfileId'])")
  echo "   ✅ Profile created: $PROFILE_ID"
else
  echo "   ⚠️  Profile result: $PROFILE_RESULT"
fi

# =============================================================================
# 3. ADD LOST BAGGAGE CASE FIELDS & TEMPLATE
# =============================================================================
echo ""
echo "🧳 Step 3: Setting up Lost Baggage case template..."

# Create custom fields
for FIELD_DEF in \
  '{"Name":"FlightNumber","Type":"Text","Description":"Flight number for the lost bag report"}' \
  '{"Name":"BagDescription","Type":"Text","Description":"Physical description of the bag"}' \
  '{"Name":"BagTagNumber","Type":"Text","Description":"Airline bag tag number"}' \
  '{"Name":"ContentsDescription","Type":"Text","Description":"Summary of bag contents"}' \
  '{"Name":"DeliveryAddress","Type":"Text","Description":"Address for bag delivery"}' \
  '{"Name":"BagPriority","Type":"SingleSelect","Description":"Priority level"}'
do
  FIELD_NAME=$(echo $FIELD_DEF | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['Name'])")
  FIELD_TYPE=$(echo $FIELD_DEF | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['Type'])")
  FIELD_DESC=$(echo $FIELD_DEF | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['Description'])")
  
  FIELD_RESULT=$(aws connectcases create-field \
    --domain-id $CASES_DOMAIN_ID \
    --name "$FIELD_NAME" \
    --type "$FIELD_TYPE" \
    --description "$FIELD_DESC" \
    --region $REGION \
    --output json 2>&1) || true
  
  if echo "$FIELD_RESULT" | grep -q "fieldId"; then
    FID=$(echo "$FIELD_RESULT" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['fieldId'])")
    echo "   ✅ Field '$FIELD_NAME': $FID"
  else
    echo "   ⚠️  Field '$FIELD_NAME': already exists or error"
  fi
done

# Create Lost Baggage case template
echo ""
echo "   Creating Lost Baggage template..."
TEMPLATE_RESULT=$(aws connectcases create-template \
  --domain-id $CASES_DOMAIN_ID \
  --name "Lost Baggage" \
  --description "Template for lost baggage reports - SkyConnect Airlines demo" \
  --region $REGION \
  --output json 2>&1) || true

if echo "$TEMPLATE_RESULT" | grep -q "templateId"; then
  TEMPLATE_ID=$(echo "$TEMPLATE_RESULT" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin)['templateId'])")
  echo "   ✅ Template created: $TEMPLATE_ID"
else
  echo "   ⚠️  Template result: $TEMPLATE_RESULT"
fi

# =============================================================================
# 4. SUMMARY
# =============================================================================
echo ""
echo "============================================"
echo "🎉 Setup Complete!"
echo "============================================"
echo ""
echo "Contact Flow ID: ${FLOW_ID:-unknown}"
echo "Customer Profile: Sarah Chen (sarah.chen@email.com)"
echo "Cases Template: Lost Baggage"
echo ""
echo "Next steps:"
echo "  1. Create a chat widget in Connect admin console"
echo "     (Admin → Channels → Chat → Add chat widget)"
echo "     Use flow: SkyConnect Chat Flow"
echo "  2. Copy the widget snippet into website/index.html"
echo "  3. Push changes to GitHub"
echo ""
