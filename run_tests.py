#!/usr/bin/env python3
"""Stdlib-only test runner. Finds every test_* function in tests/ and runs it.

Usage:
    python3 run_tests.py            # run everything
    python3 run_tests.py parser     # run only test_parser.py
"""

import importlib
import inspect
import pkgutil
import sys
import traceback
from pathlib import Path


def discover_test_modules(filter_substr: str | None):
    tests_pkg = importlib.import_module("tests")
    for info in pkgutil.iter_modules(tests_pkg.__path__):
        if not info.name.startswith("test_"):
            continue
        if filter_substr and filter_substr not in info.name:
            continue
        yield importlib.import_module(f"tests.{info.name}")


def run_module(mod) -> tuple[int, int]:
    passed = failed = 0
    fns = [
        (name, obj) for name, obj in inspect.getmembers(mod, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == mod.__name__
    ]
    print(f"\n── {mod.__name__} ({len(fns)} tests) ──")
    for name, fn in fns:
        try:
            fn()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}")
            tb = traceback.format_exc()
            # Indent the traceback for readability
            for line in tb.splitlines():
                print(f"        {line}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {name}: {e!r}")
            tb = traceback.format_exc()
            for line in tb.splitlines():
                print(f"        {line}")
        else:
            passed += 1
            print(f"  ok    {name}")
    return passed, failed


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    filt = sys.argv[1] if len(sys.argv) > 1 else None
    total_pass = total_fail = 0
    for mod in discover_test_modules(filt):
        p, f = run_module(mod)
        total_pass += p
        total_fail += f
    print(f"\n{'═' * 40}")
    print(f"  {total_pass} passed, {total_fail} failed")
    print(f"{'═' * 40}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
