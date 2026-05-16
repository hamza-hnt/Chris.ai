# Chris.AI Backend

FastAPI backend for the Chris.AI bootstrap.

Main entry points:

- `app/main.py`: API application and health routes.
- `app/config.py`: environment-driven settings with fail-fast validation.
- `app/agent/`: context-injected Chris agent, prompts, tools, and providers.
- `app/domain/`: SQLAlchemy models, schemas, and scoped repositories.
- `app/orchestration/`: router, isolation guard, alerts, and intervention.
- `tests/prompt_evals/`: offline prompt evaluation harness and scenarios.

Run through the root Makefile:

```bash
make up
make migrate
make seed
make sample
make eval
```
