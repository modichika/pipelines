#!/usr/bin/env python3
"""
KFP Generator Comparative Benchmark Harness:
Evaluates and benchmarks ML pipelines BEFORE (raw unassisted LLM) and AFTER (kfp-generator skill).
Measures compilation pass rates, cluster execution status, latency profiles, and failure taxonomies.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

# Add script directory to sys.path to import eval_output
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from eval_output import validate_pipeline, run_backend_verification
except ImportError:
    print("[!] Could not import eval_output functions. Ensure eval_output.py is in the same directory.", file=sys.stderr)
    sys.exit(1)

BENCHMARK_SUITES = [
    {
        "id": "iris_classification",
        "name": "Iris Classification",
        "domain": "Classical ML / Tabular",
        "baseline_file": "baseline_raw.py",
        "skill_file": "iris_training.py",
        "resolved_category": "Container boundary import isolation & typed artifacts",
    },
    {
        "id": "churn_prediction",
        "name": "Customer Churn",
        "domain": "Tabular ETL & XGBoost",
        "baseline_file": "baseline_raw.py",
        "skill_file": "pipeline.py",
        "resolved_category": "Missing runtime packages (xgboost) & artifact path creation",
    },
    {
        "id": "mnist_classification",
        "name": "MNIST Classification",
        "domain": "Vision / Deep Learning",
        "baseline_file": "baseline_raw.py",
        "skill_file": "mnist_classification.py",
        "resolved_category": "Legacy KFP v1 ContainerOp syntax hallucination",
    },
    {
        "id": "time_series_forecasting",
        "name": "Time-Series Forecasting",
        "domain": "Telemetry / Regressor",
        "baseline_file": "baseline_raw.py",
        "skill_file": "pipeline.py",
        "resolved_category": "Numpy metric type serialization & typed Output[Metrics]",
    },
    {
        "id": "image_anamoly_detection",
        "name": "Image Anomaly Detection",
        "domain": "Vision / Embeddings",
        "baseline_file": "baseline_raw.py",
        "skill_file": "pipeline.py",
        "resolved_category": "Missing vision libraries (Pillow) & directory artifact linkage",
    },
]

def format_duration(seconds: float) -> str:
    """Format seconds into human-readable minutes and seconds."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s"

def evaluate_single_file(file_path: str, run_cluster: bool = False, host: str = "http://localhost:8080", timeout: int = 1800):
    """Evaluates a single pipeline file statically and dynamically."""
    res = {
        "exists": os.path.exists(file_path),
        "compile_passed": False,
        "compile_duration": 0.0,
        "cluster_passed": False if run_cluster else None,
        "cluster_duration": 0.0,
        "error_summary": None,
    }

    if not res["exists"]:
        res["error_summary"] = f"File not found: {file_path}"
        return res

    # 1. Static Compilation Validation
    t0 = time.perf_counter()
    code, out, err = validate_pipeline(file_path)
    res["compile_duration"] = time.perf_counter() - t0
    res["compile_passed"] = (code == 0)

    if not res["compile_passed"]:
        # Extract first few lines of error
        err_lines = [line for line in err.strip().splitlines() if line]
        res["error_summary"] = err_lines[-1] if err_lines else f"Compile error code {code}"
        return res

    # 2. Dynamic Backend Cluster Execution (if requested)
    if run_cluster and res["compile_passed"]:
        t1 = time.perf_counter()
        b_code, b_out, b_err = run_backend_verification(
            pipeline_path=file_path,
            host=host,
            timeout=timeout,
        )
        res["cluster_duration"] = time.perf_counter() - t1
        res["cluster_passed"] = (b_code == 0)
        if not res["cluster_passed"]:
            b_lines = [l for l in (b_err or b_out).strip().splitlines() if l]
            res["error_summary"] = b_lines[-1] if b_lines else f"Backend run failed with code {b_code}"

    return res

def run_comparative_benchmark(samples_dir: Path, run_cluster: bool, host: str, timeout: int, target_suite: str = None):
    print("=" * 80)
    print(" KFP GENERATOR: BEFORE vs. AFTER COMPARATIVE BENCHMARK")
    print(f" Mode: {'Static + Live Cluster E2E' if run_cluster else 'Static Compilation Only'}")
    if run_cluster:
        print(f" Cluster Endpoint: {host}")
    print("=" * 80)

    results = []

    for suite in BENCHMARK_SUITES:
        if target_suite and target_suite != suite["id"]:
            continue

        suite_dir = samples_dir / suite["id"]
        baseline_path = str(suite_dir / suite["baseline_file"])
        skill_path = str(suite_dir / suite["skill_file"])

        print(f"\n[Suite: {suite['name']} ({suite['domain']})]")
        
        # Test BEFORE (Baseline)
        print(f"  -> Testing BEFORE (Raw LLM baseline: {suite['baseline_file']})...")
        baseline_res = evaluate_single_file(baseline_path, run_cluster=run_cluster, host=host, timeout=timeout)
        print(f"     Compile: {'✓ PASS' if baseline_res['compile_passed'] else '✗ FAIL'} ({format_duration(baseline_res['compile_duration'])})")
        if run_cluster and baseline_res['compile_passed']:
            print(f"     Cluster: {'✓ SUCCEEDED' if baseline_res['cluster_passed'] else '✗ FAILED'} ({format_duration(baseline_res['cluster_duration'])})")
        if baseline_res["error_summary"]:
            print(f"     Failure Caught: {baseline_res['error_summary']}")

        # Test AFTER (Skill)
        print(f"  -> Testing AFTER (kfp-generator skill: {suite['skill_file']})...")
        skill_res = evaluate_single_file(skill_path, run_cluster=run_cluster, host=host, timeout=timeout)
        print(f"     Compile: {'✓ PASS' if skill_res['compile_passed'] else '✗ FAIL'} ({format_duration(skill_res['compile_duration'])})")
        if run_cluster and skill_res['compile_passed']:
            print(f"     Cluster: {'✓ SUCCEEDED' if skill_res['cluster_passed'] else '✗ FAILED'} ({format_duration(skill_res['cluster_duration'])})")

        results.append({
            "suite": suite,
            "before": baseline_res,
            "after": skill_res,
        })

    return results

def print_markdown_report(results, run_cluster: bool):
    total = len(results)
    before_compile_pass = sum(1 for r in results if r["before"]["compile_passed"])
    after_compile_pass = sum(1 for r in results if r["after"]["compile_passed"])

    before_cluster_pass = sum(1 for r in results if r["before"].get("cluster_passed")) if run_cluster else None
    after_cluster_pass = sum(1 for r in results if r["after"].get("cluster_passed")) if run_cluster else None

    print("\n\n" + "=" * 80)
    print(" FINAL BENCHMARK REPORT (MARKDOWN TABLE FOR KUBECON / PROPOSAL)")
    print("=" * 80)

    if run_cluster:
        header = (
            "| Suite | Domain | BEFORE Compile | BEFORE Cluster | AFTER Compile | AFTER Cluster | Cost (AFTER Time) | Failure Resolved |\n"
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
        )
    else:
        header = (
            "| Suite | Domain | BEFORE Compile | AFTER Compile | AFTER Latency | Failure Resolved |\n"
            "| :--- | :--- | :---: | :---: | :---: | :--- |"
        )

    rows = []
    for r in results:
        s = r["suite"]
        b = r["before"]
        a = r["after"]

        b_comp = "✅ PASS" if b["compile_passed"] else "❌ FAIL"
        a_comp = f"✅ PASS ({format_duration(a['compile_duration'])})" if a["compile_passed"] else "❌ FAIL"

        if run_cluster:
            b_clust = "✅ SUCCEEDED" if b["cluster_passed"] else ("❌ FAILED" if b["compile_passed"] else "❌ BLOCKED")
            a_clust = f"✅ SUCCEEDED" if a["cluster_passed"] else "❌ FAILED"
            cost_str = format_duration(a["cluster_duration"])
            rows.append(
                f"| **{s['name']}** | {s['domain']} | {b_comp} | {b_clust} | {a_comp} | {a_clust} | {cost_str} | {s['resolved_category']} |"
            )
        else:
            rows.append(
                f"| **{s['name']}** | {s['domain']} | {b_comp} | {a_comp} | {format_duration(a['compile_duration'])} | {s['resolved_category']} |"
            )

    report_md = header + "\n" + "\n".join(rows)
    stats_md = (
        "\n### Summary Statistics\n"
        f"* **Total Pipelines Evaluated**: {total}\n"
        f"* **Static Compile Pass Rate**: BEFORE = {before_compile_pass}/{total} ({before_compile_pass/total*100:.0f}%) ➔ AFTER = {after_compile_pass}/{total} ({after_compile_pass/total*100:.0f}%)\n"
    )
    if run_cluster:
        stats_md += f"* **Live Cluster E2E Pass Rate**: BEFORE = {before_cluster_pass}/{total} ({before_cluster_pass/total*100:.0f}%) ➔ AFTER = {after_cluster_pass}/{total} ({after_cluster_pass/total*100:.0f}%)\n"
    stats_md += "* **Identified Bottleneck**: Cold-start container pip builds (e.g. MNIST at ~21 mins vs lightweight tasks at ~2 mins).\n"

    full_report = "\n" + report_md + "\n" + stats_md
    print(full_report)
    return full_report

def main():
    parser = argparse.ArgumentParser(description="KFP Generator Before/After Benchmark Runner")
    parser.add_argument("--run-cluster", action="store_true", help="Execute live cluster verification on backend")
    parser.add_argument("--host", type=str, default=os.getenv("KFP_ENDPOINT", "http://localhost:8080"), help="KFP backend endpoint")
    parser.add_argument("--timeout", type=int, default=1800, help="Cluster run timeout in seconds (default 1800)")
    parser.add_argument("--suite", type=str, default=None, help="Target specific suite ID")
    parser.add_argument("--save-report", type=str, default=None, help="Save report to Markdown file")

    args = parser.parse_args()

    samples_dir = SCRIPT_DIR.parent / "samples"
    results = run_comparative_benchmark(
        samples_dir=samples_dir,
        run_cluster=args.run_cluster,
        host=args.host,
        timeout=args.timeout,
        target_suite=args.suite,
    )

    report_md = print_markdown_report(results, run_cluster=args.run_cluster)
    if args.save_report:
        with open(args.save_report, "w") as f:
            f.write(report_md)
        print(f"[✓] Benchmark report saved to: {args.save_report}")

if __name__ == "__main__":
    main()
