# LFX Mentorship Proposal: Pod Lifecycle Diagnostics for KFP

**CNCF Issue:** [#1928](https://github.com/cncf/mentoring/issues/1928) | **Upstream:** [#12843](https://github.com/kubeflow/pipelines/issues/12843) | **Term:** 2026 Term 3 (Sep–Nov)  
**Mentors:** Alyssa Goins ([@alyssacgoins](https://github.com/alyssacgoins)), Matt Prahl ([@mprahl](https://github.com/mprahl)) | **Applicant:** [Student Name]

---

### 1. Root Cause Analysis & Project Objective
[Kubeflow Pipelines](https://github.com/kubeflow/pipelines) (KFP) abstracts Kubernetes for ML workloads. However, when a task pod experiences a **Pod Lifecycle Failure** (`ImagePullBackOff`, `Unschedulable`, `CrashLoopBackOff`, `OOMKilled`, `NodeLost`), the abstraction breaks down.

**Root Cause:**
1. KFP relies solely on Argo `Workflow` CRD status updates. Argo does not stream container waiting states or Kubelet events, causing tasks to freeze in `Pending`/`Running` indefinitely.
2. `persistence-agent` only watches Workflow CRDs, dropping Pod-level failure reasons before they reach the API Server or Database.
3. Users are forced to drop down to `kubectl` CLI debugging, leaking the abstraction.

**Goal:** Build an end-to-end architecture across `persistence-agent`, `ml-pipeline` API Server, MySQL DB/MLMD, Protobuf contracts, and React UI to capture, store, enforce timeouts for, and visually present Pod lifecycle failures inside the KFP Console.

---

### 2. Architecture: Watcher, APIServer & Database Integration

**Data Flow:**  
`[Pod Namespace]` ──► `[K8s API/etcd]` ──► `[persistence-agent Watcher]` ──► `[ml-pipeline API Server]` ──► `[MySQL DB / MLMD]` ──► `[KFP React UI]`

* **Phase A: Go Watcher (`persistence-agent`):** Extend `PersistenceAgent` ([`persistence_agent.go`](file:///home/shristi/pipelines/backend/src/agent/persistence/persistence_agent.go)) with a `PodInformer` & `EventInformer` (`client-go`) filtered by `workflows.argoproj.io/workflow`. Extract container states (`Waiting.Reason`: `ImagePullBackOff`, `Terminated.Reason`: `OOMKilled`) and Pod conditions (`PodScheduled=False`). Map Pods to tasks via `workflows.argoproj.io/node-name` and report diagnostic payloads to the API Server.
* **Phase B: APIServer & Database State Engine:**
  * **Proto Schema:** Update `run.proto` ([`PipelineTaskDetail`](file:///home/shristi/pipelines/backend/api/v2beta1/run.proto#L320)) adding `PodLifecycleState` enum & `PodLifecycleDetail` message (`state`, `reason`, `message`, `last_transition_time`).
  * **APIServer Timeout Engine:** Add configurable timeout evaluators (`PROVISIONING_TIMEOUT_SECONDS`, `CRASH_LOOP_TIMEOUT_SECONDS`) in `ml-pipeline` API Server to trigger controlled workflow termination when thresholds are breached.
  * **Database & MLMD Persistence:** Update API Server persistence layer (`resource_manager`) to write `PodLifecycleDetail` into MySQL database tables and MLMD Execution custom properties *before* task termination, repairing the data pipeline so failure logs are never lost.
* **Phase C: React 19 UI Diagnostics:** Upgrade DAG Graph and Details drawer in [`frontend/src/`](file:///home/shristi/pipelines/frontend/src/). Display Amber/Orange badges for provisioning warnings and Red badges for runtime/node failures, alongside inline diagnostic banners and hover tooltips linking to docs.

---

### 3. Why This Architecture Solves the Root Cause

1. **Direct Event Stream:** Bypasses Argo CRD polling delay by having `persistence-agent` watch `Pod` & `Event` resources in etcd directly.
2. **Active Timeout Policy:** Moves timeout responsibility to `ml-pipeline` API Server, preventing frozen runs.
3. **Repaired Data Pipeline:** Guarantees `PodLifecycleDetail` is stored in MySQL DB and MLMD before pod teardown.
4. **Complete Abstraction:** Exposes structured failure reasons directly in the UI, eliminating any `kubectl` CLI usage.

---

### 4. Timeline & Verification Plan

* **Pre-Term:** Align on proto schemas; set up local Kind cluster (`make -C backend kind-cluster-agnostic`).
* **W1–W4 (Phase A):** Add `PodInformer` & `EventInformer` to `persistence-agent`; update `run.proto` & regenerate code (`make -C api golang`).
* **W5–W8 (Phase B):** Implement APIServer timeouts & MySQL/MLMD persistence; write Ginkgo integration tests (`backend/test/v2/api`).
* **W9–W12 (Phase C):** Update React UI with status badges & tooltips; add Vitest tests (`npm run test:ui`); publish docs & demo.
* **Qualifications:** Proficient in Go (`client-go`, informers, gRPC), MySQL/MLMD schemas, TypeScript/React 19, and KFP v2 architecture.
