# loguclyd-demo

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
| Alias | loguclyd-demo |
| Instance ID | 524d1a50-ebd2-49f9-8949-a9faf9076635 |
| Region | us-east-1 |
| Admin URL | https://loguclyd-demo.my.connect.aws/ |

## Project Structure

```
loguclyd-demo/
├── README.md
├── website/          # Mock airline website (HTML/JS/CSS)
├── flows/            # Connect contact flow exports
├── guides/           # Guide definitions
├── knowledge/        # Q in Connect knowledge base content
└── scripts/          # Demo reset & setup scripts
```

## Getting Started

See the implementation plan in the project wiki or ask Aki.
