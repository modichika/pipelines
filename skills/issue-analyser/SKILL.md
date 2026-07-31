---
name: issue-analyser
description: Analyse open issues against KFP standards, evaluate quality, recommend area labels, and post triage comments.

---

# Skill: Kubeflow Pipelines Issue Quality Triager & Commenter

## Description
Fetche open issues from the `kubeflow/pipelines` repository, analyze their engineering density against blueprint standards, generate a highly concise quality report, and provide a direct automated action to apply component labels and post the final review comment back to GitHub.

## Prerequisites
- The user must be authenticated via the GitHub CLI (`gh auth login`).
- The active terminal workspace must have internet access to communicate with the GitHub API and the local LLM inference backend.

## Execution Sequence
1. Run `gh issue list --limit 10 --json number,title,body` to fetch recent open tickets.
2. Display the list to the maintainer and ask: "Which issue number would you like to triage?"
3. Once a number is selected, fetch the full issue text using: `gh issue view <NUMBER>`
4. Run the issue payload through the evaluation rubric defined below.
5. Identify the appropriate repository labels to apply based on the **Automated Labeling Engine** logic.
6. Display the generated markdown analysis and the proposed labels on-screen to the maintainer.
7. **Wait for confirmation.** Ask the maintainer: "Would you like me to apply the labels and post this analysis to the issue thread now?"
8. Upon confirmation, execute the tasks sequentially via the GitHub CLI tool:
   ```bash
   gh issue edit <NUMBER> --add-label "<PROPOSED_LABEL>"
   gh issue comment <NUMBER> --body "<GENERATED_MARKDOWN_ANALYSIS>"
   ```

---

## Evaluation Rubric & Calibration Standards

Analyze the quality of the incoming issue based on Scope, Context, Guidance, and Complexity. Calibrate evaluations strictly against these compressed KFP reference standards:

- **BACKEND (#13314)**: [backend] S3 operations fail with non-AWS object stores after AWS SDK v2 checksum defaults change. *Standard: Clear isolated scope.*
- **BUG TIER (#13180)**: [bug] fix: E2E test flakiness on K8s v1.34.0 — root cause analysis. *Standard: High-quality root-cause data and explicit cluster environment metrics.*
- **FRONTEND (#13108)**: [frontend] Adds coverage for frontend mock:api startup and enum drift. *Standard: Explicit file paths and clear definitions of done.*
- **SDK (#12865)**: [sdk] [bug] [set_accelerator_limit] rejects valid accelerator counts (only allows 0, 1, 2, 4, 8, 16). *Standard: Elite technical precision with exact failing parameter layouts.*

Compare the incoming issue detail density directly against the relevant blueprint standard above.

---

## Automated Labeling Engine

Analyze the text content to select the single most accurate component label and status label from the following official `kubeflow/pipelines` categories:

### 🧩 Component Categories (Choose One)
- `area/sdk`: Content mentions Python DSL, compiler, components, pipelines building, or local client execution.
- `area/backend`: Content mentions API server, scheduled workflow engines, persistence agent, object storage (S3/MinIO), or metadata storage.
- `area/frontend`: Content mentions UI dashboard, pipeline runs viewer, visualization components, or frontend server.
- `area/testing`: Content isolates test suites, CI/CD flakiness, or test cluster environments.

### 🚦 Status & Lifecycles (Choose One)
- `lifecycle/needs-information`: If the quality report marks **Ready for Pickup** as **NO**.
- `status/triaged`: If the quality report marks **Ready for Pickup** as **YES**.

---

## Output Formatting Rules

Generate the report string strictly following this format structure. Do not use full-length paragraphs, markdown code wraps, introductory text, or implementation timeframe windows:

### 📊 Scope
- <State if the technical task boundaries are clear or ambiguous based on the text>
- <State if the issue isolates specific KFP components, files, or packages correctly>

### 📝 Context & Guidance
- <Evaluate if step-by-step reproduction steps, expected behavior, or links are provided against repo standards>

### ⚡ Complexity
- **Difficulty Tier:** <State difficulty tier: LOW, MEDIUM, or HIGH, calibrated against this exact rubric:>
  * *LOW*: Task is isolated to single-file fixes, shallow tweaks, or documentation updates.
  * *MEDIUM*: Task has moderate architectural depth, affecting internal logic patterns or specific layer wrappers.
  * *HIGH*: Task has deep architectural depth or high breadth, spanning multiple system components simultaneously (e.g., changes across the SDK, backend, frontend, or argo compiler engines).
- **Architecture Breadth & Depth:** <Briefly break down cross-layer impacts and internal system component overlap>

### 🎯 Overall Issue Quality Verdict
- **Ready for Pickup:** <State definitively YES or NO if this is ready for immediate developer pickup>
- **Key Recommendation:** <Outline the single most impactful structural recommendation to improve the issue quality layout>
- **Proposed Labels:** <List the identified Area and Status labels to apply>
