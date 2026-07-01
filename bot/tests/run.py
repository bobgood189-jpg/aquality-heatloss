"""Lightweight test runner (no pytest dependency): python tests/run.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_engine  # noqa: E402
import test_tools  # noqa: E402
import test_routing  # noqa: E402

total = failed = 0
for mod in (test_engine, test_tools, test_routing):
    print(f"[{mod.__name__}]")
    for n in [x for x in dir(mod) if x.startswith("test_")]:
        total += 1
        try:
            getattr(mod, n)()
            print("  ✓", n)
        except Exception as e:
            failed += 1
            print("  ✗", n, "—", e)
print(f"{total - failed}/{total} passed")
sys.exit(1 if failed else 0)
