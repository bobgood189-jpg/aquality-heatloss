"""Lightweight test runner (no pytest dependency): python tests/run.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_engine as T  # noqa: E402

fns = [n for n in dir(T) if n.startswith("test_")]
failed = 0
for n in fns:
    try:
        getattr(T, n)()
        print("  ✓", n)
    except Exception as e:
        failed += 1
        print("  ✗", n, "—", e)
print(f"{len(fns) - failed}/{len(fns)} passed")
sys.exit(1 if failed else 0)
