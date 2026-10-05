"""Optional online verification of the frozen public-code audit.

This script is intentionally separate from selfcheck.py. It downloads each
immutable GitHub source revision named in results/public_implementation_audit.csv
and confirms that the recorded strict and relaxed mask constants occur in that
frozen source. Network access is required.
"""
from __future__ import annotations

import csv
import os
import re
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIT = os.path.join(ROOT, "results", "public_implementation_audit.csv")


def raw_url(repository: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"


def normalize_hex(text: str) -> str:
    return re.sub(r"[^0-9a-f]", "", text.lower().removeprefix("0x"))


def source_contains_hex(source: str, value: str) -> bool:
    target = normalize_hex(value).lstrip("0") or "0"
    # Accept source spellings with optional leading zeros, 0x prefix, and ULL/u64 suffixes.
    for token in re.findall(r"0x[0-9a-fA-F]+", source):
        got = normalize_hex(token).lstrip("0") or "0"
        if got == target:
            return True
    return False


def main() -> None:
    with open(AUDIT, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    failures = []
    for row in rows:
        url = raw_url(row["repository"], row["commit"], row["path"])
        with urllib.request.urlopen(url, timeout=20) as response:
            source = response.read().decode("utf-8", errors="replace")
        ok_s = source_contains_hex(source, row["mask_s_hex"])
        ok_l = source_contains_hex(source, row["mask_l_hex"])
        print(f"{row['repository']} {row['commit'][:12]}: MaskS={ok_s} MaskL={ok_l}")
        if not (ok_s and ok_l):
            failures.append(row["repository"])
    if failures:
        raise SystemExit("REMOTE AUDIT VERIFICATION FAILED: " + ", ".join(failures))
    print(f"REMOTE AUDIT VERIFICATION PASS ({len(rows)}/{len(rows)} frozen revisions)")


if __name__ == "__main__":
    main()
