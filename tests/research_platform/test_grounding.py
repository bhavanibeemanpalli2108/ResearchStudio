"""Selected-source context and immutable approval association regressions."""

from copy import deepcopy
import json
import sqlite3
import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from src.research_platform.experiment_contract import canonical_hash
from src.research_platform.grounding import (
    source_context,
    grounding_manifest,
    verify_grounding,
    approval_binding,
    validate_citations,
)
from src.research_platform.workflow import create_workflow
from src.research_platform.preparation import TaskPreparationError
from test_native_workflow import NativeServices, state, CONFIG


def selected():
    return [
        {
            "id": f"https://doi.org/10.1000/source{i}",
            "selection_id": str(i) * 64,
            "title": f"Source {i}",
            "authors": ["Recorded Author"],
            "year": 2022,
            "abstract": "Genuine provided abstract excerpt." if i % 2 else None,
            "abstract_source": "OpenAlex" if i % 2 else None,
            "provenance": [{"source": "OpenAlex", "source_id": f"https://openalex.org/W{i}"}],
            "unsupported_finding": "Do not pass this field to the model",
        }
        for i in range(1, 6)
    ]


def grounded_state():
    papers = selected()
    hypothesis = "A bounded synthetic candidate may improve the approved reference."
    s = {
        "config": {"selected_literature": papers},
        "selected_idea": {
            "id": "idea-one",
            "hypothesis": hypothesis,
            "citation_ids": [papers[0]["id"]],
            "literature_rationale": "AI interpretation of supplied metadata, not verified source findings.",
        },
    }
    manifest = grounding_manifest(s)
    s["experiment_config"] = {
        "spec": {"hypothesis": hypothesis},
        "grounding_manifest": manifest,
        "grounding_sha256": canonical_hash(manifest),
    }
    return s


def test_context_preserves_all_selected_identifiers_and_only_available_source_fields():
    sources = source_context(grounded_state())
    assert len(sources) == 5
    assert sources[0]["abstract"] == "Genuine provided abstract excerpt."
    assert "abstract" not in sources[1]
    assert "unsupported_finding" not in json.dumps(sources)
    assert sources[4]["id"] == "https://doi.org/10.1000/source5"


@pytest.mark.parametrize(
    "citations", [[], ["https://doi.org/10.9999/invented"], ["https://doi.org/10.1000/source1"] * 2]
)
def test_missing_fabricated_or_duplicate_citations_are_rejected(citations):
    with pytest.raises(ValueError, match="citation_ids"):
        validate_citations([{"citation_ids": citations}], grounded_state())


@pytest.mark.parametrize(
    "mutation", ["source", "hypothesis", "citation", "manifest", "approved_spec"]
)
def test_source_hypothesis_and_citation_changes_invalidate_prepared_binding(mutation):
    s = grounded_state()
    assert verify_grounding(s)
    if mutation == "source":
        s["config"]["selected_literature"][0]["abstract"] = "Changed excerpt"
    elif mutation == "hypothesis":
        s["selected_idea"]["hypothesis"] = "An unrelated hypothesis"
    elif mutation == "citation":
        s["selected_idea"]["citation_ids"] = [s["config"]["selected_literature"][1]["id"]]
    elif mutation == "approved_spec":
        s["experiment_config"]["spec"]["hypothesis"] = "An unrelated approved claim"
    else:
        s["experiment_config"]["grounding_manifest"]["literature_rationale"] = (
            "Changed interpretation"
        )
    with pytest.raises(ValueError):
        verify_grounding(s)


def test_new_binding_includes_grounding_but_legacy_approval_is_unchanged():
    s = grounded_state()
    old = canonical_hash({"prepared_digest": "p", "dataset_sha256": "d"})
    assert approval_binding("p", "d", {}) == old
    bound = approval_binding("p", "d", s["experiment_config"])
    assert bound != old
    changed = deepcopy(s["experiment_config"])
    changed["grounding_sha256"] = "f" * 64
    assert approval_binding("p", "d", changed) != bound


def test_planning_receives_selected_abstracts_before_first_human_gate():
    class WithReferences(NativeServices):
        def model(self, stage, prompt, **kwargs):
            value = json.loads(super().model(stage, prompt, **kwargs))
            if stage == "planning":
                context = json.loads(prompt.split("Research context:\n", 1)[1])
                assert len(context["literature"]) == 5
                assert context["literature"][0]["abstract"] == "Genuine provided abstract excerpt."
                assert "unsupported_finding" not in prompt
                for hypothesis in value["hypotheses"]:
                    hypothesis["citation_ids"] = [selected()[0]["id"]]
            return json.dumps(value)

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    try:
        graph = create_workflow(WithReferences(), SqliteSaver(connection))
        graph.invoke(state(selected_literature=selected()), CONFIG)
        snapshot = graph.get_state(CONFIG)
        assert snapshot.next == ("research_plan",)
        assert snapshot.values["plan"]["hypotheses"][0]["citation_ids"] == [selected()[0]["id"]]
    finally:
        connection.close()


def test_unreferenced_plan_stops_after_bounded_repair_before_approval():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    services = NativeServices()
    try:
        graph = create_workflow(services, SqliteSaver(connection))
        with pytest.raises(TaskPreparationError):
            graph.invoke(state(selected_literature=selected()), CONFIG)
        assert services.calls.count("planning") == 2
        assert not services.executions
    finally:
        connection.close()
