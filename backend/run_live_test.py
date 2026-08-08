import time
import kfp
from kfp import dsl, compiler

@dsl.component
def hello_world(name: str) -> str:
    message = f"Hello, {name}!"
    print(message)
    return message

@dsl.pipeline(name="hello-cached-pipeline-issue10729")
def hello_pipeline(recipient: str = "Kubeflow"):
    task = hello_world(name=recipient)
    task.set_caching_options(True)

def main():
    print("Compiling pipeline...")
    pipeline_yaml = "hello_cached_pipeline.yaml"
    compiler.Compiler().compile(hello_pipeline, pipeline_yaml)

    client = kfp.Client(host='http://localhost:8888')
    # Set multi-user auth header across all underlying API clients
    for api_attr in ['_experiment_api', '_pipelines_api', '_run_api', '_upload_api', '_recurring_run_api']:
        api_obj = getattr(client, api_attr, None)
        if api_obj and hasattr(api_obj, 'api_client'):
            api_obj.api_client.default_headers['kubeflow-userid'] = 'user@example.com'

    print("Submitting Run #1 (populating cache)...")
    run_1 = client.create_run_from_pipeline_package(
        pipeline_file=pipeline_yaml,
        arguments={"recipient": "Issue10729Tester"},
        experiment_name="issue-10729-live-demo",
        namespace="user"
    )
    print(f"Run #1 created with ID: {run_1.run_id}")
    
    # Wait for Run 1
    print("Waiting for Run #1 to complete...")
    client.wait_for_run_completion(run_1.run_id, timeout=300)
    print("Run #1 completed!")

    print("\nSubmitting Run #2 (triggering cache hit)...")
    run_2 = client.create_run_from_pipeline_package(
        pipeline_file=pipeline_yaml,
        arguments={"recipient": "Issue10729Tester"},
        experiment_name="issue-10729-live-demo",
        namespace="user"
    )
    print(f"Run #2 created with ID: {run_2.run_id}")
    
    print("Waiting for Run #2 to process cached step...")
    # Wait a bit for pods to be spawned and finish
    time.sleep(15)
    client.wait_for_run_completion(run_2.run_id, timeout=300)
    print("Run #2 completed!")
    print(f"Run #2 ID: {run_2.run_id}")

if __name__ == "__main__":
    main()


## agy esume 0d115301-ad42-430c-88da-bb55514f7174