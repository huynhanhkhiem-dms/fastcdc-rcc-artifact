# Reproducibility Artifact

## A Machine-Checkable Compatibility Certificate for Deterministic Content-Defined Chunking Migrations

SUPPLEMENTARY MATERIAL
A Machine-Checkable Compatibility Certificate for Deterministic Content-Defined Chunking Migrations

Purpose
-------
This archive reproduces the formal, empirical, and source-provenance evidence
reported in the manuscript. Its central artifact is Rule Compatibility
Certificate (RCC) 1.1 for deterministic reset-based content-defined chunking
(CDC) migrations.

RCC 1.1 stores the complete registered boundary semantics in canonical form,
including the full 256-entry Gear table. SHA-256 rule fingerprints are compact
integrity identifiers over those complete descriptors; digest equality is not
the logical premise of the equivalence result.

Boundary convention
-------------------
The controlled FastCDC executor follows the literal index convention printed in
Algorithm 1 of the 2016 and 2020 FastCDC publications. For a chunk starting at
absolute offset s, the candidate index i starts at min_size. The executor:

  1. updates the Gear state using src[s + i],
  2. tests the active acceptance mask, and
  3. returns i when the test succeeds.

The emitted end-exclusive boundary is therefore s + i. The tested candidate
byte src[s + i] influences the decision but belongs to the following chunk.
This convention is explicitly recorded in every RCC 1.1 descriptor and in the
portable conformance vectors.

Primary real-source validation corpus
-------------------------------------
The archive includes every non-test .go file from five fixed packages in the Go
1.23.2 standard library:

  archive/zip
  compress/flate
  crypto/tls
  encoding/json
  net/http

The packaged corpus contains 74 source files and 1,578,537 bytes. GO_VERSION.txt
records the Go release and LICENSE_GO.txt contains the upstream license. The
corpus is a fixed, reproducible real-source validation set, not a probability
sample of production storage workloads.

For the printed 2016-versus-2020 pre-target-mask substitution under the primary
frozen Gear table, 48 of 74 files have exactly identical boundary streams. Over
all 74 files, both boundary Jaccard similarity and content-addressed same-content
reuse range from 0 to 1. These results illustrate file-level heterogeneity; they
do not estimate deployment prevalence.

RCC 1.1 evidence semantics
--------------------------
1. Complete descriptor identity. For the registered deterministic executor,
   fieldwise identity of complete canonical rule descriptors is a sufficient
   premise for identical boundaries on every finite input.

2. Constructive inequivalence. If descriptors differ, a verified jointly
   live-reachable candidate at which the declared rules make different decisions
   disproves universal equivalence.

3. Workload-scoped replay. Replay quantifies only the declared files, rule pair,
   migration direction, and reuse definition. A successful replay sample is not
   promoted to a universal compatibility statement.

Primary FastCDC witness
-----------------------
For the printed FastCDC pre-target masks and the registered executor, the
artifact regenerates a jointly live-reachable witness after a shared reset at
absolute offset 18,528. At boundary offset 22,278, the common 64-bit state is
0x35d8a0b88480ebe0. The 2016 pre-target mask accepts this state and the 2020
pre-target mask rejects it.

Finite-memory reset-state result
--------------------------------
For the Gear recurrence

  H_(t+1) = 2 H_t + G(b_t) mod 2^w,

two executions receiving the same bytes and table but starting from reset states
H_0 and H'_0 satisfy

  H_t - H'_t = 2^t (H_0 - H'_0) mod 2^w.

Hence their states coincide after w common hash updates. With w = 64, reset-state
influence is transient, but it may still change an earlier decision. The
packaged constructive witness differs at update 27. In contrast, the real-source
mutation replay is boundary-identical for all 74 files under the tested reset-
state pair. This is the paper's direct example of why finite replay cannot serve
as a universal equivalence certificate.

Archive contents
----------------
src/rule_model.py
  RCC 1.1 descriptor schema, full Gear-table serialization, descriptor
  validation, canonical fingerprints, descriptor differences, descriptor-to-
  rule reconstruction, and the registered deterministic executor.

src/make_compatibility_certificate.py
src/verify_compatibility_certificate.py
  Generate and independently verify the RCC 1.1 certificate. The verifier checks
  full descriptor integrity and round-trip reconstruction, rule fingerprints,
  descriptor differences, constructive witness regeneration, and bound evidence
  hashes.

src/real_source_validation.py
  Replays the printed FastCDC mask pair on all 74 packaged Go source files and
  writes per-file plus per-package metrics.

src/rule_mutation_suite.py
  Replays five boundary-defining rule-difference classes on the 74-file real
  corpus (370 runs total): printed pre-target mask, public Gear table, minimum
  size, reset state, and arithmetic width.

src/gear_sensitivity.py
  Replays the printed mask pair on the same 74 files under five Gear tables
  (370 runs total): two frozen public tables and three deterministic probes.

src/boundary_stream.py
  Deterministic designed-workload mechanism probes retained for witness
  extraction and stress testing. These generated workloads are supporting
  diagnostics rather than the primary real-source validation corpus.

src/make_inequivalence_witness.py
  Regenerates the primary jointly live-reachable FastCDC mask-pair witness.

src/make_reset_state_witness.py
  Deterministically searches the finite reset-state transient window and writes
  the update-27 differing-decision witness.

src/make_conformance_vectors.py
  Produces portable input digests and expected boundaries for the registered
  executor and both printed FastCDC pre-target masks.

src/mask_geometry.py
  Reproduces exact acceptance-set calculations used only as supporting static
  diagnostics; these calculations are not presented as a new metric.

src/selfcheck.py
  Runs the offline integrity suite. It includes an independently coded literal
  FastCDC Algorithm-1 executor cross-check, RCC 1.1 verification, descriptor
  checks, witness regeneration, real-corpus hash/metric recomputation, mutation
  checks, conformance vectors, and the 64-update reset-state convergence check.
  A successful complete run ends with SELF-CHECK PASS.

src/verify_public_audit.py
  Optional networked verifier for immutable GitHub revisions in the frozen
  public-source audit. No network access is needed for the manuscript results.

src/make_figures.py
  Regenerates the two primary real-source figures from
  results/real_source_validation.json.

corpus/go1232_stdlib/
  Packaged Go 1.23.2 source files, release marker, and upstream license.

results/
  Machine-readable outputs for RCC 1.1, real-source replay, mutation validation,
  Gear sensitivity, witnesses, conformance vectors, supporting designed-workload
  probes, mask diagnostics, and the frozen public implementation audit.

figures/
  Publication figures in PDF and PNG formats.

requirements.txt
  Pins matplotlib for figure regeneration. Analytical and verification code uses
  the Python standard library.

Frozen external source provenance
---------------------------------
Primary Gear table:
  srijs/rust-gearhash, src/table.rs, DEFAULT_TABLE
  commit d8fe811678f2f129fbccca647bac6f691ef8490f

Second public Gear table:
  wxiacode/FastCDC-c, fastcdc.h, GEARv2
  commit 7d661508aeef2d9be3c7fc6e4b94325ef90205c5

The immutable source-audit snapshot in
results/public_implementation_audit.csv records six additional code-lineage
checks used only to establish that both printed mask lineages remain observable
in accessible software. It does not establish prevalence or complete behavioral
identity of those repositories.

Reproduction
------------
From the archive root, use Python 3.10 or newer:

  python src/mask_geometry.py
  python src/boundary_stream.py
  python src/real_source_validation.py
  python src/gear_sensitivity.py
  python src/rule_mutation_suite.py
  python src/make_conformance_vectors.py
  python src/make_inequivalence_witness.py
  python src/make_reset_state_witness.py
  python src/make_compatibility_certificate.py
  python src/verify_compatibility_certificate.py
  python src/selfcheck.py
  python src/make_figures.py

Optional networked provenance check:

  python src/verify_public_audit.py

Expected integrity checks
-------------------------
A complete offline self-check must report, among other lines:

  Gear-table sensitivity: 5 tables / 370 real-source runs structural checks PASS
  Cross-component mutation suite: 5 rule-difference classes / 370 real-source runs PASS
  Reset-state liveness: 64-update convergence bound + transient divergence witness PASS
  RCC-1.1 VERIFICATION PASS
  Published Algorithm-1 indexing convention: independent executor cross-check PASS
  Packaged Go source corpus: hashes and migration metrics PASS
  SELF-CHECK PASS

Interpretation boundary
-----------------------
RCC 1.1 does not claim that different descriptors are necessarily behaviorally
different. Descriptor identity is a sufficient, not necessary, equivalence
condition for the registered schema. A constructive witness establishes possible
divergence. Replay reports compatibility only for the named content and
migration direction. The public-source audit is an existence audit rather than
a census. The packaged Go corpus is real source code but is not a statistical
sample of deployed deduplication workloads.

Contact
-------
Huynh Anh Khiem
Faculty of Information Technology, Ton Duc Thang University
Ho Chi Minh City, Vietnam
huynhanhkhiem@tdtu.edu.vn
ORCID: 0009-0007-7210-174X


PUBLIC REPOSITORY
-----------------
The complete reproducibility artifact is archived at:
https://github.com/huynhanhkhiem-dms/fastcdc-rcc-artifact
