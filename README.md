# RCC 1.1 FastCDC Reproducibility Artifact

This public repository archives the code, corpus, result tables, conformance vectors, compatibility certificate, figures, and self-check scripts supporting the manuscript submitted to *Software: Practice and Experience*.

## Reproduce

Download `Supplementary_Material.zip`, extract it, and run:

```bash
python src/selfcheck.py
```

The self-check validates the RCC 1.1 compatibility certificate, independent boundary executor, constructive inequivalence witness, reset-state transient witness, rule-mutation suite, Gear-table sensitivity study, packaged Go-source corpus hashes, migration metrics, and conformance vectors.

## Archive contents

- `src/` - analysis, certificate generation/verification, witnesses, figures, and self-check code
- `corpus/` - frozen Go 1.23.2 standard-library source corpus used by the study
- `results/` - CSV/JSON outputs, conformance vectors, compatibility certificate, and witnesses
- `figures/` - figures generated from the archived outputs
- `requirements.txt` - Python dependencies
- `README.txt` - detailed reproduction notes

## Reproducibility status

The archived package was self-checked before publication and completed with `SELF-CHECK PASS`.

## Author

Huynh Anh Khiem  
Faculty of Information Technology, Ton Duc Thang University, Ho Chi Minh City, Vietnam  
ORCID: 0009-0007-7210-174X

## Third-party material

The packaged Go standard-library source files retain the Go project's license notice in `corpus/go1232_stdlib/LICENSE_GO.txt`.
