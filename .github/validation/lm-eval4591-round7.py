import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from lm_eval.tasks._yaml_loader import load_yaml

root = Path.cwd()
evidence = Path(os.environ["RUNNER_TEMP"]) / "lm-eval4591-round7"
evidence.mkdir(parents=True, exist_ok=True)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert head == "c09418d65e9748f91dfa9a80535fe19df5009335", head
assert subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip() == "1231b82735bfdee595b1b8f4371c718afa4f6fda"
paths = {
    "lm_eval/tasks/ifeval/ifeval.yaml": 5.0,
    "lm_eval/tasks/leaderboard/ifeval/ifeval.yaml": 4.0,
    "lm_eval/tasks/ifeval/multilingual/ifeval_es.yaml": 2.0,
    "lm_eval/tasks/ifeval/multilingual/ifeval_ca.yaml": 2.0,
}
changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD^", "HEAD"], text=True).splitlines()
assert set(changed) == set(paths) | {"lm_eval/tasks/ifeval/README.md"}, changed
versions = {}
for path, expected in paths.items():
    actual = load_yaml(root / path, resolve_func=False)["metadata"]["version"]
    assert actual == expected, (path, actual, expected)
    versions[path] = actual
assert (root / "lm_eval/tasks/ifeval/../../../docs/new_task_guide.md").resolve().is_file()
subprocess.run(["git", "diff", "--check", "HEAD^", "HEAD"], check=True)
(evidence / "source-and-versions.json").write_text(json.dumps({
    "sha": head, "tree": "1231b82735bfdee595b1b8f4371c718afa4f6fda",
    "changed_files": changed, "versions": versions,
}, indent=2))
command = [
    "python", "-m", "pytest", "-q",
    "tests/test_ifeval_zero_arguments.py", "tests/test_metrics.py",
    "--junitxml=" + str(evidence / "pytest.xml"),
]
result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(result.stdout, flush=True)
(evidence / "pytest.log").write_text(result.stdout)
assert result.returncode == 0, result.returncode
xml = ET.parse(evidence / "pytest.xml")
cases = xml.findall(".//testcase")
assert len(cases) == 60, len(cases)
assert not xml.findall(".//failure"), "test failures"
assert not xml.findall(".//error"), "test errors"
assert not xml.findall(".//skipped"), "language-model-dependent tests were skipped"
subprocess.run(["pre-commit", "run", "--files", *changed], check=True, timeout=600)
assert not subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip()
print(json.dumps({"sha": head, "passed": 60, "skipped": 0, "source_unchanged": True}, indent=2), flush=True)
