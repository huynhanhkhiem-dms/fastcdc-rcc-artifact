"""Canonical rule model and registered deterministic FastCDC executor.

RCC-1.1 stores the complete declared boundary semantics used by this artifact.
The 256-entry Gear table is embedded fieldwise in the canonical descriptor;
its SHA-256 is retained only as an integrity/checking convenience.  Therefore
universal identity is established by descriptor equality, not by assuming that
a hash digest is collision-free as a matter of logic.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

EXECUTOR_ID = "fastcdc_published_index_v1"
DESCRIPTOR_SCHEMA = "rcc-rule-1.1"


def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def gear_table_sha256(gear: Iterable[int], word_bits: int = 64) -> str:
    nbytes = (word_bits + 7) // 8
    mask = (1 << word_bits) - 1
    vals = list(gear)
    if len(vals) != 256:
        raise ValueError("Gear table must contain exactly 256 entries")
    h = hashlib.sha256()
    for x in vals:
        h.update((x & mask).to_bytes(nbytes, "big"))
    return h.hexdigest()


@dataclass(frozen=True)
class Rule:
    name: str
    gear: tuple[int, ...]
    pre_mask: int
    post_mask: int
    min_size: int
    avg_size: int
    max_size: int
    word_bits: int = 64
    reset_state: int = 0
    executor_id: str = EXECUTOR_ID
    transition: str = "H_next=(2*H+Gear[byte]) mod 2^w"

    def __post_init__(self) -> None:
        if len(self.gear) != 256:
            raise ValueError("Gear table must contain exactly 256 entries")
        if not (0 < self.min_size <= self.avg_size <= self.max_size):
            raise ValueError("require 0 < min_size <= avg_size <= max_size")
        if self.word_bits <= 0 or self.word_bits % 8 != 0:
            raise ValueError("word_bits must be a positive multiple of 8")
        if self.executor_id != EXECUTOR_ID:
            raise ValueError(f"unsupported executor_id: {self.executor_id}")

    def descriptor(self) -> dict:
        width_hex = max(1, self.word_bits // 4)
        mask = (1 << self.word_bits) - 1
        gear_hex = [f"0x{x & mask:0{width_hex}x}" for x in self.gear]
        return {
            "schema": DESCRIPTOR_SCHEMA,
            "executor_id": self.executor_id,
            "word_bits": self.word_bits,
            "arithmetic": f"unsigned modulo 2^{self.word_bits}",
            "gear_table_encoding": f"256 unsigned {self.word_bits}-bit integers in byte-value order 0..255",
            "gear_table_hex": gear_hex,
            "gear_table_sha256": gear_table_sha256(self.gear, self.word_bits),
            "transition": self.transition,
            "reset_state_hex": f"0x{self.reset_state & mask:0{width_hex}x}",
            "skipped_prefix_rule": "bytes at relative indices 0..min_size-1 are not hashed or tested",
            "candidate_index_initial": "i=min_size",
            "candidate_update_rule": "update state with src[i], then test the active mask",
            "pre_target_test_interval": "min_size <= i < min(avg_size, capped_remaining)",
            "post_target_test_interval": "min(avg_size, capped_remaining) <= i < capped_remaining",
            "acceptance_predicate": "(state & active_mask)==0",
            "accepted_boundary_rule": "return relative index i; candidate byte src[i] is not included in the preceding chunk",
            "boundary_coordinate": "end-exclusive absolute boundary=start+i",
            "next_chunk_rule": "next chunk starts at the returned absolute boundary and resets state",
            "min_tail_rule": "if remaining<=min_size return remaining",
            "maximum_rule": "capped_remaining=min(remaining,max_size); if no candidate accepts return capped_remaining",
            "eof_rule": "final returned boundary equals input length",
            "min_size": self.min_size,
            "avg_size": self.avg_size,
            "max_size": self.max_size,
            "pre_target_mask_hex": f"0x{self.pre_mask & mask:0{width_hex}x}",
            "post_target_mask_hex": f"0x{self.post_mask & mask:0{width_hex}x}",
        }

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.descriptor())).hexdigest()


def validate_descriptor(desc: dict) -> None:
    required = {
        "schema", "executor_id", "word_bits", "arithmetic", "gear_table_encoding",
        "gear_table_hex", "gear_table_sha256", "transition", "reset_state_hex",
        "skipped_prefix_rule", "candidate_index_initial", "candidate_update_rule",
        "pre_target_test_interval", "post_target_test_interval", "acceptance_predicate",
        "accepted_boundary_rule", "boundary_coordinate", "next_chunk_rule",
        "min_tail_rule", "maximum_rule", "eof_rule", "min_size", "avg_size",
        "max_size", "pre_target_mask_hex", "post_target_mask_hex",
    }
    missing = sorted(required - set(desc))
    extra = sorted(set(desc) - required)
    if missing or extra:
        raise ValueError(f"descriptor fields mismatch; missing={missing}, extra={extra}")
    if desc["schema"] != DESCRIPTOR_SCHEMA or desc["executor_id"] != EXECUTOR_ID:
        raise ValueError("unsupported descriptor schema/executor")
    if len(desc["gear_table_hex"]) != 256:
        raise ValueError("descriptor must embed exactly 256 Gear entries")
    rule = rule_from_descriptor(desc, name="descriptor_validation")
    if rule.descriptor() != desc:
        raise ValueError("descriptor does not round-trip canonically")


def rule_from_descriptor(desc: dict, name: str = "from_descriptor") -> Rule:
    if desc.get("schema") != DESCRIPTOR_SCHEMA or desc.get("executor_id") != EXECUTOR_ID:
        raise ValueError("unsupported descriptor schema/executor")
    word_bits = int(desc["word_bits"])
    gear = tuple(int(x, 16) for x in desc["gear_table_hex"])
    rule = Rule(
        name=name,
        gear=gear,
        pre_mask=int(desc["pre_target_mask_hex"], 16),
        post_mask=int(desc["post_target_mask_hex"], 16),
        min_size=int(desc["min_size"]),
        avg_size=int(desc["avg_size"]),
        max_size=int(desc["max_size"]),
        word_bits=word_bits,
        reset_state=int(desc["reset_state_hex"], 16),
        executor_id=desc["executor_id"],
        transition=desc["transition"],
    )
    expected_digest = gear_table_sha256(rule.gear, word_bits)
    if expected_digest != desc["gear_table_sha256"]:
        raise ValueError("Gear table digest does not match embedded entries")
    return rule


def descriptor_differences(a: Rule, b: Rule) -> dict:
    da, db = a.descriptor(), b.descriptor()
    keys = sorted(set(da) | set(db))
    return {k: {"old": da.get(k), "new": db.get(k)} for k in keys if da.get(k) != db.get(k)}


def chunk_boundaries(data: bytes, rule: Rule) -> list[int]:
    """Execute Algorithm-1 indexing semantics used in FastCDC 2016/2020.

    Within each chunk-local source buffer, i starts at min_size.  The executor
    updates the Gear state with src[i], tests the active mask, and on acceptance
    returns i.  The returned value is the chunk length/end-exclusive boundary,
    so the candidate byte src[i] influences the decision but belongs to the
    following chunk.  This seemingly unusual convention is deliberately frozen
    because it matches the published pseudocode and the v2016 reference-style
    implementation checked in the study.
    """
    # Force canonical validation of every executable rule.
    validate_descriptor(rule.descriptor())

    width_mask = (1 << rule.word_bits) - 1
    gear = [x & width_mask for x in rule.gear]
    pre_mask = rule.pre_mask & width_mask
    post_mask = rule.post_mask & width_mask
    reset = rule.reset_state & width_mask

    bounds = [0]
    start = 0
    n_total = len(data)
    while start < n_total:
        remaining = n_total - start
        if remaining <= rule.min_size:
            bounds.append(n_total)
            break

        capped = min(remaining, rule.max_size)
        normal = min(rule.avg_size, capped)
        i = rule.min_size
        fp = reset
        cut_rel = None

        while i < normal:
            fp = ((fp << 1) + gear[data[start + i]]) & width_mask
            if (fp & pre_mask) == 0:
                cut_rel = i
                break
            i += 1

        if cut_rel is None:
            while i < capped:
                fp = ((fp << 1) + gear[data[start + i]]) & width_mask
                if (fp & post_mask) == 0:
                    cut_rel = i
                    break
                i += 1

        if cut_rel is None:
            cut_rel = capped

        cut_abs = start + cut_rel
        if cut_abs <= start:
            raise AssertionError("executor produced a non-progressing boundary")
        bounds.append(cut_abs)
        start = cut_abs

    if bounds[-1] != n_total:
        bounds.append(n_total)
    return bounds
