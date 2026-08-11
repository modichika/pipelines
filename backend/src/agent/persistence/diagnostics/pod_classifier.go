// Copyright 2026 The Kubeflow Authors
//
// Licensed under the Apache License, Version 2.0 (the "License")
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/Licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific Language governing permissions and
// Limitations under the License.

package diagnostics

import (
	"fmt"
	"strings"

	v1 "k8s.io/api/core/v1"
)

type DiagnosticCategory string

const (
	CategoryUnspecified DiagnosticCategory = "DIAGNOSTIC_CATEGORY_UNSPECIFIED"
	CategoryProvisioningFailure DiagnosticCategory = "PROVISIONING_FAILURE"
	CategorySchedulingFailure DiagnosticCategory = "SCHEDULING_FAILURE"
	CategoryRuntimeCrash DiagnosticCategory = "RUNTIME_CRASH"
	CategoryNodeEviction DiagnosticCategory = "NODE_EVICTION"
)

type PodLifecycleDiagnostics struct {
	Category   DiagnosticCategory  `json:"category"`
	ReasonCode  string             `json:"reason_code"`
	RawExitCode  int32			 `json:"raw_exit_code"`
	HumanExplanation  string 		   `json:"human_explanation"`
	RemediationRecommendation  string 	   `json:"remediation_recommendation"`
	DocumentationURL    string 		   `json:"documentation_url"`
}


const (
	DefaultDocsURL = "https://www.kubeflow.org/docs/components/pipelines/v2/troubleshooting"
)

// ClassifyPodStatus inspects a Kubernetes v1.PodStatus and returns a structured PodLifecycleDiagnostics pointer.
// If no Lifecycle failure is detected, it returns nil.

func ClassifyPodStatus(podStatus *v1.PodStatus) *PodLifecycleDiagnostics {
	if podStatus == nil {
		return nil
	}

	// 1. Check Pod Eviction / Node Preemption
	if strings.EqualFold(podStatus.Reason, "Evicted") || strings.EqualFold(podStatus.Reason, "Preempted") {
		return &PodLifecycleDiagnostics{
			Category: CategoryNodeEviction,
			ReasonCode: podStatus.Reason,
			RawExitCode: -1,
			HumanExplanation: fmt.Sprintf("The pod was evicted or preempted from node: %s", podStatus.Message),
			RemediationRecommendation: "Retry execution or request non-preemptible node instances.",
			DocumentationURL: DefaultDocsURL + "#node-eviction",
		}
	}

	// 2. Check Container Level Statuses (Waiting or Terminated)
	containerStatuses := append(podStatus.InitContainerStatuses, podStatus.ContainerStatuses...)
	for _, cs := range containerStatuses {
		if cs.State.Waiting != nil {
			reason := cs.State.Waiting.Reason
			switch reason {
				case "ImagePullBackOff", "ErrImagePull":
					return &PodLifecycleDiagnostics{
						Category: CategoryProvisioningFailure,
						ReasonCode: reason,
						RawExitCode: -1,
						HumanExplanation: fmt.Sprintf("Container image '%s' could not be pulled: %s", cs.Image, cs.State.Waiting.Message),
						RemediationRecommendation: "Verify image name, tag, and imagePullSecrets credentials.",
						DocumentationURL: DefaultDocsURL + "#imagepullbackoff",
					}
				case "InvalidImageName":
					return &PodLifecycleDiagnostics{
						Category: CategoryProvisioningFailure,
						ReasonCode: reason,
						RawExitCode: -1,
						HumanExplanation: fmt.Sprintf("Invalid container image format specified %s", cs.Image),
						RemediationRecommendation: "Check image string formatting in component definition.",
						DocumentationURL: DefaultDocsURL + "#invalidimagename",

			}
			    case "CrashLoopBackOff":
					return &PodLifecycleDiagnostics{
						Category: CategoryRuntimeCrash,
						ReasonCode: reason,
						RawExitCode: -1,
						HumanExplanation: "Container failed repeatedly immediately after starting",
						RemediationRecommendation: "Inspect component entrypoint command and application logs.",
						DocumentationURL: DefaultDocsURL + "#crashloopbackoff",
		}
	}


}

        if cs.State.Terminated != nil {
			term := cs.State.Terminated
			if term.Reason == "OOMKilled" || term.ExitCode == 137 {
                return &PodLifecycleDiagnostics{
					Category: CategoryRuntimeCrash,
					ReasonCode: "OOMKilled",
					RawExitCode: term.ExitCode,
					HumanExplanation: fmt.Sprintf("Container Killed: exceeded aloocated memory limit (exit code %d).", term.ExitCode),
					RemediationRecommendation: "Increase container memory limit using SDK .set_memory_limit() method.",
					DocumentationURL: DefaultDocsURL + "#oomkilled",
				}
			}
			
			if term.ExitCode != 0 {
				return &PodLifecycleDiagnostics{
					Category: CategoryRuntimeCrash,
					ReasonCode: term.Reason,
					RawExitCode: term.ExitCode,
					HumanExplanation: fmt.Sprintf("Container exited with non-zero status code %d. Reason: %s", term.ExitCode, term.Message),
					RemediationRecommendation: "Review task execution logs for application-level runtime errors.",
					DocumentationURL: DefaultDocsURL + "#runtime-error",

			}
		}

	}

}
  // 3. Check Pod Level Conditions (Scheduling Failures)
  for _, condition := range podStatus.Conditions {
        if condition.Type == v1.PodScheduled && condition.Status == v1.ConditionFalse {
			if condition.Reason == v1.PodReasonUnschedulable || strings.Contains(condition.Message, "insufficient") {
				return &PodLifecycleDiagnostics{
					Category: CategorySchedulingFailure,
					ReasonCode: "Unschedulable",
					RawExitCode: -1,
					HumanExplanation: fmt.Sprintf("Pod could not be scheduled on cluster nodes: %s", condition.Message),
					RemediationRecommendation: "Verify cluster CPU/GPU capacity or lower task resource requests.",
					DocumentationURL: DefaultDocsURL + "#unschedulable",
				}
			}
		}
  }

  return nil
}