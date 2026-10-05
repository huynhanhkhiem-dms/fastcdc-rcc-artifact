"""Exact static compatibility calculations for zero-mask normalized CDC rules.

The scripts implement the analytical quantities used in the manuscript.  For a
uniform w-bit outcome U and B_M={u:(u & M)==0},

    P(B_M) = 2^{-popcount(M)}
    P(B_M cap B_N) = 2^{-popcount(M|N)}.

For two rules A,C with marginals p,q, disagreement d decomposes into the
classical marginal lower bound |p-q| plus geometry excess g.  We also report the normalized residual rho, which places the residual within
the full feasible disagreement range after fixing p and q. For nontrivial
zero-mask rules,

    rho = 1 - 2^{-r}.

In this regime rho is exactly one minus the classical overlap coefficient. It
is therefore used as a descriptive CDC specialization rather than claimed as a
new generic set-similarity metric. The integer r counts constrained bits of the
less restrictive rule that fall outside the stricter rule.
"""
from __future__ import annotations

from fractions import Fraction
import json
import math
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "mask_geometry.json")

MASK_S_2016 = 0x0003590703530000
MASK_S_2020 = 0x0000D9F003530000
MASK_L = 0x0000D90003530000
SEED = 20260924
N_DRAWS = 2_000_000


def popcount(x: int) -> int:
    return x.bit_count()


def fmeasure(mask: int) -> Fraction:
    return Fraction(1, 2 ** popcount(mask))


def _frac_obj(x: Fraction) -> dict:
    return {"numerator": x.numerator, "denominator": x.denominator, "decimal": float(x)}


def summarize(name: str, a: int, b: int) -> dict:
    p, q = fmeasure(a), fmeasure(b)
    ka, kb = popcount(a), popcount(b)
    union = popcount(a | b)
    inter = Fraction(1, 2 ** union)
    d = p + q - 2 * inter
    lower = abs(p - q)
    upper = min(p + q, 2 - p - q)
    g = d - lower
    capacity = upper - lower
    rho = g / capacity if capacity else Fraction(0, 1)
    k_strict = max(ka, kb)
    r = union - k_strict
    return {
        "name": name,
        "mask_a_hex": f"0x{a:016x}",
        "mask_b_hex": f"0x{b:016x}",
        "mask_a_ones": ka,
        "mask_b_ones": kb,
        "union_ones": union,
        "xor_ones": popcount(a ^ b),
        "misalignment_bits_r": r,
        "p_a": _frac_obj(p),
        "p_b": _frac_obj(q),
        "intersection": _frac_obj(inter),
        "exact_disagreement": _frac_obj(d),
        "marginal_lower_bound": _frac_obj(lower),
        "frechet_upper_bound": _frac_obj(upper),
        "geometry_excess": _frac_obj(g),
        "geometry_capacity": _frac_obj(capacity),
        "geometry_excess_saturation": _frac_obj(rho),
    }


def main() -> None:
    rows = [
        summarize("FastCDC 2016 within-version MaskS/MaskL", MASK_S_2016, MASK_L),
        summarize("FastCDC 2020 within-version MaskS/MaskL", MASK_S_2020, MASK_L),
        summarize("Cross-version pre-target MaskS 2016/2020", MASK_S_2016, MASK_S_2020),
        summarize("Cross-version post-target MaskL 2016/2020", MASK_L, MASK_L),
    ]

    design_space = []
    for r in range(0, 12):
        rho = Fraction(2**r - 1, 2**r) if r else Fraction(0, 1)
        g_15_11 = Fraction(1, 2**14) * rho
        p15, p11 = Fraction(1, 2**15), Fraction(1, 2**11)
        d_15_11 = (p11 - p15) + g_15_11
        design_space.append({
            "misalignment_bits_r": r,
            "saturation": _frac_obj(rho),
            "within_15_11_geometry_excess": _frac_obj(g_15_11),
            "within_15_11_exact_disagreement": _frac_obj(d_15_11),
        })

    # Deterministic Monte Carlo: implementation check only, never the source of
    # reported analytical values.
    rng = random.Random(SEED)
    pairs = [
        (MASK_S_2016, MASK_L),
        (MASK_S_2020, MASK_L),
        (MASK_S_2016, MASK_S_2020),
    ]
    counts = [0] * len(pairs)
    for _ in range(N_DRAWS):
        u = rng.getrandbits(64)
        for j, (a, b) in enumerate(pairs):
            counts[j] += int(((u & a) == 0) != ((u & b) == 0))
    for row, count in zip(rows[:3], counts):
        p0 = row["exact_disagreement"]["decimal"]
        phat = count / N_DRAWS
        se = math.sqrt(p0 * (1 - p0) / N_DRAWS) if p0 else 0.0
        row["monte_carlo"] = {
            "draws": N_DRAWS,
            "seed": SEED,
            "count": count,
            "estimate": phat,
            "z_from_exact": ((phat - p0) / se) if se else 0.0,
        }

    obj = {
        "model": "uniform 64-bit outcome; cut iff (U & mask)==0",
        "published_masks": {
            "fastcdc_2016_MaskS": f"0x{MASK_S_2016:016x}",
            "fastcdc_2020_MaskS": f"0x{MASK_S_2020:016x}",
            "MaskL_shared": f"0x{MASK_L:016x}",
        },
        "rows": rows,
        "zero_mask_saturation_curve": design_space,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

    for row in rows:
        print(row["name"])
        print("  d   =", row["exact_disagreement"])
        print("  g   =", row["geometry_excess"])
        print("  rho =", row["geometry_excess_saturation"])
        print("  r   =", row["misalignment_bits_r"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
