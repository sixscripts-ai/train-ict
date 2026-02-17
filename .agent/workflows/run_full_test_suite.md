---
description: Run the full QA suite (tests, types, formatting)
---

1. Run Pytest (Unit Tests)
// turbo
```bash
source .venv/bin/activate
pytest
```

2. Run MyPy (Type Checking)
// turbo
```bash
mypy .
```

3. Run Black (Format Check)
// turbo
```bash
black --check .
```
