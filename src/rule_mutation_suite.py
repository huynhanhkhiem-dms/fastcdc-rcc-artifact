"""Cross-component rule-mutation validation on a packaged real-source corpus.

The corpus contains every non-test .go file from five fixed Go 1.23.2 standard-
library packages included in this archive. The suite broadens validation beyond
one historical pre-target-mask change. The minimum-size, reset-state, and
arithmetic-width variants are controlled stress tests, not prevalence claims.
"""
from __future__ import annotations

import csv
import json
import os
import statistics

from boundary_stream import (
    GEAR, MASK_S_2016, MASK_S_2020, MASK_L, MIN_SIZE, AVG_SIZE, MAX_SIZE,
    stream_metrics, content_addressed_migration_reuse,
)
from gear_sensitivity import WXI_GEAR
from rule_model import Rule, chunk_boundaries, descriptor_differences

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORPUS = os.path.join(ROOT, "corpus", "go1232_stdlib")
OUT_JSON = os.path.join(ROOT, "results", "rule_mutation_suite.json")
OUT_CSV = os.path.join(ROOT, "results", "rule_mutation_suite.csv")


def corpus_files() -> list[str]:
    paths=[]
    for base, _, names in os.walk(CORPUS):
        for name in names:
            if name.endswith(".go"):
                paths.append(os.path.join(base, name))
    return sorted(paths)


def mk_rule(name: str, *, gear=GEAR, pre=MASK_S_2016, post=MASK_L,
            min_size=MIN_SIZE, avg_size=AVG_SIZE, max_size=MAX_SIZE,
            word_bits=64, reset_state=0) -> Rule:
    return Rule(
        name=name, gear=tuple(gear), pre_mask=pre, post_mask=post,
        min_size=min_size, avg_size=avg_size, max_size=max_size,
        word_bits=word_bits, reset_state=reset_state,
    )


def pairs() -> list[tuple[str, str, Rule, Rule]]:
    base = mk_rule("baseline_2016_mask_rust_gear")
    return [
        ("published_pre_mask",
         "Published 2016-to-2020 pre-target mask substitution; other controlled semantics fixed.",
         base, mk_rule("published_2020_pre_mask", pre=MASK_S_2020)),
        ("public_gear_table",
         "Public Gear-table substitution; masks and schedule fixed.",
         base, mk_rule("wxi_public_gear", gear=WXI_GEAR)),
        ("minimum_size_schedule",
         "Controlled minimum-size perturbation from 2 KiB to 4 KiB.",
         base, mk_rule("min_4k", min_size=4096)),
        ("reset_state",
         "Controlled reset-state perturbation; stress test of rule identity.",
         base, mk_rule("nonzero_reset", reset_state=0x9E3779B97F4A7C15)),
        ("arithmetic_width",
         "Controlled 64-bit-to-32-bit arithmetic perturbation.",
         base, mk_rule("word32", word_bits=32)),
    ]


def main() -> None:
    files=corpus_files()
    if not files:
        raise RuntimeError("packaged Go corpus is empty")
    rows=[]
    pair_meta={}
    for pair_id, description, old_rule, new_rule in pairs():
        pair_meta[pair_id]={
            "description": description,
            "old_fingerprint": old_rule.fingerprint(),
            "new_fingerprint": new_rule.fingerprint(),
            "descriptor_differences": descriptor_differences(old_rule, new_rule),
        }
        for path in files:
            rel=os.path.relpath(path,CORPUS).replace(os.sep,"/")
            data=open(path,"rb").read()
            bo=chunk_boundaries(data,old_rule)
            bn=chunk_boundaries(data,new_rule)
            sm=stream_metrics(bo,bn,len(data))
            rows.append({
                "pair":pair_id,"file":rel,"bytes":len(data),
                "boundary_jaccard":sm["boundary_jaccard"],
                "boundary_exact_identity":int(bo==bn),
                "divergent_byte_fraction":sm["divergent_byte_fraction"],
                "content_addressed_migration_reuse":content_addressed_migration_reuse(data,bo,bn),
            })

    by_pair={}
    for pair_id, _, _, _ in pairs():
        rr=[r for r in rows if r["pair"]==pair_id]
        by_pair[pair_id]={
            "n_runs":len(rr),
            "exact_identity_runs":sum(r["boundary_exact_identity"] for r in rr),
            "boundary_jaccard_median":statistics.median(r["boundary_jaccard"] for r in rr),
            "boundary_jaccard_range":[min(r["boundary_jaccard"] for r in rr),max(r["boundary_jaccard"] for r in rr)],
            "divergent_byte_fraction_median":statistics.median(r["divergent_byte_fraction"] for r in rr),
            "divergent_byte_fraction_range":[min(r["divergent_byte_fraction"] for r in rr),max(r["divergent_byte_fraction"] for r in rr)],
            "migration_reuse_median":statistics.median(r["content_addressed_migration_reuse"] for r in rr),
            "migration_reuse_range":[min(r["content_addressed_migration_reuse"] for r in rr),max(r["content_addressed_migration_reuse"] for r in rr)],
        }

    obj={
        "design":{
            "corpus":"all packaged non-test .go files from archive/zip, compress/flate, crypto/tls, encoding/json, and net/http in Go 1.23.2",
            "n_files":len(files),
            "pair_count":len(pair_meta),
            "total_runs":len(rows),
            "scope_note":"The corpus is a fixed real-source validation set, not a probability sample. Three semantic/configuration perturbations are controlled stress tests.",
        },
        "pairs":pair_meta,"rows":rows,"by_pair":by_pair,
    }
    with open(OUT_JSON,"w",encoding="utf-8") as f: json.dump(obj,f,indent=2)
    with open(OUT_CSV,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(json.dumps({"design":obj["design"],"by_pair":by_pair},indent=2))


if __name__=="__main__":
    main()
