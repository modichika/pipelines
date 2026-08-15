
Abstracting Pod Lifecycle Diagnostics for Kubeflow Pipelines

By Shristi GitHub: shristi
Upstream Issue:  Enhance support and visualization for pod lifecycle failure in Kubeflow Pipelines
Mentors: Alyssa Goins, Matt Prahl 
Target Solution: Unified End-to-End Diagnostic Pipeline (Full-Stack Native Abstraction)
Table of Contents
1. Introduction
Personal Details
Why This Project?
2. Summary
3. Root Cause Analysis
    1. Ingestion Gap in KFP Persistence Agent (backend/src/agent/persistence)
    2. Schema Gap in KFP API Contract (api/v2beta1)
    3. Visualization Gap in Frontend UI (frontend/src)
4. Proposed Solution Architecture
5. Detailed Technical Specification
5.1 Go Backend Engine & Event Listener
5.2 Log Pipeline Repair & Timeout Manager
5.3 Protobuf & OpenAPI Schema Extension
5.4 Frontend Visual Console Upgrade (React 19 / MUI)
6. Testing Strategy
7. 12-Week Implementation Timeline
Week 1 – 2: Go Backend Event Collector
Week 3 – 4: Log Pipeline Repair & Backend Persistence
Week 5 – 6: Protobuf API & Client Generation
Week 7 – 8: Frontend Visual DAG Console
Week 9 – 10: Educational Tooltips & Custom Timeout Manager
Week 11 – 12: Documentation, Interactive Demo & Polish






1. Introduction
Personal Details
Name: Shristi
Email: shristimodi95@gmail.com
GitHub: shristi
LinkedIn: shristi 
Timezone: Indian Standard Time (IST / UTC +5:30)
University: K.K. College Of Engineering and Management



Hi, I'm Shristi, a last-year engineering student with expertise in Golang, DevOps, Kubernetes, and cloud. For the last 4 months, I have been actively contributing to the Kubeflow project and related repositories[kubeflow/pipelines, kubeflow/trainer, kubeflow/mcp-server, kubeflow/docs-agent], with pull requests successfully merged and opened, under review across various technical areas, and issues assigned. I have a good understanding about Kubeflow/pipelines’s working and codebase. 





CONTRIBUTIONS:
#
Repository
PR
Description








1.
kubeflow/pipelines
#13653


2. 
kubeflow/pipelines
#13707


3. 
kubeflow/pipelines
#13596


4. 
kubeflow/pipelines
#13372  




Why This Project?
Kubeflow Pipelines (KFP) serves as the primary abstraction bridge between Machine Learning engineers and distributed Kubernetes clusters. Having worked with cloud-native ML workloads, I have experienced the frustration of a pipeline run freezing without clear diagnostic feedback, forcing a context switch to kubectl describe pod and analyzing raw K8s events.
This project addresses that technical friction by bringing native pod lifecycle diagnostics to KFP. Abstracting low-level infrastructure failures while retaining UI visibility inside the KFP UI console represents a usability leap for the entire Kubeflow community.
I have been contributing to Kubeflow Pipelines a lot recently, collaborating with core maintainers there and being active in the community meetings.



2. Summary
To abstract Kubernetes infrastructure workload for data scientists and ML engineers, Kubeflow is designed so that they can focus entirely on model development/training. When a low-level infrastructure failure, a pod lifecycle failure occurs -  at the provisioning level (e.g., ImagePullBackOff or Unschedulable), runtime level (e.g., CrashLoopBackOff or OOMKilled), or node level (e.g., NodeLost or Preempted) the forcing the data scientist/MLE to leave the KFP UI and investigate the issue themselves that requires deep knowledge of Kubernetes.

I am proposing a solution to extend the backend/src/agent/persistence that currently catches the high-level run statuses - Pending, Running, Succeeded, Failed to also catch the low-level infrastructure pod lifecycle failures directly from Kubernetes execution workflow states and store it in the native KFP API Server database (MySQL DB) via native KFP Task (`PipelineTaskDetail`) and Artifact APIs (aligning with KFP's MLMD Removal Architecture #12147), then show it in the KFP UI highlighting the exact failure reasons, necessary docs url and color-coded. This architecture solves the root-cause of the problem by directly aiming to bridge Kubernetes pods' event logs to KFP’s event logs. 

Instead of touching the surface level like frontend, or just changing the Argo-Workflow node.message, I propose to handle the root-cause by extending agent/persistence because it’s responsible to watch Kubernetes pods events across the cluster and listens to live Argo workflow.




3. Root Cause Analysis

1. Ingestion Gap in KFP Persistence Agent (backend/src/agent/persistence)
The KFP Persistence Agent syncs Argo Workflow states into the KFP MySQL database via WorkflowSaver.Save(). When a pod hits a lifecycle state like ImagePullBackOff or Unschedulable, the pod itself has not exited cleanly with an Argo workflow status update. The KFP backend ignores transient K8s pod event streams, resulting in unhandled or dropped status transitions.
2. Schema Gap in KFP API Contract (api/v2beta1)
The KFP API schema defines execution status primarily in terms of SUCCEEDED, FAILED, RUNNING, or PENDING. It lacks a structured representation for pod lifecycle diagnostic details, preventing the backend from communicating fine-grained failure causes (such as exit status 137 for OOMKilled) to client applications.
3. Visualization Gap in Frontend UI (frontend/src)
The frontend DAG component relies on high-level node status strings. Without granular diagnostic metadata, the UI cannot distinguish between a pod actively pulling a 10GB container image and a pod permanently stuck in ImagePullBackOff.



4. Proposed Solution Architecture
This proposed solution implements a native, end-to-end diagnostic pipeline that handles pod lifecycle events cleanly across the backend, API schema, and frontend UI.

Presenting architectures through mermaid and miro diagrams:
Architecture that shows how each component connects


Mermaid_diagram
Architecture that deep-dives into folders and files 


Miro_Architecture






5. Detailed Technical Specification
5.1 Go Backend Engine & Event Listener
The Go backend will be upgraded to capture pod lifecycle events in real time without introducing significant overhead on the K8s API server.
Engine-Agnostic Execution Diagnostic Extractor:
In accordance with KFP architectural boundary guidelines (AGENTS.md), diagnostic extraction is designed to be engine-agnostic at the persistence layer. Rather than spawning a cluster-wide K8s PodInformer (which adds API server watch overhead and tightly couples persistence-agent to etcd Pod CRDs), persistence-agent leverages its existing `execInformer` stream.
Extend WorkflowSaver in `backend/src/agent/persistence/worker/workflow_saver.go` with an `ExtractPodDiagnostics(wf *util.Workflow)` extractor method to scrape container wait reasons (`ImagePullBackOff`, `CrashLoopBackOff`), pod conditions (`Unschedulable`), and exit statuses directly from the `Workflow`/`Execution` object status.
Classification Engine:
Map raw K8s status codes to structured diagnostic categories:
K8s Pod State / Event | Diagnostic Classification | Diagnostic Action
ImagePullBackOff / ErrImagePull | PROVISIONING_FAILED | Fast-fail task after configurable timeout; flag invalid image URL.
Unschedulable | SCHEDULING_FAILED | Flag missing node resources (CPU/GPU/RAM) or unsatisfied affinity.
Invalid StorageClass / PVC ProvisioningFailed | PROVISIONING_FAILED | Fast-fail task immediately (60s); flag missing/invalid storageClassName or quota breach.
CrashLoopBackOff | RUNTIME_CRASH | Active fail-fast after threshold (3 consecutive crashes or 3 min duration); flag startup syntax/import error.
OOMKilled (Exit 137) | OUT_OF_MEMORY_CRASH | Identify memory limit exceedance; compute requested vs. required limit.
Preempted / NodeLost | NODE_EVICTED | Mark as evicted; trigger automatic retry if task retry policy exists.

5.2 Log Pipeline Repair & Timeout Manager
Preventing Log Drops in Persistence Pipeline:
Modify WorkflowSaver.Save() in backend/src/agent/persistence/worker/workflow_saver.go to ensure pod status reason and message buffers are preserved during workflow completion or abort phases.
Ensure ReportWorkflow persists pod failure payloads into MySQL even when Argo Workflow reports an unhandled pod failure.

Per-Error Custom Timeout Engine & Storage Provisioning Manager:
Implement customizable timeout policies in backend/src/apiserver/server/run_server.go and backend/src/agent/persistence:
- PVC Storage Provisioning Differentiator: Distinguish between deterministic storage errors vs. transient volume attachment:
  * Deterministic PVC Failures (Invalid StorageClass / Quota Breach): Inspect PVC events for `ProvisioningFailed` or `storageclass.storage.k8s.io not found`. Since an invalid `storageClassName` will never recover, trigger an immediate fast-fail timeout (e.g., 60 seconds) with explicit diagnostic advice ("Verify available cluster StorageClasses via 'kubectl get sc'").
  * Transient Volume Binding (WaitForFirstConsumer / Cloud CSI Attachment): For normal volume binding delays (e.g. cloud EBS/GCP PD disk creation), set a generous 10-15 minute grace period while displaying an Amber provisioning status badge in the UI.
- CrashLoopBackOff Fast-Fail Threshold: When a pod enters CrashLoopBackOff due to startup crashes (e.g. invalid syntax/imports), Kubernetes applies exponential backoffs (up to 5 min per retry). Rather than waiting passively for hours, persistence-agent / API Server evaluates `containerStatuses[*].state.waiting.reason == "CrashLoopBackOff"` alongside `restartCount`. If `restartCount >= 3` or `CRASH_LOOP_TIMEOUT` (e.g., 3 minutes) is reached, trigger an active fail-fast termination, marking the task as FAILED with diagnostic feedback ("Inspect container entrypoint command and application logs").
- Deterministic Image/Syntax Errors: Trigger fail-fast timeout (e.g., 2 minutes) instead of waiting for default execution timeout (hours).
- Transient Infrastructure Evictions: Apply exponential backoff grace periods for node re-scheduling.

5.3 Protobuf & OpenAPI Schema Extension
Modify `backend/api/v2beta1/run.proto` and `report.proto` to introduce a streamlined `PodLifecycleDiagnostics` message in `PipelineTaskDetail`:

```protobuf
message PodLifecycleDiagnostics {
  // Structured diagnostic error code (e.g., "IMAGE_PULL_BACKOFF", "OOM_KILLED", "UNSCHEDULABLE", "CRASH_LOOP_BACKOFF", "EVICTED")
  string error_code = 1;

  // Detailed K8s pod event message or container termination reason
  string error_message = 2;
}
```

Regenerate backend Go code and frontend OpenAPI clients:
- `make -C api golang`
- `npm run apis:all`

5.4 Frontend Visual Console Upgrade (React 19 / MUI)
The frontend console (frontend/src/pages/RunDetails.tsx and DAG components) will be updated with intuitive visual indicators:
Color-Coded DAG Node Status Badges:
🟧 Amber Badge (PROVISIONING_FAILED / SCHEDULING_FAILED): Displayed when pod is stuck pulling images or pending node allocation.
🟥 Dark Red Badge (RUNTIME_CRASHED / OOMKilled): Displayed when container crashes due to OOM or runtime panic.
🟪 Purple Badge (NODE_EVICTED): Displayed when underlying node was preempted or lost.
Alert Banner:
Render a visibility alert banner above the log viewer tab: Sample - 


Educational Tooltips:
Hovering over a failed or pending DAG node triggers a tooltip summarizing the failure reason and providing a direct link to troubleshooting documentation.
Translates low-level infrastructure codes into high-level ML domain concepts directly inside the React 19 / MUI DAG console, providing actionable recommendations without requiring kubectl CLI access. 




6. Testing Strategy
Following the repository's testing policy (AGENTS.md), all code changes will be tested locally before submission.



Go Unit & Integration Tests:
Write unit tests for WorkflowSaver in backend/src/agent/persistence/worker/workflow_saver_test.go.
Run Ginkgo compiler and API integration tests:



Frontend Vitest UI Testing:
Add unit and snapshot tests for visual status badges and diagnostic banners in frontend/src.
Run full frontend test suite:


End-to-End Cluster Testing:
Spin up a local Kind development cluster using:

make -C backend kind-cluster-agnostic

Deploy sample pipelines designed to trigger ImagePullBackOff, Unschedulable, and OOMKilled states, verifying end-to-end diagnostic propagation to the UI.






7. 12-Week Implementation Timeline
Week 1 – 2: Go Backend Event Collector
Add pod event/condition parsing to KFP Persistence Agent (backend/src/agent/persistence).
Implement classification logic for ImagePullBackOff, Unschedulable, OOMKilled, and Preempted.
Add unit tests for event classification utilities.
Week 3 – 4: Log Pipeline Repair & Backend Persistence
Fix Argo Workflow log dropping bug in WorkflowSaver.go and ReportWorkflow.
Persist pod failure status messages into native KFP MySQL database tables (PipelineTaskDetail).
Run Go unit tests and Ginkgo API test suites.
Week 5 – 6: Protobuf API & Client Generation
Define PodLifecycleDiagnostics in api/v2beta1/pipeline_spec.proto and report.proto.
Generate Go, Python, and TypeScript OpenAPI clients (make -C api golang, npm run apis:all).
Update API server handler endpoints to return diagnostic payload.
Week 7 – 8: Frontend Visual DAG Console
Add color-coded lifecycle status badges (Amber, Red, Purple) to DAG nodes in React UI.
Create a reusable PodDiagnosticBanner component in MUI v5.
Write Vitest unit tests for visual UI components.
Week 9 – 10: Educational Tooltips & Custom Timeout Manager
Implement educational hover tooltips with troubleshooting documentation links.
Build per-error custom timeout engine in API server (fast-fail for bad images/scheduling).
Verify timeout policies on local Kind clusters.
Week 11 – 12: Documentation, Interactive Demo & Polish
Author comprehensive documentation for KFP repo and Kubeflow website.
Create an interactive web demo showing live pod lifecycle diagnostic handling.
Perform final code cleanup, verify all lint/test checks pass, and submit upstream PRs.


Long-Term Impact

By abstracting Kubernetes pod lifecycle failures natively inside Kubeflow Pipelines, this project eliminates major technical friction for data scientists and ML engineers. It reinforces KFP's core value proposition: providing a seamless, production-ready machine learning platform where infrastructure complexity is hidden behind intuitive visual abstractions.



