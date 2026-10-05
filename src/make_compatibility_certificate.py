"""Generate the RCC-1.1 machine-checkable compatibility certificate.

RCC-1.1 embeds the complete canonical descriptors used by the registered
executor. SHA-256 fingerprints are integrity identifiers over those descriptors;
fieldwise descriptor identity, not digest equality, is the sufficient premise
for the universal-identity certificate supported by this schema.
"""
from __future__ import annotations

import hashlib
import json
import os

from boundary_stream import GEAR, MASK_S_2016, MASK_S_2020, MASK_L, MIN_SIZE, AVG_SIZE, MAX_SIZE
from rule_model import Rule, descriptor_differences

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(RES, "compatibility_certificate.json")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def controlled_rules() -> tuple[Rule, Rule]:
    common = dict(
        gear=tuple(GEAR), post_mask=MASK_L, min_size=MIN_SIZE,
        avg_size=AVG_SIZE, max_size=MAX_SIZE, word_bits=64, reset_state=0,
    )
    return (
        Rule(name="printed_2016_pre_mask", pre_mask=MASK_S_2016, **common),
        Rule(name="printed_2020_pre_mask", pre_mask=MASK_S_2020, **common),
    )


def main() -> None:
    old, new = controlled_rules()
    with open(os.path.join(RES, "inequivalence_witness.json"), encoding="utf-8") as f:
        witness = json.load(f)
    with open(os.path.join(RES, "real_source_validation.json"), encoding="utf-8") as f:
        replay = json.load(f)

    identical = old.descriptor() == new.descriptor()
    witness_valid_shape = (
        witness.get("decision_2016_cut") is True and
        witness.get("decision_2020_cut") is False and
        witness.get("mask_2016_hex", "").lower() == f"0x{MASK_S_2016:016x}" and
        witness.get("mask_2020_hex", "").lower() == f"0x{MASK_S_2020:016x}"
    )
    if identical:
        verdict = "UNIVERSAL_EQUIVALENCE_BY_COMPLETE_DECLARED_RULE_IDENTITY"
    elif witness_valid_shape:
        verdict = "CONSTRUCTIVE_INEQUIVALENCE_WITH_WORKLOAD_SCOPED_REPLAY"
    else:
        verdict = "REPLAY_ONLY_NO_UNIVERSAL_CLAIM"

    evidence_files = [
        "boundary_stream_results.json",
        "conformance_vectors.json",
        "inequivalence_witness.json",
        "mask_geometry.json",
        "rule_mutation_suite.json",
        "reset_state_transient_witness.json",
        "gear_sensitivity.json",
        "public_implementation_audit.csv",
    ]
    real_source = os.path.join(RES, "real_source_validation.json")
    if os.path.exists(real_source):
        evidence_files.append("real_source_validation.json")

    cert = {
        "schema": "rcc-1.1",
        "registered_executor": "fastcdc_published_index_v1",
        "verdict": verdict,
        "claim_semantics": {
            "universal_equivalence": (
                "For the registered executor, fieldwise identity of the complete canonical rule descriptors "
                "is a sufficient premise for identical boundary streams on every finite input. Descriptor "
                "fingerprints are integrity identifiers only."
            ),
            "constructive_inequivalence": (
                "A verified jointly live-reachable candidate at which the two declared rules make different "
                "boundary decisions disproves universal equivalence."
            ),
            "workload_replay": (
                "Replay metrics apply only to the declared byte streams, rule pair, migration direction, and "
                "reuse definition; they do not imply universal behavior or deployment prevalence."
            ),
        },
        "old_rule": {
            "name": old.name,
            "fingerprint_sha256": old.fingerprint(),
            "descriptor": old.descriptor(),
        },
        "new_rule": {
            "name": new.name,
            "fingerprint_sha256": new.fingerprint(),
            "descriptor": new.descriptor(),
        },
        "descriptor_differences": descriptor_differences(old, new),
        "constructive_witness": {
            "present": witness_valid_shape,
            "result_file": "inequivalence_witness.json",
            "workload": witness.get("workload"),
            "replicate_one_based": witness.get("replicate_one_based"),
            "shared_reset_offset": witness.get("shared_reset_offset"),
            "candidate_byte_offset_zero_based": witness.get("candidate_byte_offset_zero_based"),
            "candidate_boundary_end_exclusive": witness.get("candidate_boundary_end_exclusive"),
            "state_hex": witness.get("state_hex"),
        },
        "replay_scope": {
            "result_file": "real_source_validation.json",
            "corpus": replay["corpus"]["name"],
            "files": replay["summary"]["n_files"],
            "total_bytes": replay["summary"]["total_bytes"],
            "migration_reuse_range": replay["summary"]["migration_reuse_range"],
            "boundary_metric_primary": "exact boundary identity plus boundary Jaccard",
            "content_reuse_metric": "content-addressed same-content byte reuse",
        },
        "evidence_sha256": {name: sha256_file(os.path.join(RES, name)) for name in evidence_files},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2)
    print(json.dumps({
        "schema": cert["schema"],
        "verdict": verdict,
        "old_fingerprint": old.fingerprint(),
        "new_fingerprint": new.fingerprint(),
        "differing_fields": list(cert["descriptor_differences"]),
    }, indent=2))


if __name__ == "__main__":
    main()
