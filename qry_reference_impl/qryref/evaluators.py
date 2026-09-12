"""Semantic-evaluator contracts and evaluation-key validation (spec 26).

Implements the Phase 6 surface of the v0.3.0 design draft:

* the evaluator contract records of 26.2 (registered input/output
  schemas, determinism, guarantee, model and policy identity, rewrite
  class, tuple-preservation and tuple-generation flags, and the
  evaluator-specific evaluation-key fields);
* the deterministic evaluation-key contract of 26.5 with the Q15
  decision: universally mandatory key fields (evaluator contract ID,
  source commit, input digests, the four policies, output schema) plus
  the evaluator-specific fields declared by the contract;
* materialized evaluator mode (26.3, 26.7): an assessment source
  carries the immutable assessment relation plus the recorded
  evaluation (actor, model, configuration, key, result object);
* the equality prohibition (26.8, QINV-04): a semantic-equivalence
  evaluator used as exact `=`/`!=` is a forgery;
* the inline-evaluator barrier (26.4): an inline evaluator is not
  duplicable by default (QV6-05), and a duplicated stochastic call
  breaks evaluation-identity equivalence (QV7-03 when the query
  requires that dimension, 27);
* claim-based checks (wired into claim_semantic_diagnostics): a
  heuristic contribution to an exact certified side (QV5-08) and a
  tuple-generating evaluator modeled as a tuple-preserving Select
  (QV5-09, QV6-07).

QV6-06 (committed semantic results are materialized or otherwise
auditable) is satisfied by construction for assessment sources: the
record must be complete (QV6-02) and immutable (QV6-03).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .diagnostics import Diagnostic, diag

# ---------------------------------------------------------------------------
# Evaluation-key contract (26.5, Q15 decision)

# Universally mandatory in every evaluation key (Q15): evaluator
# contract ID, source commit, input object/tuple digests, the four
# policies, and the output schema.
UNIVERSAL_KEY_FIELDS = (
    "evaluator_id",
    "source_commit",
    "input_digests",
    "visibility_policy",
    "authorization_policy",
    "leakage_policy",
    "assessment_policy",
    "output_schema",
)

# 26.7 materialization obligation: the fields a recorded evaluation
# must carry (actor identity; model identity and version; evaluator
# contract; evaluation key; configuration digest; source commit;
# result object; the four policies; output schema).
ASSESSMENT_REQUIRED_FIELDS = (
    "created_by",
    "model_id",
    "model_version",
    "configuration_digest",
    "source_commit",
    "input_digests",
    "visibility_policy",
    "authorization_policy",
    "leakage_policy",
    "assessment_policy",
    "output_schema",
)


def _seeded_digest(kind: str, name: str) -> str:
    """A stable content reference for a registered contract artifact.

    The reference is derived from the artifact's identity so the
    registry is deterministic and reproducible from the repo.
    """
    return kind + ":" + hashlib.sha256(name.encode("utf-8")).hexdigest()


def _key_fields(*extra: str) -> tuple[str, ...]:
    return extra


# Evaluator-specific key fields (SHOULD, 26.5): model identity and
# version, configuration digest, prompt-template digest, tool-policy
# digest, random seed or sampling identity, external service version.
STOCHASTIC_KEY_FIELDS = _key_fields(
    "model_id", "model_version", "configuration_digest",
    "prompt_template_digest", "tool_policy_digest",
    "random_seed", "service_version",
)


def _contract(
    slug: str,
    determinism: str,
    *,
    semantic_equivalence: bool = False,
    generates_tuples: bool = False,
    key_fields: tuple[str, ...] = (),
    model_id: str = "sol/classifier/positive",
) -> dict[str, Any]:
    return {
        "evaluator_id": f"sol:evaluator/{slug}/v1",
        "input_schema": _seeded_digest("object", f"sol:evaluator/{slug}/v1:input"),
        "output_schema": _seeded_digest("object", f"sol:evaluator/{slug}/v1:output"),
        "determinism": determinism,
        "guarantee": "heuristic",
        "model_actor": f"agent:{slug}_001",
        "model_id": model_id,
        "model_version": "2026-07-01",
        "configuration_digest": _seeded_digest("digest", f"sol:evaluator/{slug}/v1:config"),
        "monotonicity": "unknown",
        "side_effects": ["materializes_assessment"] if determinism == "stochastic" else [],
        "rewrite_class": "barrier",
        "tuple_preserving": not generates_tuples,
        "generates_tuples": generates_tuples,
        "semantic_equivalence": semantic_equivalence,
        "evaluation_key_schema": list(key_fields),
    }


# ---------------------------------------------------------------------------
# Registered evaluator contracts (26.2)

EVALUATOR_CONTRACTS: dict[str, dict[str, Any]] = {
    # Deterministic positive classifier: the Phase 1/4/5 corpus
    # evaluator (QGOLD-013/014, QPATH-022). Deterministic evaluators
    # resolve repeated invocations to the same result by definition,
    # so no evaluation key is required (QINV-13).
    "sol:evaluator/positive_classifier/v1": _contract(
        "positive_classifier", "deterministic"),

    # Stochastic vector-similarity evaluator (QPATH-002): a
    # semantic-equivalence relation that MUST NOT be interpreted as
    # exact `=` (26.8, QINV-04).
    "sol:evaluator/vector_similarity/v1": _contract(
        "vector_similarity", "stochastic",
        semantic_equivalence=True,
        key_fields=STOCHASTIC_KEY_FIELDS,
        model_id="provider/embedding-model"),

    # Stochastic semantic-equivalence evaluator (spec 26.2/26.5
    # example; QGOLD-009 materialized mode, QPATH-024/025 key
    # pathologies).
    "sol:evaluator/semantic_equivalence/v1": _contract(
        "semantic_equivalence", "stochastic",
        semantic_equivalence=True,
        key_fields=STOCHASTIC_KEY_FIELDS,
        model_id="provider/model"),

    # Stochastic tuple-generating LLM operator (QPATH-040): NOT
    # tuple-preserving; it must not be modeled as a Select inheriting
    # the input relation as an upper bound (13.7.1, 26.6).
    "sol:evaluator/tuple_generator/v1": _contract(
        "tuple_generator", "stochastic",
        generates_tuples=True,
        key_fields=STOCHASTIC_KEY_FIELDS,
        model_id="provider/generation-model"),
}


def contract_of(evaluator_id: str) -> dict[str, Any] | None:
    return EVALUATOR_CONTRACTS.get(evaluator_id)


def is_stochastic(evaluator_id: str) -> bool:
    c = contract_of(evaluator_id)
    return bool(c) and c.get("determinism") == "stochastic"


# ---------------------------------------------------------------------------
# Materialized assessment records (26.3, 26.7)

def _tuple_key(t: Any) -> str:
    return json.dumps(t, sort_keys=True)


def assessment_relation_digest(src: dict[str, Any]) -> str:
    """Content digest of the assessment relation (schema + tuples).

    The recorded `result_object` MUST equal this digest: the
    assessment is an immutable object, and a mismatch means the
    relation is not the recorded evaluation result (26.5, QINV-13).
    """
    from .canonical import canonical_json  # lazy: avoid an import cycle
    obj = {
        "fields": list(src.get("schema", [])),
        "tuples": sorted(src.get("tuples", []), key=_tuple_key),
    }
    return "object:sha256:" + hashlib.sha256(
        canonical_json(obj).encode("utf-8")).hexdigest()


def _assessment_diagnostics(name: str, src: dict[str, Any],
                            a: dict[str, Any]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    ev = a.get("evaluator_id", "")
    contract = contract_of(ev)
    if contract is None:
        diags.append(diag("QV6-01", "unregistered_evaluator", f"source:{name}",
                          f"Evaluator {ev!r} has no registered input and output schemas (26.2)"))
    missing = [f for f in ASSESSMENT_REQUIRED_FIELDS if not a.get(f)]
    if missing:
        diags.append(diag("QV6-02", "incomplete_evaluation_record", f"source:{name}",
                          "Evaluation record is missing recorded identity: "
                          + ", ".join(missing) + " (26.7)"))
    expected = assessment_relation_digest(src)
    if a.get("result_object") != expected:
        diags.append(diag("QV6-03", "assessment_not_immutable", f"source:{name}",
                          "The recorded result object does not match the assessment "
                          "relation's content; the assessment is not immutable (26.5)"))
    return diags


# ---------------------------------------------------------------------------
# Plan-shape checks (26.4, 26.5, 26.8)

def evaluator_semantic_diagnostics(query: dict[str, Any]) -> list[Diagnostic]:
    """Plan-shape semantic-evaluator checks. Inert for queries that use
    no evaluators and no assessment sources."""
    diags: list[Diagnostic] = []
    nodes = {n["id"]: n for n in query.get("nodes", [])}

    # 26.3/26.7: materialized assessment records.
    for name, src in sorted((query.get("sources") or {}).items()):
        a = src.get("assessment")
        if a is not None:
            diags.extend(_assessment_diagnostics(name, src, a))

    # 26.5/Q15: stochastic evaluators in a rewritable plan need a
    # complete deterministic evaluation key (or a materialized
    # assessment, which is a source-level record).
    eval_nodes = [n for n in nodes.values() if n.get("op") == "evaluate"]
    for n in sorted(eval_nodes, key=lambda x: x.get("id", "")):
        ev = n.get("evaluator", "")
        if not ev or not is_stochastic(ev):
            continue
        key = n.get("evaluation_key")
        if not isinstance(key, dict):
            diags.append(diag("QV6-03", "missing_evaluation_key", f"node:{n.get('id')}",
                              "A stochastic evaluator in a rewritable plan has no "
                              "deterministic evaluation key (26.5, Q15)"))
            continue
        if key.get("transient"):
            diags.append(diag("QINV-13", "transient_assessment", f"node:{n.get('id')}",
                              "A transient cache entry that may expire or vary does not "
                              "satisfy the stable-assessment invariant (26.5)"))
            diags.append(diag("QV6-03", "transient_evaluation_key", f"node:{n.get('id')}",
                              "The evaluation key resolves to a transient result, not an "
                              "immutable result object (26.5)"))
            continue
        contract = contract_of(ev)
        required = list(UNIVERSAL_KEY_FIELDS) + list(
            contract.get("evaluation_key_schema", []) if contract else [])
        missing = [f for f in required if f not in key]
        if missing:
            diags.append(diag("QV6-03", "incomplete_evaluation_key", f"node:{n.get('id')}",
                              "The evaluation key is missing required fields: "
                              + ", ".join(missing) + " (26.5, Q15)"))

    # 26.4: an inline evaluator is not duplicable by default. Two
    # evaluate nodes with the same evaluator over the same input are a
    # duplicated evaluator call (QV6-05); for a stochastic evaluator
    # the duplication also breaks evaluation-identity equivalence
    # (27), which the query may require (QV7-03).
    required_dims = set(query.get("required_dimensions") or ())
    by_call: dict[tuple[str, str], list[str]] = {}
    for n in eval_nodes:
        by_call.setdefault((n.get("evaluator", ""), n.get("input", "")),
                           []).append(n.get("id", ""))
    for (ev, _inp), ids in sorted(by_call.items()):
        if len(ids) > 1 and ev:
            target = "node:" + "/".join(sorted(ids))
            diags.append(diag("QV6-05", "duplicated_evaluator_call", target,
                              "The plan duplicates an inline evaluator call; an inline "
                              "evaluator is not duplicable by default (26.4)"))
            if is_stochastic(ev) and "evaluation_identity" in required_dims:
                diags.append(diag("QV7-03", "preservation_dimensions_uncovered", "query",
                                  "The duplicated stochastic call breaks evaluation-identity "
                                  "equivalence; the preservation contract does not cover the "
                                  "query-required logical-equivalence dimensions (27)"))

    # 26.8/QINV-04: a semantic-equivalence evaluator used as exact
    # identity (`=`/`!=`) is a forgery (QV6-04: heuristic labeled
    # exact without proof).
    for n in sorted(nodes.values(), key=lambda x: x.get("id", "")):
        if n.get("op") != "filter":
            continue
        for t in sorted((n.get("predicate") or {}).get("terms", []),
                        key=lambda t: json.dumps(t, sort_keys=True)):
            ev = t.get("evaluator")
            if not ev or t.get("op") not in {"eq", "ne"}:
                continue
            contract = contract_of(ev)
            if contract is None:
                diags.append(diag("QV6-01", "unregistered_evaluator", f"node:{n.get('id')}",
                                  f"Evaluator {ev!r} has no registered input and output "
                                  f"schemas (26.2)"))
                continue
            if contract.get("semantic_equivalence"):
                diags.append(diag("QINV-04", "semantic_equality_forgery", f"node:{n.get('id')}",
                                  f"Semantic similarity from {ev} is interpreted as exact "
                                  f"identity on field {t.get('field')!r}; `=` MUST mean "
                                  f"exact typed equality (8.5, 26.8)"))
                diags.append(diag("QV6-04", "heuristic_labeled_exact", f"node:{n.get('id')}",
                                  "A stochastic/heuristic evaluation is labeled exact "
                                  "without proof (26.6)"))
    return diags


# ---------------------------------------------------------------------------
# Claim-based checks (wired into claim_semantic_diagnostics)

def claim_evaluator_diagnostics(query: dict[str, Any], claim) -> list[Diagnostic]:
    """Checks that fire only when a claimed bound record commits to more
    than the plan's evaluators support (QV5-08, QV5-09, QV6-07)."""
    diags: list[Diagnostic] = []
    nodes = {n["id"]: n for n in query.get("nodes", [])}
    g = claim.guarantee

    # QV5-08: a heuristic input or predicate contributes to a
    # certified output side only through a normative or registered
    # rule. No rule licenses a heuristic contribution to an exact
    # side, so an exact claim over a plan containing a heuristic
    # evaluator is a resurrection.
    if g == "exact":
        root_ids: set[str] = set()
        stack = [query.get("root")]
        while stack:
            nid = stack.pop()
            if not nid or nid in root_ids or nid not in nodes:
                continue
            root_ids.add(nid)
            n = nodes[nid]
            op = n.get("op")
            if op in {"filter", "project", "limit", "sort", "distinct", "aggregate",
                      "rename", "annotate", "evaluate", "temporal_slice", "policy_boundary"}:
                stack.append(n.get("input"))
            elif op == "join":
                stack.extend([n.get("left"), n.get("right")])
            elif op in {"union_all", "union_distinct", "intersect", "difference"}:
                stack.extend(n.get("inputs", []))
            elif op == "least_fixpoint":
                stack.extend([n.get("seed"), n.get("edge")])
        for nid in sorted(root_ids):
            n = nodes[nid]
            if n.get("op") != "evaluate":
                continue
            contract = contract_of(n.get("evaluator", ""))
            if contract and contract.get("guarantee") == "heuristic":
                diags.append(diag("QV5-08", "heuristic_contribution_to_certified_side",
                                  f"node:{nid}",
                                  "A heuristic evaluator contributes to an exact certified "
                                  "side without a normative or registered transfer rule "
                                  "(13.7.1, 26.6)"))
                break

    # QV6-07/QV5-09: a tuple-generating evaluator modeled as a
    # tuple-preserving Select. No upper bound is certifiable for its
    # output, so any claimed upper (in particular the inherited input
    # upper) asserts a containment the operator cannot satisfy.
    root_node = nodes.get(query.get("root"))
    if root_node is not None and root_node.get("op") == "evaluate":
        contract = contract_of(root_node.get("evaluator", ""))
        if contract and contract.get("generates_tuples") and claim.upper is not None:
            diags.append(diag("QV5-09", "containment_not_certified",
                              f"node:{root_node.get('id')}",
                              "A structural one-sided bound does not satisfy the declared "
                              "containment: a tuple-generating evaluator does not preserve "
                              "the input relation as an upper bound (13.7.1, 26.6)"))
            diags.append(diag("QV6-07", "tuple_generating_select",
                              f"node:{root_node.get('id')}",
                              "An evaluator used as a tuple-preserving Select generates "
                              "tuples (26.6)"))
    return diags
