"""Explicit offline study verification; never infer a latest source run."""

from mlops_traceability.verification.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
