"""Offline integrity checks for the analytical supplement."""
from __future__ import annotations

import hashlib

from fractions import Fraction
import csv
import json
import math
import os
import random

from mask_geometry import MASK_L, MASK_S_2016, MASK_S_2020, popcount

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results")

# 1) 64-bit shift-state forgetting sanity check: H_{t+1}=2H_t+G(b_t) mod 2^64.
#    This is not the shared-boundary lemma; the lemma follows from an explicit reset.
rng = random.Random(20260924)
GEAR = [rng.getrandbits(64) for _ in range(256)]
MASK64 = (1 << 64) - 1
rng2 = random.Random(1701)
for _ in range(100):
    h1, h2 = rng2.getrandbits(64), rng2.getrandbits(64)
    suffix = bytes(rng2.getrandbits(8) for _ in range(64))
    for b in suffix:
        h1 = ((h1 << 1) + GEAR[b]) & MASK64
        h2 = ((h2 << 1) + GEAR[b]) & MASK64
    assert h1 == h2

# 2) Exhaustive set-geometry identity on every pair of subsets of 8 outcomes.
for am in range(1 << 8):
    A = {i for i in range(8) if (am >> i) & 1}
    for cm in range(1 << 8):
        C = {i for i in range(8) if (cm >> i) & 1}
        p, q = Fraction(len(A), 8), Fraction(len(C), 8)
        inter = Fraction(len(A.intersection(C)), 8)
        d = Fraction(len(A.symmetric_difference(C)), 8)
        lower = abs(p - q)
        upper = min(p + q, 2 - p - q)
        g = d - lower
        capacity = upper - lower
        assert lower <= d <= upper
        assert g == 2 * (min(p, q) - inter)
        assert g >= 0
        if g == 0:
            smaller, larger = (A, C) if p <= q else (C, A)
            assert smaller.issubset(larger)
        if capacity > 0:
            rho = g / capacity
            assert 0 <= rho <= 1

# 3) An attainable finite nested schedule simultaneously reaches all pairwise minima.
#    All hazards are integer multiples of 1/1000, matching the finite outcome space.
hazard_counts = [50, 200, 120, 350, 80]
N = 1000
sets = [set(range(k)) for k in hazard_counts]
for i, A in enumerate(sets):
    for j, C in enumerate(sets):
        d = Fraction(len(A.symmetric_difference(C)), N)
        assert d == abs(Fraction(len(A), N) - Fraction(len(C), N))

# 4) Exact published-mask checks.
with open(os.path.join(RES, "mask_geometry.json"), encoding="utf-8") as f:
    obj = json.load(f)
rows = {r["name"]: r for r in obj["rows"]}
r16 = rows["FastCDC 2016 within-version MaskS/MaskL"]
r20 = rows["FastCDC 2020 within-version MaskS/MaskL"]
rx = rows["Cross-version pre-target MaskS 2016/2020"]
rl = rows["Cross-version post-target MaskL 2016/2020"]

assert popcount(MASK_S_2016) == 15
assert popcount(MASK_S_2020) == 15
assert popcount(MASK_L) == 11
assert popcount(MASK_S_2016 | MASK_L) == 16
assert popcount(MASK_S_2020 | MASK_L) == 15
assert (MASK_L & ~MASK_S_2020) == 0  # 2020 MaskL is nested in MaskS.

assert r16["misalignment_bits_r"] == 1
assert Fraction(r16["exact_disagreement"]["numerator"], r16["exact_disagreement"]["denominator"]) == Fraction(1, 2**11)
assert Fraction(r16["geometry_excess"]["numerator"], r16["geometry_excess"]["denominator"]) == Fraction(1, 2**15)
assert Fraction(r16["geometry_excess_saturation"]["numerator"], r16["geometry_excess_saturation"]["denominator"]) == Fraction(1, 2)

assert r20["misalignment_bits_r"] == 0
assert Fraction(r20["exact_disagreement"]["numerator"], r20["exact_disagreement"]["denominator"]) == Fraction(15, 2**15)
assert r20["geometry_excess"]["numerator"] == 0
assert r20["geometry_excess_saturation"]["numerator"] == 0

assert popcount(MASK_S_2016 | MASK_S_2020) == 20
assert popcount(MASK_S_2016 ^ MASK_S_2020) == 10
assert rx["misalignment_bits_r"] == 5
assert Fraction(rx["exact_disagreement"]["numerator"], rx["exact_disagreement"]["denominator"]) == Fraction(31, 2**19)
assert Fraction(rx["geometry_excess_saturation"]["numerator"], rx["geometry_excess_saturation"]["denominator"]) == Fraction(31, 32)
assert rl["exact_disagreement"]["numerator"] == 0

# 5) For zero masks, saturation depends only on r: rho = 1 - 2^{-r}.
for row in obj["zero_mask_saturation_curve"]:
    r = row["misalignment_bits_r"]
    got = Fraction(row["saturation"]["numerator"], row["saturation"]["denominator"])
    exp = Fraction(0, 1) if r == 0 else Fraction(2**r - 1, 2**r)
    assert got == exp

# 6) Monte Carlo is only an implementation check; tolerate four standard deviations.
for row in (r16, r20, rx):
    assert abs(row["monte_carlo"]["z_from_exact"]) < 4.0

# 7) Frozen public-code audit metadata is structurally consistent and contains both lineages.
#    This offline check does not download GitHub content; use verify_public_audit.py
#    for optional remote source-content verification.
audit_path = os.path.join(RES, "public_implementation_audit.csv")
with open(audit_path, newline="", encoding="utf-8") as f:
    audit = list(csv.DictReader(f))
assert len(audit) >= 6
assert {r["lineage"] for r in audit} >= {"2016-mask", "2020-mask"}
for row in audit:
    assert len(row["commit"]) == 40
    assert row["url"].startswith("https://github.com/")
    int(row["mask_s_hex"], 16)
    int(row["mask_l_hex"], 16)

print("Core analytical checks PASS")
print("64-bit shift-state forgetting sanity check: 100/100 pairs equal after 64 common updates")
print("Set geometry: exhaustive on all pairs of subsets of an 8-point space")
print("Finite nested schedule: all pairwise marginal lower bounds attained")
print("FastCDC 2016 within-version: g=2^-15, saturation=1/2")
print("FastCDC 2020 within-version: g=0, saturation=0")
print("2016-vs-2020 pre-target MaskS: d=31/2^19, saturation=31/32=96.875%")
print("Frozen public-code audit metadata: structural checks PASS; both lineages present")

# 8) Gear-table sensitivity output is internally complete.
with open(os.path.join(RES, 'gear_sensitivity.json'), encoding='utf-8') as f:
    gs_obj = json.load(f)
assert gs_obj['design']['n_tables'] == 5
assert gs_obj['design']['total_runs'] == 370
assert gs_obj['summary']['global_boundary_jaccard_range'] == [0.0, 1.0]
assert gs_obj['summary']['global_migration_reuse_range'] == [0.0, 1.0]
print('Gear-table sensitivity: 5 tables / 370 real-source runs structural checks PASS')

# 9) Boundary-stream study: independently recompute one deterministic workload.

from boundary_stream import (
    make_workloads, chunk_boundaries, stream_metrics,
    content_addressed_migration_reuse, MASK_S_2016 as BS16,
    MASK_S_2020 as BS20,
)
with open(os.path.join(RES, 'boundary_stream_results.json'), encoding='utf-8') as f:
    bs_obj = json.load(f)
uniform0 = make_workloads(replicate=0)['uniform']
b16 = chunk_boundaries(uniform0, BS16)
b20 = chunk_boundaries(uniform0, BS20)
sm = stream_metrics(b16, b20, len(uniform0))
mr = content_addressed_migration_reuse(uniform0, b16, b20)
row0 = next(r for r in bs_obj['rows'] if r['workload']=='uniform' and r['replicate']==1)
for key in ['chunks_2016','chunks_2020','shared_internal_boundaries','divergence_episodes']:
    assert sm[key] == row0[key]
for key in ['boundary_overlap_coefficient','exact_chunk_overlap_coefficient','divergent_byte_fraction','positional_byte_reuse']:
    assert abs(sm[key] - row0[key]) < 1e-15
assert abs(mr - row0['content_addressed_migration_reuse']) < 1e-15
assert bs_obj['summary']['boundary_overlap_range'] == [0.0, 1.0]
assert bs_obj['summary']['migration_reuse_range'] == [0.0, 1.0]
print('Boundary-stream study: deterministic recomputation PASS')

# 10) Boundary-overlap empty-set semantics and end-exclusive boundary convention.
from boundary_stream import overlap_coefficient
assert overlap_coefficient(set(), set()) == 1.0
assert overlap_coefficient(set(), {5000}) == 0.0
assert overlap_coefficient({5000}, set()) == 0.0
assert overlap_coefficient({5000}, {5000, 7000}) == 1.0
# For a forced single-chunk stream the terminal boundary is exactly len(data).
assert chunk_boundaries(b'\x00' * 100, BS16) == [0, 100]
print('Boundary convention and empty-set overlap semantics: PASS')

# 11) Recompute the published conformance vectors when present.
vec_path = os.path.join(RES, 'conformance_vectors.json')
if os.path.exists(vec_path):
    with open(vec_path, encoding='utf-8') as f:
        vec = json.load(f)
    assert vec['boundary_convention'].startswith('hash src[i], test, return relative i')
    for case in vec['cases']:
        data = make_workloads(size=case['bytes'], replicate=case['replicate_zero_based'])[case['workload']]
        assert hashlib.sha256(data).hexdigest() == case['input_sha256']
        assert chunk_boundaries(data, BS16) == case['boundaries_2016']
        assert chunk_boundaries(data, BS20) == case['boundaries_2020']
    print('Conformance vectors: deterministic recomputation PASS')


# 12) Concrete jointly live-reachable inequivalence witness.
from make_inequivalence_witness import extract_witness
with open(os.path.join(RES, "inequivalence_witness.json"), encoding="utf-8") as f:
    witness = json.load(f)
wdata = make_workloads(replicate=witness["replicate_one_based"] - 1)[witness["workload"]]
recomputed = extract_witness(wdata, witness["workload"], witness["replicate_one_based"] - 1)
assert recomputed == witness
state = int(witness["state_hex"], 16)
assert ((state & MASK_S_2016) == 0) == witness["decision_2016_cut"]
assert ((state & MASK_S_2020) == 0) == witness["decision_2020_cut"]
assert witness["decision_2016_cut"] != witness["decision_2020_cut"]
print("Concrete jointly live-reachable inequivalence witness: PASS")


# 13) Cross-component mutation suite and primary Jaccard metric.
with open(os.path.join(RES, "rule_mutation_suite.json"), encoding="utf-8") as f:
    mut = json.load(f)
assert mut["design"]["pair_count"] == 5
assert mut["design"]["total_runs"] == 370
assert mut["by_pair"]["arithmetic_width"]["exact_identity_runs"] == 12
assert mut["by_pair"]["reset_state"]["exact_identity_runs"] == 74
for r in mut["rows"]:
    assert 0.0 <= r["boundary_jaccard"] <= 1.0
    assert 0.0 <= r["content_addressed_migration_reuse"] <= 1.0
print("Cross-component mutation suite: 5 rule-difference classes / 370 real-source runs PASS")

# 14) Finite-memory reset-state convergence and transient witness.
# For equal bytes/table, delta_{t+1}=2*delta_t mod 2^w, hence delta_w=0.
from boundary_stream import GEAR as PRIMARY_GEAR
rng = random.Random(424242)
for _ in range(100):
    a, b = rng.getrandbits(64), rng.getrandbits(64)
    for _t in range(64):
        byte = rng.randrange(256)
        a = ((a << 1) + PRIMARY_GEAR[byte]) & ((1 << 64) - 1)
        b = ((b << 1) + PRIMARY_GEAR[byte]) & ((1 << 64) - 1)
    assert a == b
with open(os.path.join(RES, "reset_state_transient_witness.json"), encoding="utf-8") as f:
    rw = json.load(f)
assert rw["candidate_update_index_one_based"] < rw["convergence_bound_updates"]
assert rw["decision_a_cut"] != rw["decision_b_cut"]
assert rw["convergence_bound_updates"] == 64
print("Reset-state liveness: 64-update convergence bound + transient divergence witness PASS")

# 15) Machine-checkable Rule Compatibility Certificate (RCC-1.0).
from verify_compatibility_certificate import main as verify_rcc
verify_rcc()
print("Rule Compatibility Certificate: offline verification PASS")
print("CORE SELF-CHECK PASS")

# 16) Independent literal-Algorithm-1 regression check against a separately coded executor.
def _paper_algorithm1_boundaries(data: bytes, pre_mask: int, gear: list[int]) -> list[int]:
    bounds=[0]
    start=0
    total=len(data)
    while start<total:
        n=total-start
        if n<=2048:
            bounds.append(total)
            break
        if n>=65536:
            n=65536
        normal=8192 if n>8192 else n
        fp=0
        i=2048
        cut=None
        while i<normal:
            fp=((fp<<1)+gear[data[start+i]]) & ((1<<64)-1)
            if (fp & pre_mask)==0:
                cut=i
                break
            i+=1
        if cut is None:
            while i<n:
                fp=((fp<<1)+gear[data[start+i]]) & ((1<<64)-1)
                if (fp & MASK_L)==0:
                    cut=i
                    break
                i+=1
        if cut is None:
            cut=i
        bounds.append(start+cut)
        start+=cut
    return bounds

for rep in range(3):
    for name,data in make_workloads(size=131072,replicate=rep).items():
        assert _paper_algorithm1_boundaries(data, BS16, PRIMARY_GEAR) == chunk_boundaries(data, BS16)
        assert _paper_algorithm1_boundaries(data, BS20, PRIMARY_GEAR) == chunk_boundaries(data, BS20)
print('Published Algorithm-1 indexing convention: independent executor cross-check PASS')

# 17) Packaged non-synthetic source-code corpus is internally reproducible.
with open(os.path.join(RES, 'real_source_validation.json'), encoding='utf-8') as f:
    real_obj=json.load(f)
assert real_obj['summary']['n_files'] == 74
assert real_obj['summary']['total_bytes'] == 1578537
for row in real_obj['rows']:
    path=os.path.join(ROOT,'corpus','go1232_stdlib',row['file'])
    data=open(path,'rb').read()
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    b16=chunk_boundaries(data,BS16); b20=chunk_boundaries(data,BS20)
    assert (b16==b20) == row['exact_boundary_identity']
    assert abs(stream_metrics(b16,b20,len(data))['boundary_jaccard']-row['boundary_jaccard']) < 1e-15
    assert abs(content_addressed_migration_reuse(data,b16,b20)-row['content_addressed_migration_reuse']) < 1e-15
print('Packaged Go source corpus: hashes and migration metrics PASS')
print('SELF-CHECK PASS')
