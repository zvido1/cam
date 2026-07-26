# Step 448 — Input/Output hash record (Task 0)

Independent post-run validation, not emitted by the sanctioned harness. Read-only against run outputs.

## ENTRY record (before any analysis)

```
$ python build_log/448_hash_artifacts.py ENTRY
```

| artifact | bytes | SHA-256 |
|---|---|---|
| `build_log/431_selection_measurement_sidecar.json` | 818521 | `c44573cb56d990afe7818dbdbfc3aa1e9586e51331a86b348b97f0e55967a9e7` |
| `build_log/431_runtime_seam_capture.json` | 533 | `01e0427e187b658d07947978b30e6bb8a78b9e2f0551180d00cde364d10ec981` |
| `build_log/431_selection_measurement.md` | 5298 | `8f469cec0d5d50fcfbfdaf65b4c53c1034640e58b0cf07092b4fb8d47bfe3603` |
| `build_log/431_validation.json` | -- | **NOT PRODUCED** |
| `build_log/431_repository_seam_check.json` | -- | **NOT PRODUCED** |
| `build_log/431_fatal_run_error.json` | -- | **NOT PRODUCED** |

## EXIT record (end of step; all audit operations were read-only)

```
$ python build_log/448_hash_artifacts.py EXIT
```

| artifact | bytes | SHA-256 |
|---|---|---|
| `build_log/431_selection_measurement_sidecar.json` | 818521 | `c44573cb56d990afe7818dbdbfc3aa1e9586e51331a86b348b97f0e55967a9e7` |
| `build_log/431_runtime_seam_capture.json` | 533 | `01e0427e187b658d07947978b30e6bb8a78b9e2f0551180d00cde364d10ec981` |
| `build_log/431_selection_measurement.md` | 5298 | `8f469cec0d5d50fcfbfdaf65b4c53c1034640e58b0cf07092b4fb8d47bfe3603` |
| `build_log/431_validation.json` | -- | **NOT PRODUCED** |
| `build_log/431_repository_seam_check.json` | -- | **NOT PRODUCED** |
| `build_log/431_fatal_run_error.json` | -- | **NOT PRODUCED** |
