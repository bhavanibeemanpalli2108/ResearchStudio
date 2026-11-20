"""An explicit boundary around the existing upstream scientist workflow."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .execution import CapabilityError, DockerExecutor, ExecutionCancelled, write_result

REPO_ROOT = Path(__file__).resolve().parents[2]
FULL_MODE_REASON = (
    "Full upstream runs require an isolated Linux worker with its own Docker daemon, "
    "credential proxy, and enforceable provider budget. The original agsci pipeline "
    "launches unrestricted coding agents and forwards credentials; this web service "
    "does not launch it on the host or mount the host Docker socket. Use the reviewed "
    "upstream CLI independently after provisioning that worker."
)


class ScientistAdapter:
    supported_phases = ("investigation",)

    def __init__(
        self,
        *,
        executor: DockerExecutor | None = None,
        environ: Mapping[str, str] | None = None,
        results_root: str | Path | None = None,
    ):
        self.environ = environ if environ is not None else os.environ
        self.executor = executor or DockerExecutor(
            image=self.environ.get("RESEARCH_CPU_IMAGE", "python:3.12-slim")
        )
        self.results_root = Path(
            results_root
            or self.environ.get("RESEARCH_UPSTREAM_RESULTS", str(REPO_ROOT / "results"))
        ).resolve()

    def capabilities(self) -> dict[str, Any]:
        cpu = self.executor.capabilities()
        return {
            "demo": {
                "ready": True,
                "description": "Deterministic fixture; no scientific evidence.",
            },
            "free": cpu,
            "full": {
                "ready": False,
                "reason": FULL_MODE_REASON,
                "agsci_cli": bool(shutil.which("agsci")),
                "bash": bool(shutil.which("bash")),
                "windows_requires_wsl": os.name == "nt",
                "upstream_task_available": (REPO_ROOT / "examples/circpack/task.md").is_file(),
                "command_preview": self.upstream_command_preview(),
                "existing_run_import": True,
            },
            "supported_phases": list(self.supported_phases),
        }

    @staticmethod
    def upstream_command_preview(*, model: str | None = None) -> list[str]:
        # Only known fixed task and fixed bounds; no arbitrary Hydra overrides,
        # paths, native execution, credentials, shell evaluation, or agent CLI.
        command = [
            "agsci",
            "run",
            "examples/circpack",
            "--dry-run",
            "container.enabled=true",
            "container.network=none",
            "container.env_file=",
            "investigation.execution.max_idea_cycles=1",
            "ablations.execution.num_replications=1",
            "ablations.execution.max_evals_per_variant=1",
            "posthoc.execution.max_selected_analyses=1",
        ]
        if model is not None:
            from .providers import ModelUnavailableError
            import re

            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
                raise ModelUnavailableError("Invalid upstream model identifier.")
            command.extend(["agent.name=gemini", "agent.model=" + model])
        return command

    def list_existing_runs(self) -> list[dict[str, Any]]:
        """Inventory only the documented results/<task>/<agent>/<run> envelope."""
        if not self.results_root.is_dir():
            return []
        runs: list[dict[str, Any]] = []
        for path in sorted(self.results_root.glob("*/*/*")):
            if len(runs) >= 500:
                break
            if (
                path.is_symlink()
                or not path.is_dir()
                or not path.resolve().is_relative_to(self.results_root)
            ):
                continue
            relative = path.relative_to(self.results_root)
            if any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", part) for part in relative.parts):
                continue
            if (path / "investigation").is_dir():
                runs.append(
                    {
                        "id": relative.as_posix(),
                        "task": relative.parts[0],
                        "agent": relative.parts[1],
                        "run_id": relative.parts[2],
                        "source": "upstream_agsci",
                    }
                )
        return runs

    def import_existing_run(self, upstream_id: str) -> dict[str, Any]:
        """Reuse upstream inspector normalization, returning only numeric evidence.

        The administrator configures the results root; API callers choose an
        inventory identifier, never a filesystem path. No source is imported
        from the result directory and no candidate program is executed.
        """
        inventory = {item["id"]: item for item in self.list_existing_runs()}
        if upstream_id not in inventory:
            raise CapabilityError("Upstream run identifier is unavailable.")
        envelope = (self.results_root / upstream_id).resolve()
        if not envelope.is_relative_to(self.results_root):
            raise CapabilityError("Upstream run escaped its configured results root.")
        # Upstream inspector assumes trusted local directories. Validate that
        # bounded assumption before invoking it in the web service.
        count = 0
        metadata_bytes = 0
        for base, directories, files in os.walk(envelope, followlinks=False):
            for name in directories + files:
                child = Path(base) / name
                count += 1
                if (
                    count > 10000
                    or child.is_symlink()
                    or not child.resolve().is_relative_to(envelope)
                ):
                    raise CapabilityError(
                        "Upstream run contains unsafe links or exceeds the import limit."
                    )
                if child.is_file() and child.suffix in {".json", ".jsonl", ".log"}:
                    size = child.stat().st_size
                    metadata_bytes += size
                    if size > 2 * 1024 * 1024 or metadata_bytes > 16 * 1024 * 1024:
                        raise CapabilityError("Upstream metadata exceeds the bounded import limit.")
        from apps.run_inspector.backend.discovery import discover_single_run

        metadata = inventory[upstream_id]
        run = discover_single_run(
            envelope / "investigation", upstream_id, metadata["task"], metadata["agent"]
        )
        if run is None:
            raise CapabilityError("Upstream investigation contains no recognized result markers.")
        evaluations = []
        for worker in run.workers:
            for idea in worker.ideas:
                for program in idea.programs:
                    numeric = {
                        key: value
                        for key, value in (program.metrics or {}).items()
                        if isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                    }
                    evaluations.append(
                        {
                            "worker": worker.worker_index,
                            "program": program.program_idx,
                            "metrics": numeric,
                            "correct": (program.correct or {}).get("correct") is True,
                        }
                    )
        score = run.best_combined_score
        if score is not None and not math.isfinite(score):
            score = None
        return {
            "status": "imported",
            "source": "upstream_agsci",
            "demo": False,
            "upstream_id": upstream_id,
            "task": metadata["task"],
            "agent": metadata["agent"],
            "metrics": {"best_combined_score": score, "evaluations": evaluations},
            "artifacts": [
                name
                for name in (
                    "paper/paper.pdf",
                    "paper/paper.tex",
                    "investigation/best_program_manifest.json",
                )
                if (envelope / name).is_file()
            ],
            "logs": [
                "Read existing upstream artifacts through the original run inspector; no program was executed."
            ],
            "limitations": [
                "Imported numeric metadata is reported as upstream evidence; this service has not rerun or independently verified it."
            ],
        }

    def execute(
        self,
        run_id: str,
        profile: str,
        configuration: dict[str, Any],
        workdir: str | Path,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if profile == "free":
            raise CapabilityError(
                "Free research requires protocol-v2 generated programs in Docker; the fixed benchmark is retired from genuine execution."
            )
        if profile not in {"demo", "free", "full"}:
            raise CapabilityError("Unknown execution profile.")
        if profile == "full":
            raise CapabilityError(FULL_MODE_REASON)
        if cancel_check and cancel_check():
            raise ExecutionCancelled("Execution was cancelled.")
        directory = Path(workdir).resolve()
        receipt = directory / "execution_result.json"
        # The caller owns one iteration-specific directory. Replay returns the
        # already measured result rather than silently repeating an experiment.
        if receipt.is_file():
            result = json.loads(receipt.read_text(encoding="utf-8"))
            if result.get("run_id") != run_id or result.get("profile") != profile:
                raise CapabilityError("Execution receipt belongs to another run or profile.")
            return result
        if profile == "demo":
            metrics = {
                "baseline": {"sum_radii": 26 / 14, "valid": True, "circles": 26},
                "candidate": {"sum_radii": 26 / 12, "valid": True, "circles": 26},
                "improvement": 26 / 12 - 26 / 14,
                "fixture": True,
            }
            source = "deterministic_demo_fixture"
            logs = ["DEMO FIXTURE: these numbers are prerecorded values, not measured evidence."]
        else:
            metrics = self.executor.execute(cancel_check=cancel_check)
            source = "curated_square_grid_packing_v1"
            logs = [
                "Executed the fixed reviewed square-grid circle-packing comparison in isolated Docker.",
                "No LLM code was executed. This is a constrained CPU study; arbitrary research prompts do not change the executable.",
            ]
        result = {
            "run_id": run_id,
            "profile": profile,
            "status": "completed",
            "metrics": metrics,
            "configuration": {
                "program": "curated_square_grid_packing_v1",
                "circles": 26,
                "baseline_grid": [7, 4],
                "candidate_grid": [6, 5],
                "requested_plan": configuration,
            },
            "artifacts": ["execution_result.json"],
            "logs": logs,
            "demo": profile == "demo",
            "source": source,
            "limitations": [
                "This fixed n=26 circle-packing benchmark compares two reviewed grid configurations and checks boundaries and pairwise separation. The original upstream NumPy evaluator is not run.",
                "Research prompts do not change the fixed executable; results do not establish conclusions for unrelated questions.",
                "The adapter currently supports the investigation phase only.",
            ],
        }
        write_result(receipt, result)
        return result
