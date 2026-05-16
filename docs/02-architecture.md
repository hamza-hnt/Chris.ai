# Architecture

Chris.AI uses stateless FastAPI workers, a context-injected agent, and a single
PostgreSQL database for both relational business data and JSONB agent memory.

```mermaid
flowchart TB
    subgraph Channels
        WA[WhatsApp]
        EM[Email]
    VOX[SLNG Voice]
    end

    subgraph Supervisor
        DASH[React Dashboard]
    end

    subgraph Backend["FastAPI Backend"]
        WH[Webhooks]
        ROUTER[Router]
        CTX[Context Loader]
        AGENT[Chris Agent]
        TOOLS[Tool Executor]
        ALERTS[Alert Engine]
        INTV[Intervention]
    end

    subgraph Storage
        PG[(PostgreSQL)]
    end

    subgraph External
        LLM[LLM Provider]
        TAV[Tavily]
    end

    WA --> WH
    EM --> WH
    VOX --> WH
    WH --> ROUTER
    ROUTER --> CTX
    CTX --> PG
    CTX --> AGENT
    AGENT --> LLM
    AGENT --> TOOLS
    TOOLS --> TAV
    TOOLS --> PG
    PG --> ALERTS
    ALERTS --> DASH
    DASH --> INTV
    INTV --> AGENT
```

## Per-Turn Flow

```mermaid
sequenceDiagram
    participant Channel
    participant API
    participant Router
    participant DB
    participant Agent
    participant Tools

    Channel->>API: Incoming message
    API->>Router: Resolve sender contact
    Router->>DB: Lookup contact and lease
    DB-->>Router: property_id and sender_role
    Router->>DB: Load scoped context
    DB-->>Agent: One-property context bundle
    Agent->>Tools: plan.review_or_create
    Agent->>Tools: Allowed operational actions
    Tools->>DB: Scoped writes and traces
    Agent-->>API: Outgoing messages
```

FastAPI workers keep no critical state in memory. Any worker can serve any turn
because PostgreSQL is the source of truth for both business facts and agent
memory.

## Provider Abstraction

Agent code depends on `LLMProvider`, not directly on any SDK. OpenAI is the
default provider. Anthropic is wired as a stub so provider selection is a config
change once implemented.

## Read Next

- [Single Agent](03-single-agent.md)
- [Data Model](05-data-model.md)
- [Tool Contracts](07-tool-contracts.md)
