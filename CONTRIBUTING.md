# Contributing

Contributions should preserve three principles:

1. Patient text stays local.
2. Unsupported evidence cannot produce `MET`.
3. The project is described as a pre-screen, never an adjudicator.

Before opening a pull request:

```bash
python -m pip install -r requirements-dev.txt
make check
```

Use synthetic fixtures only. Do not include real clinical documents, credentials,
downloaded model files, or local runtime databases.
