---
description: Testing Conventions T-01/T-02/T-03
---

# Testing Conventions

```bash
grep -rn "^from aifw\|^from promptfw" src/
grep -rn "AsyncMock(wraps=" src/
pytest src/ -v --tb=short
```
