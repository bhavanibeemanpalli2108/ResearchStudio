"""Read-only scheduling evidence audit. No providers, Docker or program execution."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _critical(df: int) -> float:
    """Independently integrate Student-t density and invert CDF at 0.975."""
    factor = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))

    def cdf(x: float) -> float:
        steps = 4096
        width = x / steps

        def density(t: float) -> float:
            return factor * (1 + t * t / df) ** (-(df + 1) / 2)

        area = density(0) + density(x)
        area += sum((4 if i % 2 else 2) * density(i * width) for i in range(1, steps))
        return 0.5 + width * area / 3

    low, high = 0.0, 64.0
    for _ in range(48):
        middle = (low + high) / 2
        if cdf(middle) < 0.975:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def audit(workspace: Path, run_id: str) -> dict[str, Any]:
    require(bool(re.fullmatch(r"[a-f0-9]{32}", run_id)), "Invalid run ID")
    workspace = workspace.resolve()
    root = workspace / "artifacts"
    with sqlite3.connect((workspace / "platform.db").as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute(
            "select status,config,state,usage from rp_runs where id=?", (run_id,)
        ).fetchone()
        require(row is not None, "Run not found")
        status, config, state_text, usage_text = row
        state, usage = json.loads(state_text), json.loads(usage_text)
        artifacts = db.execute(
            "select id,relative_path,sha256,size_bytes from rp_artifacts where run_id=? order by id",
            (run_id,),
        ).fetchall()
        ledger = db.execute(
            "select provider,model,stage,status,input_tokens,output_tokens,estimated_cost from rp_model_usage where run_id=? order by id",
            (run_id,),
        ).fetchall()
    checked = []
    for artifact_id, relative, sha, size in artifacts:
        path = root / relative
        require(
            path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(),
            "Unsafe artifact path",
        )
        content = path.read_bytes()
        require(
            len(content) == size and hashlib.sha256(content).hexdigest() == sha,
            "Artifact hash/size mismatch",
        )
        checked.append({"id": artifact_id, "sha256": sha})
    cfg = state["experiment_config"]
    spec = cfg["spec"]
    require(
        spec["protocol"] == "scheduling_v1", "Audit supports retained scheduling_v1 evidence only"
    )
    executions = root / run_id / "execution"
    receipts = sorted(executions.glob("*/execution_result.json"))
    require(len(receipts) == 1, "Expected exactly one retained execution receipt")
    receipt_path = receipts[0]
    result = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(result["configuration"]["spec"] == spec, "Executed design differs from approved spec")
    require(result["spec_hash"] == digest(spec), "Specification hash mismatch")
    require(
        cfg["approval_digest"]
        == digest(
            {"prepared_digest": cfg["prepared_digest"], "dataset_sha256": result["dataset_sha256"]}
        ),
        "Final approval binding mismatch",
    )
    require(
        state["approval"]["approved"]
        and state["approval"]["approval_digest"] == cfg["approval_digest"],
        "Final approval not retained",
    )
    require(
        result["dataset_sha256"] == cfg["evaluation_validation"]["dataset_sha256"],
        "Dataset commitment mismatch",
    )
    for role in ("baseline", "candidate"):
        require(
            hashlib.sha256((receipt_path.parent / f"{role}.py").read_bytes()).hexdigest()
            == result[role]["code_sha256"],
            "Program source hash mismatch",
        )
    private = list((workspace / "private-evaluations").glob("*/private_fixture.json"))
    fixture = next(
        (
            json.loads(p.read_text(encoding="utf-8"))
            for p in private
            if json.loads(p.read_text(encoding="utf-8")).get("dataset_sha256")
            == result["dataset_sha256"]
        ),
        None,
    )
    if fixture is None:
        raise ValueError("Retained private fixture is missing")
    require(
        digest({k: v for k, v in fixture.items() if k != "dataset_sha256"})
        == result["dataset_sha256"],
        "Private fixture hash mismatch",
    )
    # Never export the private fixture salt or private labels into the audit output.
    inputs = json.loads((receipt_path.parent / "public_inputs.json").read_text(encoding="utf-8"))
    require(
        inputs == [case["public_input"] for case in fixture["cases"]],
        "Public/private fixture mismatch",
    )
    require([row["seed"] for row in inputs] == spec["seeds"], "Seed sequence mismatch")
    recomputed = []
    for data, observation in zip(inputs, result["per_seed"], strict=True):
        seed = data["seed"]
        require(observation["seed"] == seed, "Observation seed mismatch")
        durations = data["durations"]
        require(len(durations) == spec["dataset"]["job_count"], "Job count mismatch")
        require(
            all(
                type(n) is int
                and spec["dataset"]["duration_min"] <= n <= spec["dataset"]["duration_max"]
                for n in durations
            ),
            "Durations outside approved range",
        )
        metrics = {}
        for role in ("baseline", "candidate"):
            output = json.loads(
                (receipt_path.parent / f"{role}_{seed}.output.json").read_text(encoding="utf-8")
            )
            require(
                digest(output) == observation[f"{role}_output_sha256"],
                "Recorded output hash mismatch",
            )
            order = output["order"]
            require(sorted(order) == list(range(len(durations))), "Invalid schedule permutation")
            if role == "baseline":
                require(order == list(range(len(durations))), "Baseline is not FIFO")
            elapsed = total = 0
            for index in order:
                elapsed += durations[index]
                total += elapsed
            metrics[role] = total
            require(total == observation[role], "Retained measurement disagrees with output")
        require(digest(data) == observation["public_input_sha256"], "Input hash mismatch")
        improvement = metrics["baseline"] - metrics["candidate"]
        require(improvement == observation["improvement"], "Improvement mismatch")
        recomputed.append({"seed": seed, **metrics, "improvement": improvement})
    differences = [row["improvement"] for row in recomputed]
    mean = statistics.mean(differences)
    n = len(differences)
    deviation = statistics.stdev(differences)
    sem = deviation / math.sqrt(n)
    p_value = (
        sum(
            abs(sum(v * sign for v, sign in zip(differences, signs, strict=True)))
            >= abs(sum(differences))
            for signs in itertools.product((-1, 1), repeat=n)
        )
        / 2**n
    )
    critical = _critical(n - 1)
    lower, upper = mean - critical * sem, mean + critical * sem
    summary = result["statistical_summary"]
    for key, actual in {
        "baseline_mean": statistics.mean(row["baseline"] for row in recomputed),
        "candidate_mean": statistics.mean(row["candidate"] for row in recomputed),
        "paired_improvement_mean": mean,
        "paired_improvement_stddev": deviation,
        "paired_improvement_sem": sem,
        "paired_sign_flip_p_value": p_value,
    }.items():
        require(
            math.isclose(actual, summary[key], rel_tol=1e-9, abs_tol=1e-9),
            "Aggregate statistic mismatch: " + key,
        )
    require(
        math.isclose(lower, summary["paired_t_95_interval"]["lower"], abs_tol=1e-6)
        and math.isclose(upper, summary["paired_t_95_interval"]["upper"], abs_tol=1e-6),
        "Student-t interval mismatch",
    )
    require(
        result["meets_minimum_improvement"] == (mean > spec["evaluation"]["minimum_improvement"]),
        "Threshold mismatch",
    )
    require(result["metrics"] == state["results"]["metrics"], "State and receipt metric mismatch")
    require(
        result["per_seed"] == state["results"]["per_seed"]
        and summary == state["results"]["statistical_summary"],
        "State and receipt observation/statistics mismatch",
    )
    require(
        result["baseline"]["code_sha256"] == cfg["baseline_sha256"]
        and result["candidate"]["code_sha256"] == state["program"]["sha256"],
        "Source identity differs from persisted approval/program",
    )
    require(
        all(
            row[0] == state["provider"] and row[1] == state["model"] and row[3] == "completed"
            for row in ledger
        ),
        "Unexpected provider/model or unfinished ledger attempt",
    )
    require(
        len(ledger) == usage["calls"]
        and sum(row[4] for row in ledger) == usage["input_tokens"]
        and sum(row[5] for row in ledger) == usage["output_tokens"],
        "Ledger totals mismatch",
    )
    snapshot = digest(
        {
            "status": status,
            "config": config,
            "state": state_text,
            "usage": usage_text,
            "artifacts": artifacts,
            "ledger": ledger,
        }
    )
    return {
        "passed": True,
        "run_id": run_id,
        "status": status,
        "snapshot_sha256": snapshot,
        "verified_artifacts": checked,
        "approval_digest": cfg["approval_digest"],
        "per_seed": recomputed,
        "mean_improvement": mean,
        "sign_flip_p_value": p_value,
        "independently_integrated_t_critical": critical,
        "t_95_interval": [lower, upper],
        "retained_output_pairs": n,
        "programs_executed": 0,
        "provider_requests": 0,
        "ledger_calls": len(ledger),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.workspace, args.run_id), indent=2))


if __name__ == "__main__":
    main()
