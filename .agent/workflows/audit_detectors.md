---
description: Audit and verify all ICT detectors against validation data
---

1. Run the detector verification script
// turbo
```bash
source .venv/bin/activate
python scripts/debug/verify_detectors.py
```

2. Run the specific detector test suite
// turbo
```bash
pytest scripts/tests/test_detectors.py
```
