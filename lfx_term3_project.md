[CNCF LFX Proposal] Kubeflow Pipelines: Abstracting Pod Lifecycle Diagnostics

CNCF Project
Kubeflow

Term
2026 Term 3 (Sep-Nov)

Program Name
Abstracting Pod Lifecycle Diagnostics for Kubeflow Pipelines

Program Description
Background
Kubeflow Pipelines (KFP) is an orchestrator for containerized ML workloads. Featuring a Python SDK as well as a UI that visualizes pipeline run workloads as directed acyclic graphs, KFP is designed to be a Kubernetes abstraction for ML engineers and data scientists scaling their containerized training and experimentation workflows.

But this abstraction breaks when a Kubernetes pod hits lifecycle failure. These failures can occur at the provisioning level (e.g., ImagePullBackOff or Unschedulable), runtime level (e.g., CrashLoopBackOff or OOMKilled), or node level (e.g., NodeLost or Preempted). On failure, the KFP UI displays a pipeline frozen at the current pod – not succeeding, progressing, or failing.

The KFP console provides visual support for pod failures that result from errors in user-supplied pipeline code. But this support does not extend to the pod lifecycle failures defined above, forcing a user to debug with the Kubernetes CLI. Additionally, even after a user has retrieved pod status, they also require an advanced understanding of Kubernetes pod events and infrastructure. While AI tooling can ease the burden of Kubernetes debugging, it should not be a prerequisite for the project’s target users. This proposal aims to reduce technical friction in KFP by abstracting away low-level Kubernetes details for ML engineers and data scientists.

Qualifications
A successful applicant for this project is proficient in Go and Typescript and has practical experience with Kubernetes and pod debugging. Experience with Kubeflow is preferred.

Project Deliverables
This project introduces a new abstraction layer to visualize and manage Kubernetes pod lifecycle failures directly within the KFP UI. Spanning the entire KFP stack, the implementation is divided into three core phases:

UI-level Diagnostic Support: An upgraded visual console featuring color-coded pod lifecycle statuses, inline failure messages, and educational hover tooltips linked to documentation.
API Server-level Pod Failure Management: A more robust API layer capable of handling per-error custom timeouts and a repaired data pipeline that prevents Argo Workflow failure logs from being dropped.
Enablement & Docs: Complete feature documentation (within the KFP repository and the Kubeflow website) alongside an interactive website demo.
Technologies
Kubernetes (including kubectl CLI), Go, Typescript

Skills same as Technologies?

Yes, the required skills are the same as the technologies listed above.
Required/Desirable Skills
No response

Mentors
Alyssa Goins | @alyssacgoins | agoins@redhat.com | alyssacgoins
Matt Prahl | @mprahl | mprahl@redhat.com | mprahl

Upstream Issue URL
kubeflow/pipelines#12843

Application Prerequisites

Resume

Cover Letter

School Enrollment Verification

Participation Permission from school or employer

Coding Challenge

Project Proposal
Project Proposal
Please submit a 1-2 page proposal outlining your approach to the project deliverables included above.

Custom Prerequisite — File Upload

Yes — completion of this task requires the mentee to submit a file.