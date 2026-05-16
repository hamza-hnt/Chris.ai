# Overview

Chris.AI is an autonomous AI property management platform for rental portfolios.
It helps manage tenant requests, landlord approvals, provider coordination, rent
receipts, lease lifecycle events, and document production.

The product has two layers:

- Single Chris agent: one logical agent scoped to one property.
- Orchestration layer: deterministic routing, context loading, state tracking,
  alerts, and human intervention hooks for the whole fleet.

The first build focuses on the single-agent prompt system and a runnable project
skeleton. WhatsApp, email, SLNG voice, and provider integrations are stubbed.

```mermaid
flowchart LR
    Tenant[Tenant] --> Router[Deterministic Router]
    Landlord[Landlord] --> Router
    Provider[Provider] --> Router
    Router --> Context[Property-Scoped Context]
    Context --> Chris[Single Chris Agent]
    Chris --> Tools[Tool Executor]
    Tools --> Postgres[(PostgreSQL)]
    Supervisor[Supervisor] --> Intervention[Intervention Channel]
    Intervention --> Chris
```

## Core Principles

Agents do the thinking. They interpret messages, maintain plans, decide the next
allowed action, communicate with humans, and produce controlled documents.

Orchestration does the plumbing. It resolves senders, loads context, enforces
property scope, persists state, executes alerts, and exposes supervisor controls.

One property means one logical Chris. There is one FastAPI deployment and one
agent class. The API injects exactly one property's context per turn.

## Read Next

- [Architecture](02-architecture.md)
- [Single Agent](03-single-agent.md)
- [Security and Isolation](10-security-and-isolation.md)
