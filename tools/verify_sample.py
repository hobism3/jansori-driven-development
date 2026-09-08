#!/usr/bin/env python3
"""Check supplied sample inputs or a separate B/C candidate. No Jansori implementation.

Python 3.10+; standard library only; a C++17 compiler is required except in integrity mode.
The evaluator-held API header, runner, probe and golden data are always used.
Reports are not evidence of Plugin operation, AI-DLC approval or correction propagation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "fixtures/workloads"
ACCEPT = ROOT / "fixtures/acceptance"
SUFFIXES = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inc", ".tpp"}
FIXED = ["tools/verify_sample.py", "fixtures/workloads/common/cmodel.hpp",
         "fixtures/workloads/common/runner.cpp", "fixtures/workloads/C/session_probe.cpp",
         "fixtures/acceptance/workload-golden.json", "fixtures/acceptance/lifecycle-golden.json"]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Cannot complete command {args!r}: {exc}") from exc
    return {"command": args, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def require_success(record: dict[str, Any]) -> None:
    if record["returncode"]:
        raise RuntimeError(json.dumps(record, ensure_ascii=False))


def compare(expected: list[Any], actual: list[Any]) -> list[dict[str, Any]]:
    result = []
    for i in range(max(len(expected), len(actual))):
        e = expected[i] if i < len(expected) else None
        a = actual[i] if i < len(actual) else None
        if e != a:
            result.append({"index": i, "expected": e, "actual": a})
    return result


def arithmetic(case: dict[str, Any], which: str) -> list[int]:
    """Direct independent calculation of the PUBLIC numeric contract, not optimized C++."""
    w, h, r = case["width"], case["height"], case["radius"]
    pixels, s, g = case["input_rgb"], case["strength_q8"], case["gain_q8"]
    answer = []
    for y in range(h):
        for x in range(w):
            for channel in range(3):
                total = 0
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        yy = max(0, min(h - 1, y + dy))
                        xx = max(0, min(w - 1, x + dx))
                        total += pixels[(yy * w + xx) * 3 + channel]
                mean = total // ((2 * r + 1) ** 2)
                value = pixels[(y * w + x) * 3 + channel]
                if which == "B":
                    value = (value * (256 - s) + mean * s + 128) // 256
                else:
                    numerator = (value - mean) * g
                    delta = (abs(numerator) // 256) * (-1 if numerator < 0 else 1)
                    value = max(0, min(255, value + delta))
                answer.append(value)
    return answer


def integrity() -> dict[str, Any]:
    manifest = read_json(ROOT / "INPUT-MANIFEST.json")
    bad = [name for name, value in manifest["files"].items()
           if not (ROOT / name).is_file() or digest(ROOT / name) != value]
    if bad:
        raise RuntimeError("Manifest mismatch: " + ", ".join(bad))
    if manifest["file_count_without_manifest"] != len(manifest["files"]):
        raise RuntimeError("Manifest count mismatch")
    fixture_json = list((ROOT / "fixtures").rglob("*.json"))
    for file in fixture_json:
        read_json(file)
    cases = read_json(ACCEPT / "development-cases.json")["cases"]
    ids = [c["case_id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise RuntimeError("Duplicate development case ID")
    r_ids = {r for c in cases for r in c["r_ids"]}
    i_ids = {i for c in cases for i in c["invariants"]}
    if r_ids != {f"R-{i:02d}" for i in range(1, 15)}:
        raise RuntimeError("Incomplete or unknown R-ID references")
    if i_ids != {f"I-{i:02d}" for i in range(1, 16)}:
        raise RuntimeError("Incomplete or unknown I-ID references")
    seeds = [read_json(p) for p in (ROOT / "fixtures/seed").glob("*.json")]
    by_id = {s["skill_id"]: s for s in seeds}
    if len(by_id) != len(seeds):
        raise RuntimeError("Duplicate seed ID")
    for seed in seeds:
        if seed["version"] != 1 or seed["corrections"]:
            raise RuntimeError("Seed must start with v1 and empty corrections")
        if any(k in seed for k in ("compaction_pending", "compaction_status", "runtime_status")):
            raise RuntimeError("Runtime state mixed into seed content")
        for child in seed["refs"]:
            if child not in by_id or child == seed["skill_id"] or by_id[child]["refs"]:
                raise RuntimeError("Seed refs violate the one-level fixture contract")
    golden = read_json(ACCEPT / "workload-golden.json")
    numeric_ids = [c["case_id"] for c in golden["valid_cases"]]
    if len(numeric_ids) != len(set(numeric_ids)):
        raise RuntimeError("Duplicate numeric case ID")
    for c in golden["valid_cases"]:
        for which in ("B", "C"):
            if arithmetic(c, which) != c["expected_" + which]:
                raise RuntimeError(f"Numeric golden contradicts public arithmetic: {c['case_id']}/{which}")
    return {"status": "PASS_INPUT_INTEGRITY_ONLY", "manifest_files_checked": len(manifest["files"]),
            "fixture_json_files_parsed": len(fixture_json), "development_case_count": len(cases),
            "all_R01_R14_referenced": True, "all_I01_I15_referenced": True,
            "valid_numeric_cases": len(golden["valid_cases"]),
            "invalid_numeric_cases": len(golden["invalid_cases"]),
            "lifecycle_events": len(read_json(ACCEPT / "lifecycle-golden.json")["steps"]),
            "seed_depth_check": "PASS_FIXTURE_STRUCTURE_ONLY_NOT_SERVER_ENFORCEMENT",
            "meaning": "Reference coverage and fixture consistency are NOT product requirement verification."}


def stage_sources(base: Path, which: str, workspace: Path | None) -> tuple[list[Path], dict[str, str], dict[str, Any]]:
    src, common = base / "src", base / "common"
    src.mkdir(parents=True)
    common.mkdir()
    shutil.copyfile(WORK / "common/cmodel.hpp", common / "cmodel.hpp")
    shutil.copyfile(WORK / "common/runner.cpp", common / "runner.cpp")
    origin = workspace / "src" if workspace else WORK / which
    if not origin.is_dir():
        raise RuntimeError(f"Candidate must contain a src directory: {origin}")
    files = sorted(p for p in origin.rglob("*") if p.is_file() and p.suffix in SUFFIXES)
    ignored = []
    fingerprints = {}
    for p in files:
        if p.is_symlink():
            raise RuntimeError(f"Symlink source is not supported: {p}")
        relative = p.relative_to(origin)
        fingerprints["src/" + relative.as_posix()] = digest(p)
        if p.name in ("session_probe.cpp", "runner.cpp"):
            ignored.append("src/" + relative.as_posix())
            continue
        if p.name == "cmodel.hpp":
            raise RuntimeError("Do not shadow the evaluator-held common/cmodel.hpp inside candidate src")
        target = src / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    sources = sorted(p for p in src.rglob("*") if p.suffix in (".cpp", ".cc", ".cxx"))
    if not sources or (which == "C" and not (src / "local_contrast_model.hpp").is_file()):
        raise RuntimeError("Missing workload translation units or C public model header")
    shutil.copyfile(WORK / "C/session_probe.cpp", base / "fixed-session-probe.cpp")
    return sources, fingerprints, {"ignored_workspace_observers": ignored,
                                 "common_header_and_runner": "evaluator-held copies always used",
                                 "sandbox": False}


EMITTER = r'''
#include "cmodel.hpp"
#ifdef CHECK_MODEL
#include "local_contrast_model.hpp"
#endif
#include <iostream>
void Emit(const char* Id, const char* Entry, const cmodel::Image* Image, const char* Error) {
 std::cout << "{\"case_id\":\"" << Id << "\",\"entrypoint\":\"" << Entry << '"';
 if (Image) {
  std::cout << ",\"image\":{\"width\":" << Image->Width << ",\"height\":" << Image->Height << ",\"pixels\":[";
  for (std::size_t i=0; i<Image->Pixels.size(); ++i) { if(i) std::cout<<','; std::cout<<int(Image->Pixels[i]); }
  std::cout << "]}";
 } else { std::cout << ",\"exception\":\"" << Error << '"'; }
 std::cout << "}\n";
}
int main() {
'''


def numeric_harness(which: str) -> tuple[str, list[dict[str, Any]]]:
    golden = read_json(ACCEPT / "workload-golden.json")
    code, expected = [EMITTER], []
    entries = ["DoProcess"] + (["DoRun"] if which == "C" else [])
    for valid in (True, False):
        cases = golden["valid_cases"] if valid else golden["invalid_cases"]
        for index, case in enumerate(cases, 1):
            identifier = case["case_id"] if valid else f"INVALID-{index:02d}"
            if valid:
                w, h, pixels = case["width"], case["height"], case["input_rgb"]
                params = [case["radius"], case["strength_q8"], case["gain_q8"]]
            else:
                w, h, pixels, params = 2, 1, [10, 40, 80, 90, 180, 250], [4, 160, 256]
                if "field" in case:
                    params[{"radius": 0, "strength_q8": 1, "gain_q8": 2}[case["field"]]] = case["value"]
                else:
                    pixels = [10]
            for entry in entries:
                code.append(f'{{ cmodel::Image input{{{w},{h},{{{",".join(map(str,pixels))}}}}};')
                code.append('cmodel::Parameters p{' + ','.join(map(str, params)) + '}; try {')
                call = 'cmodel::DoProcess(input,p)' if entry == "DoProcess" else 'cmodel::LocalContrastModel(p).DoRun(input)'
                code.append(f'auto result={call}; Emit("{identifier}","{entry}",&result,nullptr);')
                code.append(f'}} catch(const std::invalid_argument&) {{ Emit("{identifier}","{entry}",nullptr,"invalid_argument"); }}')
                code.append(f'catch(const std::exception&) {{ Emit("{identifier}","{entry}",nullptr,"other_exception"); }} }}')
                row: dict[str, Any] = {"case_id": identifier, "entrypoint": entry}
                if valid:
                    row["image"] = {"width": w, "height": h, "pixels": case["expected_" + which]}
                else:
                    row["exception"] = "invalid_argument"
                expected.append(row)
    code.append('return 0; }')
    return '\n'.join(code), expected


def parse_lines(run: dict[str, Any]) -> list[Any]:
    require_success(run)
    try:
        return [json.loads(line) for line in run["stdout"].splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise RuntimeError("Observation output is not JSON-lines: " + run["stdout"][:2000]) from exc


def check_workload(base: Path, compiler: str, which: str, mode: str,
                   workspace: Path | None) -> dict[str, Any]:
    sources, hashes, policy = stage_sources(base, which, workspace)
    builds = []

    def build(main: Path, name: str, extra: list[str] | None = None) -> Path:
        exe = base / name
        args = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                "-I" + str(base / "common"), "-I" + str(base / "src")]
        args += (extra or []) + [str(main)] + [str(s) for s in sources] + ["-o", str(exe)]
        result = execute(args)
        builds.append(result)
        require_success(result)
        return exe

    harness, expected = numeric_harness(which)
    numeric_source = base / "fixed-numeric.cpp"
    numeric_source.write_text(harness, encoding="utf-8")
    numeric_exe = build(numeric_source, "numeric", ["-DCHECK_MODEL"] if which == "C" else [])
    actual = parse_lines(execute([str(numeric_exe)]))
    differences = compare(expected, actual)
    report: dict[str, Any] = {"workload": which, "compiler": compiler, "candidate_source_sha256": hashes,
        "evaluator_policy": policy, "numeric": {"status": "FAIL" if differences else "PASS",
        "entrypoints": ["DoProcess"] + (["DoRun"] if which == "C" else []),
        "valid_cases_per_entrypoint": 42, "invalid_cases_per_entrypoint": 5,
        "observations_compared": len(expected), "differences": differences}}

    runner = build(base / "common/runner.cpp", "workload")
    full = base / "output.ppm"
    full_run = execute([str(runner), str(WORK / which / "input.ppm"), str(full)])
    require_success(full_run)
    full_info: dict[str, Any] = {"status": "PASS", "command": full_run["command"],
                                "stdout": full_run["stdout"].strip(), "sha256": digest(full),
                                "parameters": {"Radius": 4, "StrengthQ8": 160, "GainQ8": 256}}
    if mode == "candidate":
        original = WORK / which / ("noise_reduction.cpp" if which == "B" else "local_contrast.cpp")
        baseline_exe, baseline_output = base / "original-workload", base / "original.ppm"
        baseline_build = execute([compiler, "-std=c++17", "-O2", "-I" + str(WORK / "common"),
            "-I" + str(WORK / "C"), str(WORK / "common/runner.cpp"), str(original), "-o", str(baseline_exe)])
        builds.append(baseline_build)
        require_success(baseline_build)
        require_success(execute([str(baseline_exe), str(WORK / which / "input.ppm"), str(baseline_output)]))
        full_info["baseline_sha256"] = digest(baseline_output)
        if full.read_bytes() != baseline_output.read_bytes():
            full_info["status"] = "FAIL"
    report["full_frame"] = full_info
    if which == "C":
        probe = build(base / "fixed-session-probe.cpp", "session-probe")
        observed = parse_lines(execute([str(probe)]))
        target = read_json(ACCEPT / "lifecycle-golden.json")["steps"]
        target_diff = compare(target, observed)
        lifecycle: dict[str, Any] = {"target_event_count": len(target), "actual": observed,
                                    "target_differences": target_diff}
        if mode == "starter":
            expected_starter = copy.deepcopy(target)
            for event in expected_starter:
                event["ready"], event["frame_count"] = False, 0
            starter_diff = compare(expected_starter, observed)
            lifecycle.update({"status": "EXPECTED_INCOMPLETE" if not starter_diff and target_diff else "FAIL",
                "starter_contract_differences": starter_diff,
                "meaning": "Missing lifecycle implementation is the live C task, not a completed candidate."})
        else:
            lifecycle["status"] = "FAIL" if target_diff else "PASS"
        report["lifecycle"] = lifecycle
    report["builds"] = builds
    checks = [report["numeric"]["status"], full_info["status"]]
    if "lifecycle" in report:
        checks.append(report["lifecycle"]["status"])
    report["status"] = "FAIL" if "FAIL" in checks else ("PASS_INPUT_CHECKS_ONLY" if mode == "starter" else "PASS_FUNCTIONAL_CHECKS_ONLY")
    return report


def clean_workspace_check(base: Path) -> dict[str, Any]:
    mapping = {"TASK.md": WORK / "C/TASK.md", "input.ppm": WORK / "C/input.ppm"}
    for name in ("WORKLOAD-SPEC.md", "cmodel.hpp", "runner.cpp"):
        mapping["common/" + name] = WORK / "common" / name
    for name in ("local_contrast.cpp", "local_contrast_model.hpp", "session_probe.cpp"):
        mapping["src/" + name] = WORK / "C" / name
    snapshots, leaks = [], []
    for run in ("c0", "c1", "c2"):
        for name, source in mapping.items():
            dest = base / run / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        snapshots.append({name: digest(base / run / name) for name in mapping})
    for name in mapping:
        if name.endswith(".ppm"):
            continue
        text = (base / "c0" / name).read_text(encoding="utf-8")
        for word in ("is_ready", "m_ready", "m_frame_count", "B-NAG-", "workload-golden.json"):
            if word in text:
                leaks.append({"file": name, "term": word})
    identical = snapshots[0] == snapshots[1] == snapshots[2]
    return {"status": "PASS" if identical and not leaks else "FAIL",
            "identical_initial_C0_C1_C2_hashes": identical, "relative_files": snapshots[0],
            "known_exact_answer_leaks": leaks,
            "shared_prompt_sha256": digest(ROOT / "prompts/demo/C-START.txt"),
            "limitation": "Allow-list copy and exact-string scan only, not OS isolation or proof of session isolation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("integrity", "starter", "candidate"), default="starter")
    parser.add_argument("--candidate", type=Path, help="Separate workload workspace containing src/")
    parser.add_argument("--workload", choices=("B", "C"), default="C", help="Candidate workload only")
    parser.add_argument("--compiler", action="append", help="Compiler executable; repeat to check several; default c++")
    parser.add_argument("--report", type=Path, help="Write full JSON; keep reports outside C workspaces")
    args = parser.parse_args()
    if args.mode == "candidate" and args.candidate is None:
        parser.error("--candidate is required in candidate mode")
    if args.mode != "candidate" and args.candidate is not None:
        parser.error("--candidate is only valid in candidate mode")
    report: dict[str, Any] = {
        "scope": "Supplied sample/evaluator checks only; no AI-DLC or Jansori execution",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
        "status": "ERROR", "fixed_evaluator_sha256": {name: digest(ROOT / name) for name in FIXED},
        "not_verified": ["Jansori server/Hook/Skill", "I/R product guarantees including I-15 enforcement",
            "A/B/C real sessions and actual Capsule Read", "correction propagation and actual compaction",
            "private member naming and semantic code review", "speed improvement", "human approvals and comprehension"],
        "optimized_solution": "NOT PROVIDED", "workloads": []}
    code = 2
    try:
        report["integrity"] = integrity()
        if args.mode == "integrity":
            report["status"], code = "PASS_INPUT_INTEGRITY_ONLY", 0
        else:
            compilers = args.compiler or ["c++"]
            report["compilers"] = {}
            workspace = args.candidate.resolve() if args.candidate else None
            if workspace and (workspace == ROOT or ROOT in workspace.parents):
                raise RuntimeError("Candidate must be outside the development/evaluator package")
            if workspace and args.report and (args.report.resolve() == workspace or workspace in args.report.resolve().parents):
                raise RuntimeError("Keep evaluator reports outside the candidate workspace")
            with tempfile.TemporaryDirectory(prefix="jansori-sample-check-") as tmp:
                temp = Path(tmp)
                report["clean_workspace_checks"] = clean_workspace_check(temp / "clean")
                for index, compiler in enumerate(compilers):
                    if shutil.which(compiler) is None:
                        raise RuntimeError(f"Compiler not found: {compiler}")
                    version = execute([compiler, "--version"])
                    require_success(version)
                    report["compilers"][compiler] = version["stdout"].splitlines()[0]
                    for which in (("B", "C") if args.mode == "starter" else (args.workload,)):
                        item = check_workload(temp / f"build-{index}-{which}", compiler, which, args.mode, workspace)
                        report["workloads"].append(item)
                    if args.mode == "starter":
                        exe = temp / f"policy-{index}"
                        require_success(execute([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                            str(WORK / "policy/legacy_policy.cpp"), "-o", str(exe)]))
                        policy = execute([str(exe)])
                        require_success(policy)
                        if policy["stdout"].strip() != "top_accepted=false nr_before=100 nr_after=100 rgbp=264":
                            raise RuntimeError("Policy starter differs from its documented output")
                        report.setdefault("policy_checks", []).append({"compiler": compiler, "status": "PASS",
                            "observed": policy["stdout"].strip()})
                agreement = {}
                for which in ("B", "C"):
                    values = [w["full_frame"]["sha256"] for w in report["workloads"] if w["workload"] == which]
                    if len(values) > 1:
                        agreement[which] = len(set(values)) == 1
                report["cross_compiler_full_frame_agreement"] = agreement
                fail = any(w["status"] == "FAIL" for w in report["workloads"])
                fail = fail or any(not value for value in agreement.values()) or report["clean_workspace_checks"]["status"] == "FAIL"
                code = 1 if fail else 0
                report["status"] = "FAIL" if fail else ("PASS_INPUT_CHECKS_ONLY" if args.mode == "starter" else "PASS_FUNCTIONAL_CHECKS_ONLY")
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        report["error"] = str(exc)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
        print(f"{report['status']} — {args.report}")
    else:
        print(payload, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
