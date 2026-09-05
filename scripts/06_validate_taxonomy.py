"""Evaluate human labels; an unreviewed sample can never pass the validation gate."""

import argparse
import json
from pathlib import Path

from mlops_traceability.config import load_config
from mlops_traceability.validation.taxonomy_review import evaluate_review

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sample", type=Path)
    args = parser.parse_args()
    result = evaluate_review(args.sample, load_config("config/config.yaml"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["accepted"] else 1)
