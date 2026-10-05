"""Offline verifier for the RCC-1.1 certificate shipped with this study."""
from __future__ import annotations

import hashlib
import json
import os

from boundary_stream import make_workloads
from make_inequivalence_witness import extract_witness
from rule_model import canonical_json_bytes, rule_from_descriptor, validate_descriptor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest_descriptor(desc: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(desc)).hexdigest()


def main() -> None:
    with open(os.path.join(RES, "compatibility_certificate.json"), encoding="utf-8") as f:
        cert = json.load(f)
    assert cert["schema"] == "rcc-1.1"
    assert cert["registered_executor"] == "fastcdc_published_index_v1"

    # Generic descriptor integrity/round-trip checks: the full Gear table and all
    # registered boundary semantics are inside the descriptor itself.
    for side in ("old_rule", "new_rule"):
        desc = cert[side]["descriptor"]
        validate_descriptor(desc)
        rule = rule_from_descriptor(desc, name=cert[side]["name"])
        assert rule.descriptor() == desc
        assert digest_descriptor(desc) == cert[side]["fingerprint_sha256"]

    old_desc = cert["old_rule"]["descriptor"]
    new_desc = cert["new_rule"]["descriptor"]
    actual_diff = {
        k: {"old": old_desc.get(k), "new": new_desc.get(k)}
        for k in sorted(set(old_desc) | set(new_desc))
        if old_desc.get(k) != new_desc.get(k)
    }
    assert actual_diff == cert["descriptor_differences"]

    # Study-specific witness verification. The certificate names the deterministic
    # workload/replicate, allowing the decision path to be regenerated offline.
    cw = cert["constructive_witness"]
    assert cw["present"] is True
    replicate_zero = int(cw["replicate_one_based"]) - 1
    wdata = make_workloads(replicate=replicate_zero)[cw["workload"]]
    w = extract_witness(wdata, cw["workload"], replicate_zero)
    for key in (
        "shared_reset_offset", "candidate_byte_offset_zero_based",
        "candidate_boundary_end_exclusive", "state_hex",
    ):
        assert cw[key] == w[key]

    for name, digest in cert["evidence_sha256"].items():
        assert sha256_file(os.path.join(RES, name)) == digest, name

    assert cert["verdict"] == "CONSTRUCTIVE_INEQUIVALENCE_WITH_WORKLOAD_SCOPED_REPLAY"
    print("RCC-1.1 VERIFICATION PASS")


if __name__ == "__main__":
    main()
