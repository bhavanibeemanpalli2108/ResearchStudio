"""Shared transactional ModelUsage accounting; caller authorization stays separate."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select, text
from .database import ModelUsage, Run


class BudgetExceeded(RuntimeError):
    code = "budget_exhausted"


def usage_summary(rows: list[ModelUsage], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    observed_in = sum(row.input_tokens for row in rows if row.reported)
    observed_out = sum(row.output_tokens for row in rows if row.reported)
    reserved_in = sum(row.input_tokens for row in rows)
    reserved_out = sum(
        max(row.output_tokens, row.reserved_output_tokens)
        if row.status != "completed"
        else row.output_tokens
        for row in rows
    )
    result: dict[str, Any] = {
        "calls": len(rows),
        "calls_used": len(rows),
        "input_tokens": observed_in,
        "output_tokens": observed_out,
        "tokens": observed_in + observed_out,
        "total_tokens": observed_in + observed_out,
        "reserved_input_tokens": reserved_in,
        "reserved_output_tokens": reserved_out,
        "estimated_tokens": sum(
            row.input_tokens + row.output_tokens for row in rows if not row.reported
        ),
        "estimated_cost": sum(row.estimated_cost or 0 for row in rows)
        if rows and all(row.estimated_cost is not None for row in rows)
        else None,
        "usage_note": "Provider-reported tokens are shown separately from conservative reservations; unknown pricing is not billed as zero.",
    }
    if budget:
        result["remaining_calls"] = max(0, budget["max_llm_calls"] - len(rows))
        result["remaining_input_tokens"] = max(0, budget["max_input_tokens"] - reserved_in)
        result["remaining_output_tokens"] = max(0, budget["max_output_tokens"] - reserved_out)
        result["budget"] = budget
    return result


def refresh_usage(session: Any, run: Run) -> dict[str, Any]:
    rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == run.id)))
    run.usage = {
        **usage_summary(rows, run.config.get("budgets")),
        "runtime_seconds": run.usage.get("runtime_seconds", 0),
    }
    return run.usage


def accounting_lock(session: Any) -> None:
    if session.bind.dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))
    elif session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(7213921)"))
    else:
        raise BudgetExceeded("Unsupported transactional accounting backend")


def reserve_model_call(
    session: Any,
    run: Run,
    *,
    daily_limit: int,
    provider: str,
    model: str,
    stage: str,
    predicted: int,
    maximum: int,
) -> ModelUsage:
    """Caller holds accounting_lock and validates its own lease/grant in this transaction."""
    budgets = run.config["budgets"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = (
        session.scalar(
            select(func.count()).select_from(ModelUsage).where(ModelUsage.created_at >= today)
        )
        or 0
    )
    usage = refresh_usage(session, run)
    if daily >= daily_limit:
        raise BudgetExceeded("The configured daily API-call budget is exhausted")
    if usage["calls"] >= budgets["max_llm_calls"]:
        raise BudgetExceeded("This run's model-call budget is exhausted")
    if usage["reserved_input_tokens"] + predicted > budgets["max_input_tokens"]:
        raise BudgetExceeded("This run's input-token reservation budget is exhausted")
    if usage["reserved_output_tokens"] + maximum > budgets["max_output_tokens"]:
        raise BudgetExceeded("This run's output-token reservation budget is exhausted")
    if budgets.get("monetary_cap_usd") is not None and provider not in {"mock", "ollama"}:
        raise BudgetExceeded(
            "A monetary cap requires verified pricing; unknown-cost API requests are blocked. Use request/token limits or a local model."
        )
    row = ModelUsage(
        run_id=run.id,
        provider=provider,
        model=model,
        stage=stage,
        input_tokens=predicted,
        output_tokens=0,
        reserved_output_tokens=maximum,
        status="reserved",
        reported=False,
        estimated_cost=0.0 if provider == "mock" else None,
    )
    session.add(row)
    session.flush()
    refresh_usage(session, run)
    return row
