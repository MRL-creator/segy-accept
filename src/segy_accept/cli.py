"""Command-line entry point with explicit outcomes and safe report destinations."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .audit import audit
from .policy import Policy
from .reader import file_signature, regular_file_stat
from .report import json_text, render_html


def load_policy(path):
    initial = regular_file_stat(path)
    if initial.st_size > 1024 * 1024:
        raise ValueError("policy exceeds the 1 MiB size limit")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON policy key: {key}")
            result[key] = value
        return result

    with Path(path).open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
        opened = os.fstat(stream.fileno())
    if len(raw) > 1024 * 1024:
        raise ValueError("policy exceeds the 1 MiB size limit")
    if file_signature(initial) != file_signature(opened) or file_signature(
        initial
    ) != file_signature(regular_file_stat(path)):
        raise ValueError("policy changed while being read; rerun on a stable file")
    try:
        definition = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    except RecursionError as error:
        raise ValueError("policy JSON nesting exceeds the decoder's supported depth") from error
    return Policy.from_dict(definition)


def save_reports(result, directory, protected, overwrite=False):
    directory = Path(directory)
    targets = [directory / "audit.json", directory / "audit.html"]
    for target in targets:
        for source in protected:
            if target.resolve() == source.resolve() or (
                target.exists() and source.exists() and target.samefile(source)
            ):
                raise ValueError("report target aliases an input or policy file")
        if target.exists() and not overwrite:
            raise FileExistsError(
                f"report exists: {target}; choose another directory or --overwrite"
            )
    contents = [json_text(result), render_html(result)]
    directory.mkdir(parents=True, exist_ok=True)
    for target, content in zip(targets, contents):
        if not overwrite:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        else:
            # Replacing the directory entry avoids truncating a hardlinked source.
            with tempfile.NamedTemporaryFile(
                mode="w", dir=directory, encoding="utf-8", newline="\n", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)


def print_summary(result, directory):
    print(f"{result['status']}: {result['scan']['traces_inspected']} trace headers inspected")
    if not result["scan"]["complete"]:
        print("Scan incomplete; acceptance is not established.")
    priority = {"failure": 0, "unknown": 1, "warning": 2, "pass": 3}
    for finding in sorted(result["findings"], key=lambda item: priority[item["status"]]):
        if finding["status"] == "pass":
            continue
        print(
            f"  {finding['status'].upper()} {finding['rule_id']}: {finding['count']} reported events"
        )
        if finding["examples"] and "reason" in finding["examples"][0]:
            print(f"    Reason: {finding['examples'][0]['reason']}")
        print(f"    {finding['next_step']}")
    if result["status"] == "accepted":
        print("No blocking findings under the declared policy and supported profile.")
    print(f"HTML report: {(directory / 'audit.html').resolve()}")
    print(f"JSON report: {(directory / 'audit.json').resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only SEG-Y acceptance against a declared workflow policy"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser(
        "audit", help="inspect a local SEG-Y file and produce JSON/HTML reports"
    )
    inspect.add_argument("input", type=Path)
    inspect.add_argument("--policy", type=Path, required=True)
    inspect.add_argument("--out", type=Path, required=True)
    inspect.add_argument("--overwrite", action="store_true")
    demo = subparsers.add_parser(
        "demo", help="create synthetic fixtures and their reports in a new directory"
    )
    demo.add_argument("directory", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return 0 if error.code == 0 else 3
    try:
        if args.command == "demo":
            from .demo import generate_demo

            manifest = generate_demo(args.directory)
            policy_path = args.directory / manifest["policy"]
            policy = load_policy(policy_path)
            for case in manifest["cases"]:
                path = args.directory / case["file"]
                result = audit(path, policy)
                save_reports(result, args.directory / case["report"], [path, policy_path])
                if result["status"] != case["expected_status"]:
                    raise ValueError(f"demo expectation mismatch: {case['file']}")
                print(f"{result['status']:10} {case['file']}")
            print(f"Open {(args.directory / 'readable-broken' / 'audit.html').resolve()}")
            return 0
        policy = load_policy(args.policy)
        result = audit(args.input, policy)
        save_reports(result, args.out, [args.input, args.policy], args.overwrite)
        print_summary(result, args.out)
        return {"accepted": 0, "rejected": 1, "incomplete": 2}[result["status"]]
    except (OSError, ValueError, UnicodeError) as error:
        print(f"segy-accept: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
