import os
import subprocess

def truncate_text(text, max_chars=12000):
    if not text:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Content truncated due to size limits...]"
    return text

def main():
    model = os.getenv("TARGET_MODEL", "openai/gpt-4o-mini")
    title = os.getenv("TITLE", "")
    raw_body = os.getenv("RAW_BODY", "")

    # Ensure GitHub Models extension is available
    subprocess.run(["gh", "extension", "install", "github/gh-models"], capture_output=True)

    system_instructions = """You are an expert open-source maintainer for Kubeflow Pipelines.

Analyze the quality of the incoming issue based on Scope, Context, Guidance, and Complexity.
             
Calibrate your evaluation against these compressed reference standards:
- BACKEND (#13314): [backend] S3 operations fail with non-AWS object stores after AWS SDK v2 checksum defaults change. Clear isolated scope.
- BUG TIER (#13180): [bug] fix: E2E test flakiness on K8s v1.34.0 — root cause analysis. High-quality root-cause analysis and environment data.
- FRONTEND (#13108): [frontend] Adds coverage for frontend mock:api startup and enum drift. Explicit file paths and definitions of done.
- SDK (#12865): [sdk] [bug] [set_accelerator_limit] rejects valid accelerator counts (only allows 0, 1, 2, 4, 8, 16). Elite precision with failing parameters.

Compare the incoming issue detail density directly against the relevant blueprint standard above.

Respond strictly following this format structure without other markdown wraps:

- Each section MUST contain exactly 2 to 3 short, bullet fragments. 
- Do NOT write full-length paragraphs or introductory text. Keep it highly concise for quick scanning.
- Do NOT include any time frame or implementation window estimations.


### 📊 Scope
- <If the technical task boundaries are clear or ambiguous>
- <If the issue isolates specific components, files, or packages correctly>


### 📝 Context & Guidance
<Evaluate if steps, expected behavior, or links are provided against repo standards>

### ⚡ Complexity
- <State difficulty tier: Low, Medium, or High, calibrated against this exact rubric:
  * LOW: Task is isolated to single-file fixes, shallow tweaks, or documentation updates.
  * MEDIUM: Task has moderate architectural depth, affecting internal logic patterns or specific layer wrappers.
  * HIGH: Task has deep architectural depth or high breadth, spanning multiple system components simultaneously (e.g., changes across the SDK, backend, frontend, or argo compiler engines).>
- <Break down the breadth (cross-layer impact) and depth (internal system complexity) of the proposed change>


### 🎯 Overall Issue Quality Verdict
- <State definitively if this is ready for immediate developer pickup>
- <Outline the single most impactful recommendation to improve the issue quality>"""

    user_prompt = f"Title: {title} | Body: {truncate_text(raw_body)}"

    print(f"Using model: {model}")

    analysis_report = ""

    try:
        # Run gh models CLI command
        result = subprocess.run(
            [
                "gh", "models", "run", model,
                "--system-prompt", system_instructions,
                user_prompt
            ],
            capture_output=True,
            text=True,
            check=True
        )
        analysis_report = result.stdout.strip()
        print("AI model executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ CRITICAL: AI Model execution failed: {e.stderr}")
        if "rate limit" in e.stderr.lower():
            analysis_report = "### ⚠️ Automated Triage Skipped\nRate limit reached for the AI model tier. The action will retry on subsequent triggers."
        else:
            analysis_report = "### ⚠️ Automated Triage Skipped\nThe issue body text or environment logs exceeded processing size boundaries for this triage pass."

    # Write output for GitHub Actions safely
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a") as f:
            f.write("analysis<<EOF\n")
            f.write(analysis_report + "\n")
            f.write("EOF\n")

if __name__ == "__main__":
    main()