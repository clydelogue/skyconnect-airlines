# SkyConnect Airlines Demo

Amazon Connect demo instance configuration and assets for the **SkyConnect Airlines — Lost Baggage** end-to-end demo flow.

## Demo Overview

An airline customer reports a lost bag via a self-service website, chats with an AI agent for updates, and escalates to a human agent who sees full context in the Connect Agent Workspace.

### Flow
1. **Website** → Customer authenticates, selects flight, reports lost bag
2. **Guide** → Collects bag details, creates a Connect Case
3. **AI Chat** → Customer asks about bag status via Amazon Q agentic agent
4. **Escalation** → AI hands off to human agent (medical/safety trigger)
5. **Agent Workspace** → Agent sees case, profile, guides, and full transcript

## Connect Instance

| Property | Value |
|----------|-------|
| Region | us-east-1 |

## Project Structure

```
skyconnect-airlines/
├── README.md
├── index.html        # Mock airline website entry
├── app.js            # Website logic
├── styles.css
├── website/          # Mock airline website (HTML/JS/CSS)
└── knowledge/        # Q in Connect knowledge base content
```

## Getting Started

See the implementation plan in the project wiki or ask Aki.
