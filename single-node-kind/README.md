# Single Node Kind

Let's use fractale to run build, execute, and deploy agents. For this first test, we want to run 10 independent experiments, saving results as we go and timing the steps to Docker build. We will use a manager with a plan and no cache. We will only ask for one node. 

## LAMMPS

Here is how to run one experiment, 10 independent iterations, saving a result to ./results, and incremental to get output for each step and the final log.

```bash
outdir=./results/lammps
mkdir -p $outdir
for i in seq(1 10)
  do
  fractale agent --plan ./plans/lammps.yaml --results $outdir --incremental
done
```

## AMG2023

```bash
outdir=./results/amg2023
mkdir -p $outdir
for i in seq(1 10)
  do
  fractale agent --plan ./plans/amg2023.yaml --results $outdir --incremental
done
```

