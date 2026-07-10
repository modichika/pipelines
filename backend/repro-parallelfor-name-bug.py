import kfp
# Inject a dummy version to satisfy the component factory builder
kfp.__version__ = "2.14.3"
kfp.TYPE_CHECK = True


from kfp import compiler, dsl

@dsl.component
def echo(item: str) -> str:
    return item

@dsl.component
def collect(items: list) -> str:
    return str(items)

@dsl.pipeline(name="repro-parallelfor-name-bug")
def my_pipeline():
    with dsl.ParallelFor(items=["a", "b", "c"], name="My Custom Loop") as item:
        work = echo(item=item)
    collect(items=dsl.Collected(work.output))

compiler.Compiler().compile(my_pipeline, "pipeline.yaml")
print("Compilation Successful!")