# Chris Prompt Evals

The prompt eval harness runs scenario folders under `scenarios/`.

Each scenario contains:

- `setup.yaml`: fake property context and relational facts.
- `transcript.yaml`: one or more incoming turns.
- `assertions.yaml`: deterministic checks the trace must satisfy.

Run:

```bash
python -m tests.prompt_evals.harness
```

or from the repository root:

```bash
make eval
```

The harness is intentionally offline for v1. LLM-as-judge graders are wired
through the `LLMProvider` interface, but default to deterministic heuristics so
prompt changes can be checked quickly and repeatedly.
