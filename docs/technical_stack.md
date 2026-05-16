# Technical Stack

This early note is superseded by the structured documentation set:

- [Overview](01-overview.md)
- [Architecture](02-architecture.md)
- [Data Model](05-data-model.md)
- [Local Development](09-local-development.md)

The original notes remain below for historical context.

## Overview

This project is a cloud-native platform for an autonomous real estate agent. The system coordinates conversations and workflows between tenants, property owners, service providers, and internal supervisors.

The agent primarily receives tenant and owner requests through WhatsApp, can communicate with external providers by email, tracks active cases, preserves operational context, performs real-time web research when needed, and exposes activity metrics through a business intelligence dashboard.

The backend is stateless by design. No application instance keeps critical state in memory between requests. For each incoming event, the backend reloads the required business data and agent context from persistent storage, executes the workflow in memory, persists the updated state, and then returns or dispatches the appropriate response.

## Core Architecture

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React | BI dashboard and supervision interface |
| Backend | FastAPI / Python | Main API, webhooks, business orchestration |
| AI Agent | OpenAI API | Reasoning, decision-making, response generation |
| Agent Context | PostgreSQL JSONB | Agent memory, conversations, cases, plans, workflow state |
| ACID Data | PostgreSQL | Users, properties, leases, payments, providers, permissions |
| Web Search | Tavily | Real-time web search and external information retrieval |
| Voice | Gradium | Speech-to-text and text-to-speech interactions |
| Voice Infrastructure | SLNG | Hosting and execution layer for voice models |
| Communication | WhatsApp / Email | Tenant, owner, and service provider communication |

## FastAPI Backend

FastAPI is the core application layer. It receives external events, applies business rules, calls the AI agent, coordinates integrations, and exposes operational data to the dashboard.

Its main responsibilities are:

- Receive inbound messages from WhatsApp and email channels.
- Identify the tenant, owner, property, lease, and related case.
- Load relational business data from PostgreSQL.
- Load agent context and workflow state from PostgreSQL JSONB.
- Invoke the OpenAI-powered agent with the appropriate context and constraints.
- Trigger external tools such as Tavily, WhatsApp, email, Gradium, and provider integrations.
- Persist messages, decisions, tool traces, case updates, and workflow changes.
- Expose API endpoints consumed by the React dashboard.

## OpenAI Agent

The AI agent is workflow-oriented. It is not intended to behave as a generic chatbot. It understands incoming requests, determines the current case state, follows active plans, updates milestones, and decides the next operational action.

The agent can:

- Create and classify a new case.
- Continue an existing case with preserved context.
- Ask for missing information.
- Request owner approval before a cost-bearing action.
- Coordinate with tenants and service providers.
- Use web search when external information is required.
- Escalate cases when automation is not sufficient.
- Close resolved requests and summarize outcomes.

The agent must follow the platform's business rules, including confidentiality between parties, owner validation before spending, strict tracking of active workflows, and systematic persistence of important decisions.

## PostgreSQL JSONB

PostgreSQL JSONB stores flexible operational memory for the agent. This data is highly dynamic, document-oriented, and may evolve as workflows become more advanced.

JSONB is used for:

- Conversation history.
- Tenant and owner interaction context.
- Active cases.
- Plans and milestones.
- Saved notes and summaries.
- Tool execution traces.
- Temporary workflow state.
- Agent-facing operational memory.

JSONB is appropriate for this layer because the data is naturally JSON-based, semi-structured, and variable across different cases and workflows, while staying inside the same PostgreSQL database as the business data.

This is a deliberate architecture choice:

- A single database is simpler to operate, back up, secure, and monitor.
- Agent context and business data can be updated in the same ACID transaction.
- Property-level isolation can be enforced consistently through PostgreSQL permissions and row-level security if needed later.
- JSONB provides enough flexibility for evolving agent workflows without introducing a second database.

The main trade-off is that extremely large conversation stores, such as millions of messages per active workspace, may eventually benefit from a dedicated document or event storage system. This is not relevant for the current stage, and PostgreSQL can still scale far with proper indexing, retention policies, and partitioning.

## PostgreSQL

PostgreSQL stores critical business data and acts as the system of record for relational entities.

PostgreSQL is used for:

- Users and authentication-related identities.
- Organizations and permissions.
- Property owners.
- Tenants.
- Properties.
- Leases.
- Payments.
- Service providers.
- Contractual and financial records.
- Critical audit logs.

PostgreSQL provides ACID transactions, relational integrity, foreign keys, uniqueness constraints, and reliable indexing for structured business data.

## Data Ownership

The platform separates operational agent memory from authoritative business data at the schema and table level, while keeping both in PostgreSQL.

| Data Type | Storage | Rationale |
| --- | --- | --- |
| Agent context | PostgreSQL JSONB | Flexible JSON memory with ACID guarantees |
| Conversations | PostgreSQL JSONB | Semi-structured history tied to business entities |
| Plans and milestones | PostgreSQL JSONB | Variable workflow structures in the same transaction scope |
| Tool traces | PostgreSQL JSONB | Loosely structured records with queryable metadata |
| Users | PostgreSQL | Identity and relational integrity |
| Properties | PostgreSQL | Structured business data |
| Leases | PostgreSQL | Contractual records requiring consistency |
| Payments | PostgreSQL | ACID guarantees and auditability |
| Service providers | PostgreSQL | Structured relationships with properties and owners |
| Critical audit logs | PostgreSQL | Reliable traceability |

## Stateless Execution Model

The backend does not rely on durable in-memory state. Each request follows the same execution model:

1. Receive an inbound event.
2. Load business data from PostgreSQL.
3. Load agent context from PostgreSQL JSONB.
4. Execute the agent workflow in memory.
5. Trigger external actions if required.
6. Persist the updated context, decisions, actions, and case state.
7. Return or dispatch the response.

This model allows the FastAPI backend to scale horizontally. Multiple backend instances can process events independently because all critical state is stored in persistent systems.

## Typical Request Flow

When a tenant reports an issue through WhatsApp:

1. WhatsApp sends the inbound message to a FastAPI webhook.
2. FastAPI identifies the sender, tenant, property, lease, and related case.
3. FastAPI loads authoritative business data from PostgreSQL.
4. FastAPI loads the relevant agent context from PostgreSQL JSONB.
5. The OpenAI agent analyzes the request and determines the next step.
6. The agent updates the active case, workflow plan, and milestones.
7. Tavily may be used if real-time web information is required.
8. If a paid intervention is needed, the owner is contacted for validation.
9. After validation, the agent coordinates with the tenant or a service provider.
10. Messages, actions, tool traces, and state transitions are persisted.
11. The React dashboard displays the updated operational state.

## Dashboard

The React dashboard provides supervision and BI capabilities for the platform.

It should expose:

- Active cases and their current status.
- Conversation timelines.
- Agent decisions and tool usage.
- Pending approvals.
- Provider coordination status.
- Operational metrics.
- Escalations requiring human review.

The dashboard is a supervision layer, not the source of truth. It reads from backend APIs that aggregate relational and JSONB data from PostgreSQL.

## External Integrations

The platform integrates with multiple external services:

- WhatsApp for tenant and owner communication.
- Email for service provider communication.
- Tavily for real-time web search.
- Gradium for speech-to-text and text-to-speech features.
- SLNG for voice model infrastructure.
- OpenAI API for agent reasoning and response generation.

External calls should be traced and persisted so the system can provide auditability, debugging context, and dashboard visibility.

## Technical Principles

The initial architecture is based on the following principles:

- PostgreSQL is the business source of truth.
- PostgreSQL JSONB is the operational memory of the agent.
- FastAPI orchestrates business workflows and integrations.
- The OpenAI API provides agentic reasoning and response generation.
- The backend remains stateless and horizontally scalable.
- External side effects are persisted and traceable.
- Workflow state is explicit, inspectable, and recoverable.
- The dashboard provides visibility, supervision, and BI over the platform activity.
