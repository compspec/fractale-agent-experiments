# LAMMPS Experiment

Let's use fractale to run build, execute, and deploy agents. For this first test, we want to run 10 independent experiments, saving results as we go and timing the steps to Docker build. We will use a manager with a plan and no cache.

## Manager

Here is how to run one experiment, saving a result to ./results.

```bash
fractale agent --plan ./plans/run-lammps.yaml --results ./results
```
