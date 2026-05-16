# Architecture

Chris.AI uses stateless FastAPI workers, a context-injected agent, and a single
PostgreSQL database for both relational business data and JSONB agent memory.

```mermaid
flowchart TB
    subgraph Channels
        WA[WhatsApp]
        TW[Twilio Sandbox]
        EM[Email]
        VOX[WhatsApp Voice Note]
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
        LLM[OpenAI Agent Runtime]
        TAV[Tavily]
        SLNG[SLNG Unified STT]
    end

    WA --> TW
    VOX --> TW
    TW --> WH
    TW --> SLNG
    SLNG --> WH
    EM --> WH
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
    participant OpenAI
    participant Tavily
    participant SLNG

    Channel->>API: Incoming text message
    Channel->>SLNG: Voice media is transcribed when present
    SLNG-->>API: Transcript
    API->>Router: Resolve sender contact
    Router->>DB: Lookup contact and lease
    DB-->>Router: property_id and sender_role
    Router->>DB: Load scoped context
    DB-->>Agent: One-property context bundle
    Agent->>OpenAI: Reason over context and current turn
    Agent->>Tools: plan.review_or_create
    Agent->>Tools: Allowed operational actions
    Tools->>Tavily: Provider or web search when needed
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

## Hackathon Integrations

- OpenAI: agentic reasoning and response generation through the provider
  abstraction and the OpenAI agent runtime.
- Tavily: live web search for provider discovery near the scoped property
  address.
- SLNG: speech-to-text for WhatsApp voice notes using the Unified STT endpoint
  before routing the transcript through the normal agent flow.

## Read Next

- [Single Agent](03-single-agent.md)
- [Data Model](05-data-model.md)
- [Tool Contracts](07-tool-contracts.md)
