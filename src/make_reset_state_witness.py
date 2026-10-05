"""Construct a deterministic transient witness for a reset-state-only change.

For Gear recurrence H_{t+1}=2H_t+G(b_t) mod 2^w, two initial states
converge after at most w common hash updates because their difference is
2^t(H_0-H'_0) mod 2^w.  Before that horizon, reset state can still alter a
boundary decision.  This script deterministically searches for such an early
candidate under the frozen 2016 pre-target mask.
"""
from __future__ import annotations

import hashlib
import json
import os
import random

from boundary_stream import GEAR, MASK_S_2016

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "reset_state_transient_witness.json")
WORD_BITS = 64
MASK64 = (1 << WORD_BITS) - 1
RESET_A = 0
RESET_B = 0x9E3779B97F4A7C15
SEARCH_SEED = 271828
MAX_TRIALS = 200000


def main() -> None:
    rng = random.Random(SEARCH_SEED)
    for trial in range(1, MAX_TRIALS + 1):
        h_a, h_b = RESET_A, RESET_B
        bs = bytearray()
        for update_index in range(1, WORD_BITS + 1):
            b = rng.randrange(256)
            bs.append(b)
            h_a = ((h_a << 1) + GEAR[b]) & MASK64
            h_b = ((h_b << 1) + GEAR[b]) & MASK64
            cut_a = (h_a & MASK_S_2016) == 0
            cut_b = (h_b & MASK_S_2016) == 0
            if cut_a != cut_b:
                out = {
                    "word_bits": WORD_BITS,
                    "search_seed": SEARCH_SEED,
                    "trial": trial,
                    "candidate_update_index_one_based": update_index,
                    "reset_a_hex": f"0x{RESET_A:016x}",
                    "reset_b_hex": f"0x{RESET_B:016x}",
                    "state_a_hex": f"0x{h_a:016x}",
                    "state_b_hex": f"0x{h_b:016x}",
                    "mask_hex": f"0x{MASK_S_2016:016x}",
                    "decision_a_cut": cut_a,
                    "decision_b_cut": cut_b,
                    "candidate_bytes_hex": bytes(bs).hex(),
                    "candidate_bytes_sha256": hashlib.sha256(bytes(bs)).hexdigest(),
                    "convergence_bound_updates": WORD_BITS,
                    "interpretation": (
                        "The reset-state difference can change a decision before the w-update "
                        "convergence horizon. If both executions survive w common hash updates, "
                        "their states are identical thereafter until the next reset."
                    ),
                }
                with open(OUT, "w", encoding="utf-8") as f:
                    json.dump(out, f, indent=2)
                print(json.dumps(out, indent=2))
                return
            if cut_a and cut_b:
                break
    raise RuntimeError("no transient witness found within deterministic search budget")


if __name__ == "__main__":
    main()
