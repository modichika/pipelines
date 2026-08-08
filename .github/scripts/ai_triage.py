import os
import re
import sys
import time
import subprocess
import requests

# Configuration from Environment Variables
TARGET_MODEL = os.getenv("TARGET_MODEL", "openai/gpt-4o-mini")
ISSUE_TITLE = os.getenv("TITLE", "")
RAW_BODY = os.getenv("RAW_BODY", "")
GH_TOKEN = os.getenv("GH_TOKEN")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER")

def post_github_comment(body):
    """Posts a comment back to the GitHub issue."""
    if not ISSUE_NUMBER or not GH_TOKEN:
        return
    cmd = ["gh", "issue", "comment", str(ISSUE_NUMBER), "--body", body]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to post comment: {e.stderr}")

def run_model_with_retry(system_prompt, user_prompt, max_retries=3):
    """Executes local Ollama inference with exponential backoff retry logic."""
    url = "http://localhost:11434/api/generate"
    delay = 2
    
    payload = {
        "model": TARGET_MODEL,
        "prompt": f"{system_prompt}\n\nUser Input:\n{user_prompt}",
        "stream": False
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            print(f"⚠️ Attempt {attempt} failed with status {response.status_code}. Retrying in {delay}s...")
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed. Retrying in {delay}s... Error: {e}")
            
        time.sleep(delay)
        delay *= 2  # Exponential backoff
        
    return None

def parse_title(title):
    """Extracts type, area, and content from a validated title."""
    pattern = r"^([a-z]+)\(([a-z]+)\):\s*(.+)$"
    match = re.match(pattern, title.strip())
    if not match:
        return "chore", "general", title  # Safe fallback since YAML already verified it
    return match.group(1).lower(), match.group(2).lower(), match.group(3)

def main():
    print(f"Using model: {TARGET_MODEL}")
    
    # Step 1: Parse Title Format
    issue_type, issue_area, issue_content = parse_title(ISSUE_TITLE)
    print(f"✅ Processing valid issue. Type: {issue_type}, Area: {issue_area}")

    # Step 2: Build System Instructions based on Issue Type Standards
    system_instructions = f"""
You are an expert open-source maintainer for Kubeflow Pipelines.
Analyze the quality of the incoming issue {issue_type} based on Scope, Context, Guidance, and Complexity.

Calibrate your evaluation against these compressed reference standards:
- BACKEND (#13314): [backend] S3 operations fail with non-AWS object stores after AWS SDK v2 checksum defaults change. Clear isolated scope.
- BUG TIER (#13180): [bug] fix: E2E test flakiness on K8s v1.34.0 — root cause analysis. High-quality root-cause analysis and environment data.
- FRONTEND (#13108): [frontend] Adds coverage for frontend mock:api startup and enum drift. Explicit file paths and definitions of done.
- SDK (#12865): [sdk] [bug] [set_accelerator_limit] rejects valid accelerator counts. Elite precision with failing parameters.

Respond strictly following this format structure without other markdown wraps:
- Each section MUST contain exactly 2 to 3 short, bullet fragments. 
- Do NOT write full-length paragraphs or introductory text. Keep it highly concise.
- Do NOT include any time frame or implementation window estimations.

### 📊 Scope
- <If the technical task boundaries are clear or ambiguous>
- <If the issue isolates specific components, files, or packages correctly>

### 📝 Context & Guidance
<Evaluate if steps, expected behavior, or links are provided against repo standards>

### ⚡ Complexity
- <State difficulty tier: Low, Medium, or High>
- <Break down breadth and depth of the proposed change>

### 🎯 Overall Issue Quality Verdict
- <State definitively if this is ready for immediate developer pickup>
- <Outline the single most impactful recommendation>
"""

    user_prompt = f"Title: {ISSUE_TITLE} | Body: {RAW_BODY}"

    # Step 3: Run AI Model with Retry Mechanism
    analysis_report = run_model_with_retries = run_model_with_retry(system_instructions, user_prompt)

    if not analysis_report:
        print("⚠️ CRITICAL: AI Model execution failed after multiple retries.")
        analysis_report = (
            "### ⚠️ Automated Triage Skipped\n"
            "The issue body text or environment logs exceeded processing size boundaries or API limits for this triage pass."
        )

    # Set GitHub Actions output
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a") as f:
            f.write("analysis<<EOF\n")
            f.write(analysis_report + "\n")
            f.write("EOF\n")

    print("DEBUG: The raw analysis sent to output was:")
    print(analysis_report)

if __name__ == "__main__":
    main()