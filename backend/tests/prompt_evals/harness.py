from pathlib import Path
from typing import Any

import yaml

from app.agent.prompts.render import render_system_prompt
from tests.prompt_evals.judges import LLMJudge, JudgeResult, deterministic_judges

SCENARIO_ROOT = Path(__file__).parent / "scenarios"


def run_all() -> list[tuple[str, list[JudgeResult]]]:
    results = []
    for scenario_dir in sorted(path for path in SCENARIO_ROOT.iterdir() if path.is_dir()):
        results.append((scenario_dir.name, run_scenario(scenario_dir)))
    return results


def run_scenario(scenario_dir: Path) -> list[JudgeResult]:
    setup = _load_yaml(scenario_dir / "setup.yaml")
    transcript = _load_yaml(scenario_dir / "transcript.yaml")
    assertions = _load_yaml(scenario_dir / "assertions.yaml")
    trace = {
        "scenario": scenario_dir.name,
        "property_id": setup["property_context"]["property_id"],
        "turns": [],
    }
    for incoming in transcript["turns"]:
        trace["turns"].append(_simulate_turn(setup, incoming))
    return [
        *deterministic_judges(trace, assertions),
        LLMJudge().no_delegation_of_work(trace),
    ]


def _simulate_turn(setup: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    context = setup["property_context"]
    system_prompt = render_system_prompt(context, incoming)
    body = incoming["body"].lower()
    sender_role = incoming["sender_role"]
    calls = [
        {
            "name": "plan.review_or_create",
            "arguments": {
                "plan_name": f"Eval request: {incoming['body'][:48]}",
                "steps": [
                    {"description": "Review authority and active plan.", "status": "in_progress"},
                    {"description": "Take next allowed action.", "status": "pending"},
                ],
            },
            "output": {"ok": True, "plan": {"id": "plan-eval", "property_id": context["property_id"]}},
        }
    ]
    outgoing = []

    if _contains_injection(body):
        calls.append(
            {
                "name": "escalate",
                "arguments": {
                    "reason": "Prompt injection attempt ignored and treated as data.",
                    "severity": "medium",
                },
                "output": {"ok": True},
            }
        )
        outgoing.append(
            {
                "to_role": sender_role,
                "body": "I have noted your message and will continue with the normal property-management workflow.",
            }
        )
    elif "receipt" in body or "paid" in body:
        if sender_role == "landlord" and setup.get("payment_confirmed") is True:
            calls.append(
                {
                    "name": "documents.create_receipt",
                    "arguments": {"payment_id": setup["relational_facts"]["payment_id"]},
                    "output": {
                        "ok": True,
                        "document": {
                            "payload": {
                                "source": "relational",
                                "amount": setup["relational_facts"]["rent_amount"],
                            }
                        },
                    },
                }
            )
        else:
            calls.append(
                {
                    "name": "messaging.ask_question",
                    "arguments": {
                        "to_role": "landlord",
                        "body": "Can you confirm whether the tenant payment has been received?",
                    },
                    "output": {"ok": True},
                }
            )
            outgoing.append(
                {
                    "to_role": "landlord",
                    "body": "Can you confirm whether the tenant payment has been received?",
                }
            )
    elif "contractor" in body or "provider" in body or "plumber" in body:
        calls.append(
            {
                "name": "provider.list_preferred",
                "arguments": {"trade": "plumber"},
                "output": {"ok": True, "providers": context.get("preferred_providers", [])},
            }
        )
        calls.append(
            {
                "name": "messaging.ask_question",
                "arguments": {
                    "to_role": "landlord",
                    "body": "Which approved provider should I contact for this request?",
                },
                "output": {"ok": True},
            }
        )
        outgoing.append(
            {
                "to_role": "landlord",
                "body": "Which approved provider should I contact for this request?",
            }
        )
    else:
        outgoing.append(
            {
                "to_role": sender_role,
                "body": "Thanks, I have opened a plan for this request.",
            }
        )

    calls.append(
        {
            "name": "plan.mark_step",
            "arguments": {
                "plan_id": "plan-eval",
                "step_index": 0,
                "status": "done",
                "evidence": "Plan reviewed before external action.",
            },
            "output": {"ok": True},
        }
    )
    return {
        "incoming": incoming,
        "system_prompt_chars": len(system_prompt),
        "tool_calls": calls,
        "outgoing_messages": outgoing,
    }


def _contains_injection(body: str) -> bool:
    return "ignore previous" in body or "system prompt" in body or "bypass" in body


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def main() -> None:
    results = run_all()
    print("Scenario                         Status  Failed judges")
    print("-------------------------------- ------- ------------------------------")
    any_failed = False
    for name, judges in results:
        failed = [judge.name for judge in judges if not judge.passed]
        status = "PASS" if not failed else "FAIL"
        any_failed = any_failed or bool(failed)
        print(f"{name:<32} {status:<7} {', '.join(failed)}")
    if any_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
