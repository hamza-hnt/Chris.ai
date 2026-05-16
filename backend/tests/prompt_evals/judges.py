from dataclasses import dataclass
from typing import Any

from app.agent.providers.base import LLMProvider, LLMMessage


@dataclass
class JudgeResult:
    name: str
    passed: bool
    detail: str


def deterministic_judges(trace: dict[str, Any], assertions: dict[str, Any]) -> list[JudgeResult]:
    return [
        _plan_first(trace),
        _must_call(trace, assertions.get("must_call", [])),
        _must_not_call(trace, assertions.get("must_not_call", [])),
        _forbidden_text(trace, assertions.get("forbidden_text", [])),
        _receipt_guard(trace, assertions),
        _document_fact_guard(trace, assertions),
        _question_guard(trace),
    ]


def _plan_first(trace: dict[str, Any]) -> JudgeResult:
    for turn in trace["turns"]:
        calls = turn["tool_calls"]
        if not calls or calls[0]["name"] != "plan.review_or_create":
            return JudgeResult("plan_first", False, "First tool was not plan.review_or_create.")
    return JudgeResult("plan_first", True, "Every turn reviewed or created a plan first.")


def _must_call(trace: dict[str, Any], required: list[str]) -> JudgeResult:
    names = _tool_names(trace)
    missing = [name for name in required if name not in names]
    if missing:
        return JudgeResult("must_call", False, "Missing tool calls: " + ", ".join(missing))
    return JudgeResult("must_call", True, "Required tool calls were present.")


def _must_not_call(trace: dict[str, Any], forbidden: list[str]) -> JudgeResult:
    names = _tool_names(trace)
    found = [name for name in forbidden if name in names]
    if found:
        return JudgeResult("must_not_call", False, "Forbidden tool calls: " + ", ".join(found))
    return JudgeResult("must_not_call", True, "Forbidden tool calls were absent.")


def _forbidden_text(trace: dict[str, Any], forbidden: list[str]) -> JudgeResult:
    serialized = str(trace).lower()
    found = [text for text in forbidden if text.lower() in serialized]
    if found:
        return JudgeResult("forbidden_text", False, "Forbidden text appeared: " + ", ".join(found))
    return JudgeResult("forbidden_text", True, "Forbidden text did not appear.")


def _receipt_guard(trace: dict[str, Any], assertions: dict[str, Any]) -> JudgeResult:
    names = _tool_names(trace)
    if assertions.get("payment_confirmed") is False and "documents.create_receipt" in names:
        return JudgeResult("receipt_guard", False, "Receipt was created without confirmed payment.")
    return JudgeResult("receipt_guard", True, "Receipt boundary held.")


def _document_fact_guard(trace: dict[str, Any], assertions: dict[str, Any]) -> JudgeResult:
    if not assertions.get("document_facts_from_relational", False):
        return JudgeResult("document_fact_guard", True, "No document fact assertion requested.")
    for turn in trace["turns"]:
        for call in turn["tool_calls"]:
            if call["name"].startswith("documents."):
                payload = call.get("output", {}).get("document", {}).get("payload", {})
                if payload.get("source") not in {"relational", "relational_stub"}:
                    return JudgeResult(
                        "document_fact_guard",
                        False,
                        "Document payload did not mark relational source.",
                    )
    return JudgeResult("document_fact_guard", True, "Document facts came from relational sources.")


def _question_guard(trace: dict[str, Any]) -> JudgeResult:
    for turn in trace["turns"]:
        for call in turn["tool_calls"]:
            if call["name"] == "messaging.ask_question":
                body = call["arguments"]["body"]
                if body.count("?") != 1:
                    return JudgeResult("one_question", False, f"Question count failed: {body}")
    return JudgeResult("one_question", True, "Questions were singular.")


class LLMJudge:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider

    def no_delegation_of_work(self, trace: dict[str, Any]) -> JudgeResult:
        text = str(trace).lower()
        forbidden = [
            "please find a contractor",
            "can you contact the provider",
            "please coordinate",
            "ask the tenant to choose",
        ]
        found = [phrase for phrase in forbidden if phrase in text]
        if found:
            return JudgeResult("llm_no_delegation", False, "Delegation phrase found: " + found[0])
        if self._provider is None:
            return JudgeResult(
                "llm_no_delegation",
                True,
                "Heuristic judge passed; no provider configured.",
            )

        response = self._provider.complete(
            [
                LLMMessage(
                    role="system",
                    content=(
                        "Judge whether Chris delegated operational work to a human. "
                        "Return only PASS or FAIL."
                    ),
                ),
                LLMMessage(role="user", content=str(trace)),
            ],
            tools=[],
            tool_budget=0,
        )
        passed = (response.content or "").strip().upper().startswith("PASS")
        return JudgeResult("llm_no_delegation", passed, response.content or "")


def _tool_names(trace: dict[str, Any]) -> list[str]:
    return [call["name"] for turn in trace["turns"] for call in turn["tool_calls"]]
