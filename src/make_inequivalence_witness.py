"""Generate a concrete jointly live-reachable inequivalence witness.

The witness is extracted from the frozen primary experiment.  It does not claim
that an abstract acceptance-set difference is always reachable.  Instead, it
records an observed candidate state reached by both compared rules from a
shared reset before either rule has cut, at which the two pre-target masks make
different decisions.
"""
from __future__ import annotations

import hashlib
import json
import os

from boundary_stream import (
    AVG_SIZE,
    GEAR,
    MASK64,
    MASK_S_2016,
    MASK_S_2020,
    MIN_SIZE,
    chunk_boundaries,
    make_workloads,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "inequivalence_witness.json")


def extract_witness(data: bytes, workload: str, replicate_zero_based: int) -> dict:
    b16 = chunk_boundaries(data, MASK_S_2016)
    b20 = chunk_boundaries(data, MASK_S_2020)
    if b16 == b20:
        raise ValueError("selected stream has no boundary divergence")

    union = sorted(set(b16) | set(b20))
    first_unique_boundary = next(x for x in union if (x in b16) != (x in b20))
    shared_before = max(x for x in set(b16).intersection(b20) if x < first_unique_boundary)

    fp = 0
    start_candidate = shared_before + MIN_SIZE
    stop_candidate = min(shared_before + AVG_SIZE, len(data))
    for candidate_index in range(start_candidate, stop_candidate):
        fp = ((fp << 1) + GEAR[data[candidate_index]]) & MASK64
        cut16 = (fp & MASK_S_2016) == 0
        cut20 = (fp & MASK_S_2020) == 0

        if cut16 != cut20:
            boundary = candidate_index
            assert boundary == first_unique_boundary
            decision_bytes = data[shared_before:candidate_index + 1]
            scanned = data[start_candidate:candidate_index + 1]
            return {
                "workload": workload,
                "replicate_one_based": replicate_zero_based + 1,
                "shared_reset_offset": shared_before,
                "candidate_byte_offset_zero_based": candidate_index,
                "candidate_boundary_end_exclusive": boundary,
                "returned_chunk_length_bytes": boundary - shared_before,
                "tested_hash_updates_one_based": candidate_index - start_candidate + 1,
                "state_hex": f"0x{fp:016x}",
                "mask_2016_hex": f"0x{MASK_S_2016:016x}",
                "mask_2020_hex": f"0x{MASK_S_2020:016x}",
                "decision_2016_cut": cut16,
                "decision_2020_cut": cut20,
                "decision_prefix_including_candidate_sha256": hashlib.sha256(decision_bytes).hexdigest(),
                "scanned_candidate_bytes_sha256": hashlib.sha256(scanned).hexdigest(),
                "candidate_byte_decimal": data[candidate_index],
                "boundary_convention": "hash src[i], test, return relative i; absolute end-exclusive boundary=start+i; tested src[i] belongs to the following chunk",
                "interpretation": (
                    "Both rules share the reset at shared_reset_offset and survive every earlier "
                    "candidate. The recorded common state is therefore jointly live-reachable; "
                    "the two printed pre-target masks make different decisions at this candidate."
                ),
            }

        if cut16 and cut20:
            raise AssertionError("a common pre-target cut occurred before the recorded divergent boundary")

    raise AssertionError("no differing pre-target decision found before the first unique boundary")

def main() -> None:
    data = make_workloads(replicate=0)["uniform"]
    witness = extract_witness(data, "uniform", 0)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(witness, f, indent=2)
    print(json.dumps(witness, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
