"""Validation on a packaged, real open-source source-code corpus.

The corpus is a byte-for-byte snapshot of all non-test Go 1.23.2 standard-library source files from five fixed packages shipped with this supplementary package.  It is
not a probability sample of production storage.  Its purpose is to complement
the designed workloads with non-synthetic source-code bytes that can be replayed
offline without external downloads.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics

from boundary_stream import (
    MASK_S_2016, MASK_S_2020, chunk_boundaries, stream_metrics,
    content_addressed_migration_reuse, shannon_entropy,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORPUS = os.path.join(ROOT, "corpus", "go1232_stdlib")
OUT_JSON = os.path.join(ROOT, "results", "real_source_validation.json")
OUT_CSV = os.path.join(ROOT, "results", "real_source_validation.csv")


def source_files() -> list[str]:
    out=[]
    for base, _, files in os.walk(CORPUS):
        for name in files:
            if name.endswith(".go"):
                out.append(os.path.join(base, name))
    return sorted(out)


def main() -> None:
    rows=[]
    manifest=[]
    for path in source_files():
        rel=os.path.relpath(path, CORPUS).replace(os.sep, "/")
        data=open(path,"rb").read()
        b16=chunk_boundaries(data, MASK_S_2016)
        b20=chunk_boundaries(data, MASK_S_2020)
        sm=stream_metrics(b16,b20,len(data))
        reuse=content_addressed_migration_reuse(data,b16,b20)
        rows.append({
            "file":rel,
            "bytes":len(data),
            "sha256":hashlib.sha256(data).hexdigest(),
            "byte_entropy":shannon_entropy(data),
            "exact_boundary_identity":b16==b20,
            "chunks_2016":len(b16)-1,
            "chunks_2020":len(b20)-1,
            "boundary_jaccard":sm["boundary_jaccard"],
            "divergent_byte_fraction":sm["divergent_byte_fraction"],
            "content_addressed_migration_reuse":reuse,
        })
        manifest.append({"file":rel,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})

    obj={
        "corpus":{
            "name":"Go 1.23.2 standard-library non-test source files from five fixed packages: archive/zip, compress/flate, crypto/tls, encoding/json, net/http",
            "purpose":"non-synthetic offline validation; not a population sample",
            "license_file":"corpus/go1232_stdlib/LICENSE_GO.txt",
            "version_file":"corpus/go1232_stdlib/GO_VERSION.txt",
            "files":manifest,
        },
        "rows":rows,
        "by_package": {pkg: {
            "n_files": sum(1 for r in rows if r["file"].startswith(pkg + "/")),
            "total_bytes": sum(r["bytes"] for r in rows if r["file"].startswith(pkg + "/")),
            "exact_identity_files": sum(bool(r["exact_boundary_identity"]) for r in rows if r["file"].startswith(pkg + "/")),
            "boundary_jaccard_median": statistics.median(r["boundary_jaccard"] for r in rows if r["file"].startswith(pkg + "/")),
            "boundary_jaccard_range": [min(r["boundary_jaccard"] for r in rows if r["file"].startswith(pkg + "/")), max(r["boundary_jaccard"] for r in rows if r["file"].startswith(pkg + "/"))],
            "migration_reuse_median": statistics.median(r["content_addressed_migration_reuse"] for r in rows if r["file"].startswith(pkg + "/")),
            "migration_reuse_range": [min(r["content_addressed_migration_reuse"] for r in rows if r["file"].startswith(pkg + "/")), max(r["content_addressed_migration_reuse"] for r in rows if r["file"].startswith(pkg + "/"))],
        } for pkg in ["archive/zip","compress/flate","crypto/tls","encoding/json","net/http"]},
        "summary":{
            "n_files":len(rows),
            "total_bytes":sum(r["bytes"] for r in rows),
            "exact_identity_files":sum(bool(r["exact_boundary_identity"]) for r in rows),
            "boundary_jaccard_median":statistics.median(r["boundary_jaccard"] for r in rows),
            "boundary_jaccard_range":[min(r["boundary_jaccard"] for r in rows),max(r["boundary_jaccard"] for r in rows)],
            "migration_reuse_median":statistics.median(r["content_addressed_migration_reuse"] for r in rows),
            "migration_reuse_range":[min(r["content_addressed_migration_reuse"] for r in rows),max(r["content_addressed_migration_reuse"] for r in rows)],
        },
    }
    with open(OUT_JSON,"w",encoding="utf-8") as f: json.dump(obj,f,indent=2)
    with open(OUT_CSV,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(json.dumps(obj["summary"],indent=2))


if __name__=="__main__": main()
