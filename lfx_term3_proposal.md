# CNCF LFX Mentorship Proposal: Abstracting Pod Lifecycle Diagnostics for Kubeflow Pipelines

**Program Name:** Abstracting Pod Lifecycle Diagnostics for Kubeflow Pipelines  
**CNCF Project:** Kubeflow (Kubeflow Pipelines)  
**Term:** 2026 Term 3 (September – November 2026)  
**Upstream Issue:** [kubeflow/pipelines#12843](https://github.com/kubeflow/pipelines/issues/12843)  
**Mentors:** Alyssa Goins (@alyssacgoins - Red Hat), Matt Prahl (@mprahl - Red Hat)  
**Target Solution:** Option D — Unified End-to-End Diagnostic Pipeline (Full-Stack Native Abstraction)  

---

## Table of Contents
1. [Applicant Information & Motivation](#1-applicant-information--motivation)
2. [Executive Summary](#2-executive-summary)
3. [Background & Problem Statement](#3-background--problem-statement)
4. [Root Cause & Architectural Gap Analysis](#4-root-cause--architectural-gap-analysis)
5. [Proposed Solution Architecture (Option D)](#5-proposed-solution-architecture-option-d)
6. [Detailed Technical Specification](#6-detailed-technical-specification)
   - [6.1 Go Backend Engine & Event Listener](#61-go-backend-engine--event-listener)
   - [6.2 Log Pipeline Repair & Timeout Manager](#62-log-pipeline-repair--timeout-manager)
   - [6.3 Protobuf & OpenAPI Schema Extension](#63-protobuf--openapi-schema-extension)
   - [6.4 Frontend Visual Console Upgrade (React 19 / MUI)](#64-frontend-visual-console-upgrade-react-19--mui)
7. [Phase-by-Phase Execution Plan](#7-phase-by-phase-execution-plan)
8. [Testing & Quality Assurance Strategy](#8-testing--quality-assurance-strategy)
9. [12-Week Detailed Implementation Timeline](#9-12-week-detailed-implementation-timeline)
10. [Risk Assessment & Edge Case Management](#10-risk-assessment--edge-case-management)
11. [Community Enablement, Documentation & Long-Term Impact](#11-community-enablement-documentation--long-term-impact)

---

## 1. Applicant Information & Motivation

### Personal Details
- **Name:** [Applicant Name]
- **Email:** [applicant@example.com]
- **GitHub:** [@applicant-github]
- **LinkedIn:** [linkedin.com/in/applicant]
- **Timezone:** Indian Standard Time (IST / UTC +5:30)
- **Primary Languages & Skills:** Go, TypeScript/React, Kubernetes (`kubectl`, Go Client, CRDs), Protobuf/gRPC, Python

### Why This Project?
Kubeflow Pipelines (KFP) serves as the primary abstraction bridge between Machine Learning engineers and distributed Kubernetes clusters. Having worked with cloud-native ML workloads, I have personally experienced the frustration of a pipeline run freezing without clear diagnostic feedback, forcing a context switch to `kubectl describe pod` and analyzing raw K8s events. 

This project directly addresses that technical friction by bringing native pod lifecycle diagnostics to KFP. Abstracting low-level infrastructure failures while retaining full visibility inside the KFP UI console represents a massive usability leap for the entire Kubeflow community.

---

## 2. Executive Summary

To abstract Kubernetes infrastructure workload for data scientists and ML engineers, Kubeflow is designed so that they can focus entirely on logic building. When a low-level infrastructure failure, a pod lifecycle failure occurs -  at the provisioning level (e.g., ImagePullBackOff or Unschedulable), runtime level (e.g., CrashLoopBackOff or OOMKilled), or node level (e.g., NodeLost or Preempted) the KFP UI freezes in pending state while the Kubernetes CLI allow the users to leave KFP UI and run kubectl get pods - w to view the status of their pipeline pods in real time. 

I am proposing a solution to extend the backend/src/agent/persistence that currently catches the high-level run statuses - Pending, Running, Succeeded, Failed to also catch the low-level infrastructure pod lifecycle failures directly from Kubernetes raw v1.PodStatus  and store it in the database(MLMD/KFP database) and then show it in the KFP UI highlighting the exact failure reasons, necessary docs url and color-coded.

---

## 3. Background & Problem Statement

### The Core Mission of Kubeflow Pipelines
Kubeflow Pipelines allows data scientists to compose complex machine learning workflows using a Python SDK, compile them into declarative pipeline specifications, and execute them on Kubernetes clusters. The KFP UI visualizes execution graphs as Directed Acyclic Graphs (DAGs), enabling users to monitor task progression, track artifacts, and review execution logs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER MENTAL MODEL                                │
│   Python SDK  ──►  KFP Pipeline Spec  ──►  KFP UI Console Graph            │
│   (ML Code)        (Pipeline Spec)         (Task Execution Nodes)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Abstracted Away
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES INFRASTRUCTURE                           │
│   Pod Scheduling  ──►  Container Runtime  ──►  Cluster Nodes / Memory       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Where the Abstraction Breaks
While KFP gracefully handles errors originating from *user-supplied Python code* (e.g., Python exceptions or assertion failures inside a container), it fails when errors occur at the *Kubernetes pod infrastructure layer*. 

Pods can fail at three distinct infrastructure phases:
1. **Provisioning / Scheduling Level:** `ImagePullBackOff`, `ErrImagePull`, `InvalidImageName`, `Unschedulable` (insufficient CPU/GPU/RAM quota, taint/toleration mismatches).
2. **Runtime Container Level:** `OOMKilled` (exceeding memory limits), `CrashLoopBackOff`, `ContainerCannotRun`.
3. **Node / Cluster Level:** `NodeLost`, `NodeUnreachable`, Cloud Provider Spot Instance `Preempted`.

### Impact on Target Users
When any of these failures occur:
- The KFP UI displays a node stuck in `Running` or `Pending` without failure details.
- Failure messages generated by Argo Workflows during pod termination are dropped in the persistence layer.
- ML engineers are forced to authenticate to K8s CLI, run `kubectl get pods -n kubeflow`, `kubectl describe pod <pod-id>`, and manually interpret K8s event logs.

---

## 4. Root Cause & Architectural Gap Analysis

### 1. Ingestion Gap in KFP Persistence Agent (`backend/src/agent/persistence`)
The KFP Persistence Agent syncs Argo Workflow states into the KFP MySQL database via `WorkflowSaver.Save()`. When a pod hits a lifecycle state like `ImagePullBackOff` or `Unschedulable`, the pod itself has not exited cleanly with an Argo workflow status update. The KFP backend ignores transient K8s pod event streams, resulting in unhandled or dropped status transitions.

### 2. Schema Gap in KFP API Contract (`api/v2beta1`)
The KFP API schema defines execution status primarily in terms of `SUCCEEDED`, `FAILED`, `RUNNING`, or `PENDING`. It lacks a structured representation for *pod lifecycle diagnostic details*, preventing the backend from communicating fine-grained failure causes (such as exit status 137 for `OOMKilled`) to client applications.

### 3. Visualization Gap in Frontend UI (`frontend/src`)
The frontend DAG component relies on high-level node status strings. Without granular diagnostic metadata, the UI cannot distinguish between a pod actively pulling a 10GB container image and a pod permanently stuck in `ImagePullBackOff`.

---

## 5. Proposed Solution Architecture (Option D)

Option D implements a native, end-to-end diagnostic pipeline that handles pod lifecycle events cleanly across the backend, API schema, and frontend UI.

```
                                  SYSTEM ARCHITECTURE (OPTION D)

 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 KUBERNETES CONTROL PLANE                                 │
 │  [ Pod Conditions ] ──► [ Container Statuses (Exit 137) ] ──► [ K8s Event Stream ]       │
 └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   GO BACKEND ENGINE                                      │
 │  ┌─────────────────────────────────┐   ┌──────────────────────────────────────────────┐  │
 │  │ Pod Event & Condition Watcher   │   │ Repaired Workflow Log Persistence Pipeline   │  │
 │  └────────────────┬────────────────┘   └──────────────────────┬───────────────────────┘  │
 │                   │                                           │                          │
 │                   ▼                                           ▼                          │
 │  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
 │  │                      Per-Error Custom Timeout & Fast-Fail Manager                  │  │
 │  └─────────────────────────────────────────┬──────────────────────────────────────────┘  │
 └────────────────────────────────────────────┼─────────────────────────────────────────────┘
                                              │ Ingests & Persists into DB / MLMD
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 PROTOBUF API LAYER (`v2beta1`)                            │
 │  `PodLifecycleDiagnostics`: { state, reason_code, raw_message, human_text, doc_url }     │
 └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ Consumed via REST / gRPC API
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   FRONTEND UI CONSOLE                                    │
 │  ┌───────────────────────────────┐ ┌───────────────────────────┐ ┌────────────────────┐ │
 │  │ Visual DAG Node Badges        │ │ Inline Diagnostic Banner  │ │ Educational        │ │
 │  │ (Amber/Red/Purple Statuses)   │ │ (Human-Readable Summary)  │ │ Hover Tooltips     │ │
 │  └───────────────────────────────┘ └───────────────────────────┘ └────────────────────┘ │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Detailed Technical Specification

### 6.1 Go Backend Engine & Event Listener

The Go backend will be upgraded to capture pod lifecycle events in real time without introducing significant overhead on the K8s API server.

1. **Pod Condition Watcher:**
   - Extend `backend/src/agent/persistence/client/workflow_client.go` and `workflow_saver.go` to listen to pod status conditions.
   - Extract `status.containerStatuses[*].state.waiting.reason` and `status.containerStatuses[*].state.terminated.reason`.
2. **Classification Engine:**
   - Map raw K8s status codes to structured diagnostic categories:

| K8s Pod State / Event | Diagnostic Classification | Diagnostic Action |
| :--- | :--- | :--- |
| `ImagePullBackOff` / `ErrImagePull` | `PROVISIONING_FAILED` | Fast-fail task after configurable timeout; flag invalid image URL. |
| `Unschedulable` | `SCHEDULING_FAILED` | Flag missing node resources (CPU/GPU/RAM) or unsatisfied affinity. |
| `OOMKilled` (Exit 137) | `RUNTIME_CRASHED` | Identify memory limit exceedance; compute requested vs. required limit. |
| `Preempted` / `NodeLost` | `NODE_EVICTED` | Mark as evicted; trigger automatic retry if task retry policy exists. |

### 6.2 Log Pipeline Repair & Timeout Manager

1. **Preventing Log Drops in Persistence Pipeline:**
   - Modify `WorkflowSaver.Save()` in `backend/src/agent/persistence/worker/workflow_saver.go` to ensure pod status reason and message buffers are preserved during workflow completion or abort phases.
   - Ensure `ReportWorkflow` persists pod failure payloads into MySQL even when Argo Workflow reports an unhandled pod failure.
2. **Per-Error Custom Timeout Engine:**
   - Implement customizable timeout policies in `backend/src/apiserver/server/run_server.go`:
     - **Deterministic Image/Syntax Errors:** Trigger immediate fail-fast timeout (e.g., 2 minutes) instead of waiting for default execution timeout (hours).
     - **Transient Infrastructure Evictions:** Apply exponential backoff grace periods for node re-scheduling.

### 6.3 Protobuf & OpenAPI Schema Extension

Modify `api/v2beta1/pipeline_spec.proto` and `report.proto` to introduce standardized diagnostic fields:

```protobuf
syntax = "proto3";

package kubeflow.pipelines.backend.api.v2beta1;

// PodLifecycleDiagnostics holds structured failure details for pod infrastructure errors.
message PodLifecycleDiagnostics {
  enum LifecycleState {
    LIFECYCLE_STATE_UNSPECIFIED = 0;
    PROVISIONING_FAILED = 1; // ImagePullBackOff, ErrImagePull, InvalidImageName
    SCHEDULING_FAILED = 2;   // Unschedulable, ResourceQuotaExceeded
    RUNTIME_CRASHED = 3;     // OOMKilled, CrashLoopBackOff, ContainerCannotRun
    NODE_EVICTED = 4;        // NodeLost, NodeUnreachable, Preempted
  }

  LifecycleState state = 1;
  string reason_code = 2;         // e.g. "OOMKilled"
  string raw_message = 3;         // e.g. "Command terminated with exit code 137"
  string human_explanation = 4;    // e.g. "The container ran out of memory."
  string remediation_hint = 5;    // e.g. "Increase task memory limit via .set_memory_limit()"
  string documentation_url = 6;   // Link to Kubeflow troubleshooting docs
}
```

Regenerate backend Go code and frontend OpenAPI clients:
```bash
make -C api golang
make -C api python
cd frontend && npm run apis:all
```

### 6.4 Frontend Visual Console Upgrade (React 19 / MUI)

The frontend console (`frontend/src/pages/RunDetails.tsx` and DAG components) will be updated with intuitive visual indicators:

1. **Color-Coded DAG Node Status Badges:**
   - 🟧 **Amber Badge (`PROVISIONING_FAILED` / `SCHEDULING_FAILED`):** Displayed when pod is stuck pulling images or pending node allocation.
   - 🟥 **Dark Red Badge (`RUNTIME_CRASHED` / `OOMKilled`):** Displayed when container crashes due to OOM or runtime panic.
   - 🟪 **Striped Purple Badge (`NODE_EVICTED`):** Displayed when underlying node was preempted or lost.

2. **Inline Diagnostic Banner:**
   - Render a high-visibility alert banner above the log viewer tab:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚠️  Pod Lifecycle Failure: OOMKilled (Exit Code 137)                                  │
│ The container was terminated because it exceeded its allocated memory limit (8Gi).     │
│ 💡 Recommendation: Update component specification to request additional RAM.            │
│ 🔗 Documentation: https://www.kubeflow.org/docs/components/pipelines/troubleshooting  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

3. **Interactive Educational Tooltips:**
   - Hovering over a failed or pending DAG node triggers a tooltip summarizing the failure reason and providing a direct link to troubleshooting documentation.

---

## 7. Phase-by-Phase Execution Plan

### **Phase 1: Backend Event Capture & Log Pipeline Repair (Weeks 1–4)**
- Implement K8s Pod event/condition parsing in `backend/src/agent/persistence`.
- Resolve log-dropping bug in `WorkflowSaver.Save()` and `ReportWorkflow`.
- Add backend unit tests using Go `fake` clients and Ginkgo integration suites.

### **Phase 2: Protobuf Contract & Code Generation (Weeks 5–6)**
- Define `PodLifecycleDiagnostics` in Protobuf files under `api/v2beta1/`.
- Run generation scripts (`make -C api golang`, `make -C api python`, `npm run apis:all`).
- Update API server response handlers to serve diagnostic metadata.

### **Phase 3: Frontend Visual Console & UX (Weeks 7–9)**
- Integrate diagnostic metadata into React 19 / MUI DAG components.
- Implement color-coded status badges, inline failure banners, and educational tooltips.
- Add UI tests using Vitest and React Testing Library (`npm run test:ui`).

### **Phase 4: Timeout Manager, Enablement & Documentation (Weeks 10–12)**
- Implement per-error custom timeout handling in API server.
- Write documentation for the KFP repo and Kubeflow website.
- Build an interactive web demo demonstrating pod failure diagnostics.

---

## 8. Testing & Quality Assurance Strategy

In accordance with the repository's testing policy (`AGENTS.md`), all code changes will be thoroughly tested locally before submission.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TESTING SUITE STRATEGY                           │
│                                                                             │
│  Backend Go Unit Tests  ──►  `go test -v ./backend/src/agent/...`           │
│  Ginkgo API & Compiler  ──►  `ginkgo -v ./backend/test/v2/api`               │
│  Frontend Vitest UI     ──►  `npm run test:ui`                              │
│  E2E Kind Cluster       ──►  `make -C backend kind-cluster-agnostic`        │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Go Unit & Integration Tests:**
   - Write unit tests for `WorkflowSaver` in `backend/src/agent/persistence/worker/workflow_saver_test.go`.
   - Run Ginkgo compiler and API integration tests:
     ```bash
     ginkgo -v ./backend/test/compiler
     ginkgo -v ./backend/test/v2/api
     ```
2. **Frontend Vitest UI Testing:**
   - Add unit and snapshot tests for visual status badges and diagnostic banners in `frontend/src`.
   - Run full frontend test suite:
     ```bash
     cd frontend && npm run test:ui
     ```
3. **End-to-End Cluster Testing:**
   - Spin up a local Kind development cluster using:
     ```bash
     make -C backend kind-cluster-agnostic
     ```
   - Deploy sample pipelines designed to trigger `ImagePullBackOff`, `Unschedulable`, and `OOMKilled` states, verifying end-to-end diagnostic propagation to the UI.

---

## 9. 12-Week Detailed Implementation Timeline

```
WEEKS 1-2      WEEKS 3-4      WEEKS 5-6      WEEKS 7-8      WEEKS 9-10     WEEKS 11-12
[  Go Event  ][ Log Pipeline ][ Protobuf API ][  React UI   ][  Timeout   ][ Docs & Demo ]
[ Collector  ][   Repair     ][ Definitions  ][ Diagnostics ][  Manager   ][ Integration ]
```

### **Community Bonding Period (Pre-Mentorship)**
- Connect with mentors Alyssa Goins and Matt Prahl to refine architectural design choices.
- Setup local Kind cluster development environment and verify full stack build workflows.

### **Week 1 – 2: Go Backend Event Collector**
- Add pod event/condition parsing to KFP Persistence Agent (`backend/src/agent/persistence`).
- Implement classification logic for `ImagePullBackOff`, `Unschedulable`, `OOMKilled`, and `Preempted`.
- Add unit tests for event classification utilities.

### **Week 3 – 4: Log Pipeline Repair & Backend Persistence**
- Fix Argo Workflow log dropping bug in `WorkflowSaver.go` and `ReportWorkflow`.
- Persist pod failure status messages into MySQL database and MLMD.
- Run Go unit tests and Ginkgo API test suites.

### **Week 5 – 6: Protobuf API & Client Generation**
- Define `PodLifecycleDiagnostics` in `api/v2beta1/pipeline_spec.proto` and `report.proto`.
- Generate Go, Python, and TypeScript OpenAPI clients (`make -C api golang`, `npm run apis:all`).
- Update API server handler endpoints to return diagnostic payload.

### **Week 7 – 8: Frontend Visual DAG Console**
- Add color-coded lifecycle status badges (Amber, Red, Purple) to DAG nodes in React UI.
- Create reusable `PodDiagnosticBanner` component in MUI v5.
- Write Vitest unit tests for visual UI components.

### **Week 9 – 10: Educational Tooltips & Custom Timeout Manager**
- Implement educational hover tooltips with troubleshooting documentation links.
- Build per-error custom timeout engine in API server (fast-fail for bad images/scheduling).
- Verify timeout policies on local Kind cluster.

### **Week 11 – 12: Documentation, Interactive Demo & Polish**
- Author comprehensive documentation for KFP repo and Kubeflow website.
- Create an interactive web demo showing live pod lifecycle diagnostic handling.
- Perform final code cleanup, verify all lint/test checks pass, and submit upstream PRs.

---

## 10. Risk Assessment & Edge Case Management

| Potential Risk / Challenge | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **K8s API Server Rate Limiting** under high cluster load | Medium | Use cached Informers in Go client rather than polling K8s API directly. |
| **Multi-Tenant Security Boundaries** | High | Enforce strict namespace isolation in Persistence Agent; never leak pod events across user namespaces. |
| **Backward Compatibility** with older KFP pipeline specs | Low | Treat `PodLifecycleDiagnostics` as an optional field in proto responses; fall back gracefully to standard status if missing. |
| **Garbage Collected Pods** | Medium | Persist diagnostic metadata to database immediately on pod failure so historical runs retain failure context. |

---

## 11. Community Enablement, Documentation & Long-Term Impact

### Community Enablement
- **Troubleshooting Guide:** Publish a user-facing guide titled *"Understanding Pod Lifecycle Diagnostics in KFP"* on `kubeflow.org`.
- **Interactive Web Demo:** Host a lightweight web demo illustrating how KFP captures and displays infrastructure failures without `kubectl`.

### Long-Term Impact
By abstracting Kubernetes pod lifecycle failures natively inside Kubeflow Pipelines, this project eliminates major technical friction for data scientists and ML engineers. It reinforces KFP's core value proposition: providing a seamless, production-ready machine learning platform where infrastructure complexity is hidden behind intuitive visual abstractions.



agy restart the chat 702e7580-11ee-40b5-8b92-bb7196fa55c8/Abstracting Pod Lifecycle Diagnostics.
---

