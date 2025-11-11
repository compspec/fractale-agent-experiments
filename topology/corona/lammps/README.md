# GPU Topology

Testing on corona (AMD). I'll have to find something to run. Update - built lammps.

 - [Gromacs](GROMACS.md)

```bash
conda deactivate
module load rocm

# Now, run the command with the corrected case for all Kokkos variables
cmake \
  -D CMAKE_INSTALL_PREFIX=../install \
  -D CMAKE_CXX_COMPILER=hipcc \
  -D BUILD_MPI=yes \
  -D PKG_KOKKOS=on \
  -D Kokkos_ENABLE_HIP=on \
  -D Kokkos_ARCH_GFX9006=on \
  -D PKG_KSPACE=on \
  -D PKG_REAXFF=on \
  -D PKG_MOLECULE=on \
  -D PKG_RIGID=on \
  -D Kokkos_ENABLE_OPENMP=on -D OpenMP_REQUIRED=on -D PKG_MANYBODY=on ../cmake
```

Shapes we care about:

- generate xml or canonical jobspec from 
- need to be able to take xml to canonical jobspec
- 1 core per L3 cache
- 2 tasks per core (by PU)
- 

- Create single node canonical jobspec with L3, L2, l1, core
- Include GPUs and have some metric of distance 
-  could be hop vertex, or a distance
-  would expect GPU to be children of NUMA noda
-  numa node -> GPU, GPU and L3 cache are siblings. Which L3 caches closest to which GPUs.
-  what does a distance mean? need to understand units.
- use an edge weight between l3 and gpu to graph.

Use RajaPerf kernels to test topology (which are cache bound, which are boundedness)
- If kernel is cache bound, depends on where the process is bound to cache. If don't do that, performance will take a hit.
- Take cache bounded app / kernel and try different mapping techniques.
- MuMMI with GPU matters.

https://www.reddit.com/r/devops/comments/1o2dfdh/devops_in_hpc_how_does_it_look_like_what_tools/ 
https://www.boredpanda.com/yup-that-exists-pics-msn/
- I don't think a dragon can explode. But a dino mite.
 
 - https://www.merriam-webster.com/dictionary/kibosh
 - https://www.merriam-webster.com/wordplay/beautiful-useless-obscure-words-volume-3
 - cowboy == american horse pirate
 - hope get to work with you

Well known that being specific will change outcome of perfomance, flux devs know this, but flux devs haven't implemented it yet.
The research comes in (the unknown part) is if we have an application not like raja perf kernel,
where you don't know boundedness behaviors, it can accept a lot of different configurations with minimal performance pentalyy. We would want an interplay between the shapes it can accept, and those that are available. Not what is representable, but what is available at a particular time.

What I'm investigating now in binding is well studied for HPC, but not something that flux supports well, and not something that users understnd well.

```bash
flux alloc -N 1 --time 8h
git clone -b add-gpu-support https://github.com/converged-computing/fluxbind
cd fluxbind
python3 -m pip install -e .
```

That works.

```bash
fluxbind run -N 1 --gpus-per-task 8 --shape ./examples/shape/google/n1-standard-8/shape_gpu_local_numa.yaml rocm-smi
cd /p/vast1/fractale/descriptive-thrust/caliper/lammps/examples/reaxff/HNS
```

## Experiments

```bash
mkdir -p results
```

Dumb Money - story of Gamestop.


### Unbound (no binding)

I tested this with and without exclusive - same result. This was the largest size before I got a memory error.

```bash
mkdir -p ./results/no-binding
for iter in $(seq 1 10)
  do
  flux run -N 1 -n 8 -g 1 --cores-per-task=6  /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1    -sf kk -pk kokkos newton on neigh half  -in in.reaxff.hns     -v x 32 -v y 16 -v z 16 |& tee ./results/no-binding/$iter.out
done
```
- Verified all GPUS being used

Testing

```
# 6 seconds 3.777 Matom-step/s
flux run -N 1 -n 8 -g 1 --cores-per-task=6  /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1    -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8

# 5 seconds 3.909 Matom-step/s
flux run -N 1 -n 8 -g 1 --cores-per-task=6 -o cpu-affinity=per-task  /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1    -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8

# 5 seconds 3.866 Matom-step/s
flux run -N 1 -n 8 -g 1 --cores-per-task=6 -o gpu-affinity=per-task  /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1    -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8

# 5 seconds, 3.872 Matom-step/s
flux run -N 1 -n 8 -g 1 --cores-per-task=6 -o gpu-affinity=per-task -o cpu-affinity=per-task /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1    -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8
```

## Shape (core) GPU Local

```bash
mkdir -p ./results/shape-core-gpu-local
for iter in $(seq 1 10)
  do
  fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-core-gpu-local.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 16 -v y 16 -v z 16 |& tee ./results/shape-core-gpu-local/$iter.out
done
```
```bash
fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-core-gpu-local.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8
```

## Shape (core) GPU Local

```bash
mkdir -p ./results/shape-core-gpu-remote
for iter in $(seq 1 10)
  do
  fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-core-gpu-remote.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 t 2 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 16 -v y 16 -v z 16 |& tee ./results/shape-core-gpu-remote/$iter.out
done
```

## Shape l2cache GPU local

```bash
# 
mkdir -p ./results/shape-l2cache-gpu-local
for iter in $(seq 1 10)
  do
  fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-l2cache-gpu-local.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 16 -v y 16 -v z 16 |& tee ./results/shape-l2cache-gpu-local/$iter.out
done
```

```bash
fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-l2cache-gpu-local.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8

```

## Shape l2cache GPU remote

```bash
mkdir -p ./results/shape-l2cache-gpu-remote
for iter in $(seq 1 10)
  do
  fluxbind run -N 1 -n 8 -g 1 --cores-per-task=2 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-l2cache-gpu-remote.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 16 -v y 16 -v z 16 |& tee ./results/shape-l2cache-gpu-remote/$iter.out
done
```
## Shape l3cache GPU local


```bash
mkdir -p ./results/shape-l3cache-gpu-local
for iter in $(seq 1 10)
  do
  fluxbind run -N 1 -n 8 -g 1 --cores-per-task=3 --shape /g/g0/sochat1/fluxbind/examples/shape/corona/shape-l3cache-gpu-local.yaml /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 16 -v y 16 -v z 16 |& tee ./results/shape-l3cache-gpu-local/$iter.out
done
```

# This is fast - 16 seconds (l2cache)
fluxbind run -N 1 -n 8 --gpus-per-task=1 --cores-per-task=2    --shape shape-l2cache.yaml    /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp     -k on g 1     -sf kk     -pk kokkos newton on neigh half     -in in.reaxff.hns     -v x 8 -v y 8 -v z 8

# This is slower has to cross caches
flux run -N 1 --exclusive --env GPUS_PER_TASK=4 --env JOB_SHAPE_FILE=shape-numa.yaml -o cpu-affinity=off -o gpu-affinity=off -n 2 --cores-per-task 24 /usr/bin/bash /g/g0/sochat1/fluxbind/fluxbind/scripts/run_mapping.sh /p/vast1/fractale/descriptive-thrust/caliper/lammps/build/lmp -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8
```

Let's try with lammps

```bash
flux run -N1 -n 1 --gpus-per-task 8 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 8 -v y 8 -v z 8 -in in.reaxff.hns -nocite
```

```bash
for i in $(seq 0 4); do
    echo "Running Packed Cores - Iteration $i..."
    fluxbind run -N 4 -n 192 --exclusive --nocolor \
        --shape /fluxbind/examples/shape/google/c4-standard-96/shape_packed_cores-shapefile.yaml \
        kripke --procs 8,4,6 --zones 128,128,96 --niter 50 |& tee results/192ranks_packed-cores/${i}.out
done
```

### NCCL Tests

Needs test with flux-gpu container

```bash
helm dependency update nccl-tests/
helm install \
  --set experiment.nodes=4 \
  --set minicluster.gpus=1 \
  --set minicluster.size=4 \
  --set minicluster.tasks=4 \
  --set experiment.tasks=4 \
  --set experiment.iterations=5 \
  --set minicluster.save_logs=true \
  --set nccl.begin=8 \
  --set nccl.end=1G \
  --set nccl.f=2 \
  --set nccl.g=1 \
  nccl ./nccl-tests

time kubectl wait --for=condition=ready pod -l job-name=nccl --timeout=600s
pod=$(kubectl get pods -o json | jq  -r .items[0].metadata.name)
kubectl logs ${pod} -f |& tee ./logs/nccl-tests.out
helm uninstall nccl
```

## Clean Up

When you are done:

```bash
gcloud container clusters delete test-cluster --region=us-central1-a
```
