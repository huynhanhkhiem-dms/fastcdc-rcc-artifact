from __future__ import annotations
import hashlib, json, os
from boundary_stream import make_workloads, chunk_boundaries, MASK_S_2016, MASK_S_2020

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "conformance_vectors.json")
VECTOR_BYTES = 256 * 1024
WORKLOADS = ["uniform", "ascii64", "source_like", "repeated_text", "low_entropy", "repeated_blocks"]

def main():
    generated = make_workloads(size=VECTOR_BYTES, replicate=0)
    cases=[]
    for name in WORKLOADS:
        data=generated[name]
        cases.append({
            "workload": name,
            "replicate_zero_based": 0,
            "bytes": len(data),
            "input_sha256": hashlib.sha256(data).hexdigest(),
            "boundaries_2016": chunk_boundaries(data, MASK_S_2016),
            "boundaries_2020": chunk_boundaries(data, MASK_S_2020),
        })
    obj={
        "purpose": "Portable conformance vectors for independent implementations of the controlled rule pair",
        "boundary_convention": "hash src[i], test, return relative i; absolute end-exclusive boundary=start+i; tested src[i] belongs to following chunk",
        "chunk_sizes": {"min": 2048, "target": 8192, "max": 65536},
        "masks": {"pre_2016": "0x0003590703530000", "pre_2020": "0x0000d9f003530000", "post_shared": "0x0000d90003530000"},
        "gear_table": "rust-gearhash DEFAULT_TABLE at commit d8fe811678f2f129fbccca647bac6f691ef8490f",
        "cases": cases,
    }
    with open(OUT,"w",encoding="utf-8") as f: json.dump(obj,f,indent=2)
    print(json.dumps({"n_cases":len(cases),"output":OUT},indent=2))

if __name__ == "__main__": main()
