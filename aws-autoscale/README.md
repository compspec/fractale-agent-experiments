# AWS Autoscaling

Let's now give the agent the choice to optimize, telling it that it has a much better selection of instance types.

## 1. Create Cluster

```bash
eksctl create cluster --config-file ./eks-config.yaml 
aws eks update-kubeconfig --region us-east-1 --name nfd-cluster
```

Install the autoscaler:

```bash
kubectl apply -f eks-autoscaler.yaml
```

Install the flux operator:

```bash
kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/refs/heads/main/examples/dist/flux-operator.yaml
```

## 2. AMG2023

```bash
outdir=./results/amg2023-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/single-node/amg2023.yaml --results $outdir --incremental
done
```

Note that the user function script was turned into the user guided function script, and the original plan for that is saved with results.

## 3. Kripke

```bash
outdir=./results/kripke-1
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/single-node/kripke.yaml --results $outdir --incremental
done
```

which nodes are less likely to not have jobs - start subgraph or subtree and start traversing much lower based on likelihood of subtree having availability. You could parallelize the graph traversals.


## 4. LAMMPS

```bash
outdir=./results/lammps-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/single-node/lammps.yaml --results $outdir --incremental
done
```

## 5. Laghos

```bash
outdir=./results/laghos-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/single-node/laghos.yaml --results $outdir --incremental
done
```

When you are done:

```bash
eksctl delete cluster --config-file ./eksctl/eks-config.yaml  --wait
```

## Cluster Experiments

Let's allow for creation up to 4 nodes. Command to get efa instances:

```
aws ec2 describe-instance-types --region us-east-1 --filters Name=network-info.efa-supported,Values=true --query "InstanceTypes[*].[InstanceType]" --output text  | sort
```

I chose the top performing instance. The reason is because the autoscaler uses them as templates, so we need one to exist. This time we need to install the EFA device plugin. I didn't see eksctl did it.

```bash
eksctl create cluster --config-file ./eksctl/eks-config-4-nodes.yaml 

aws eks update-kubeconfig --region us-east-1 --name efa-cluster

helm repo add eks https://aws.github.io/eks-charts
helm install efa eks/aws-efa-k8s-device-plugin -n kube-system

kubectl apply -f eks-efa-autoscaler.yaml
kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/refs/heads/main/examples/dist/flux-operator-arm.yaml
```

Build the base image:

```
fractale agent --plan ./plans/base-build.yaml --results ./results/base-build --incremental
```

## 1. AMG2023

```bash
outdir=./results/amg2023-4-nodes
mkdir -p $outdir-build
mkdir -p $outdir-deploy
for i in $(seq 1 3)
  do
  fractale agent --plan ./plans/multi-node/amg2023-4-nodes-build.yaml --results $outdir-build --incremental
  fractale agent --plan ./plans/multi-node/amg2023-4-nodes-deploy.yaml --results $outdir-deploy --incremental
done
```

## 2. LAMMPS

```bash
outdir=./results/lammps-4-nodes
mkdir -p $outdir
for i in $(seq 1 4)
  do
  fractale agent --plan ./plans/multi-node/lammps-4-nodes.yaml --results $outdir --incremental
incremental
done
```

## 3. Kripke

```bash
outdir=./results/kripke-4-nodes
mkdir -p $outdir
for i in $(seq 1 4)
  do
  fractale agent --plan ./plans/multi-node/kripke.yaml --results $outdir --incremental
incremental
done
```

## 4. OSU

```bash
outdir=./results/osu-allreduce
mkdir -p $outdir
for i in $(seq 1 4)
  do
  fractale agent --plan ./plans/multi-node/osu-allreduce.yaml --results $outdir --incremental
done

outdir=./results/osu-latency
mkdir -p $outdir
for i in $(seq 1 4)
  do
  fractale agent --plan ./plans/multi-node/osu-latency.yaml --results $outdir --incremental
done
```


When you are done:

```bash
eksctl delete cluster --config-file ./eks-config-4-nodes.yaml  --wait
```


## Scaling Experiments

We are going to choose the most cost effective type, hpc7g.

```bash
eksctl create cluster --config-file ./eksctl/eks-config-5-nodes.yaml 
aws eks update-kubeconfig --region us-east-1 --name efa-cluster

helm repo add eks https://aws.github.io/eks-charts
helm install efa eks/aws-efa-k8s-device-plugin -n kube-system

kubectl apply -f eks-efa-autoscaler.yaml
kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/refs/heads/main/examples/dist/flux-operator-arm.yaml
```

### LAMMPS

```bash
outdir=./results/lammps-scaling-5-nodes-hpc7g
mkdir -p $outdir
fractale agent --plan ./plans/scaling-study/scale-lammps.yaml --results $outdir --incremental
```

### AMG2023

```bash
outdir=./results/amg-scaling-5-nodes-hpc7g
mkdir -p $outdir
fractale agent --plan ./plans/scaling-study/scale-amg2023.yaml --results $outdir --incremental
```

### Kripke

```bash
outdir=./results/kripke-scaling-5-nodes-hpc7g
mkdir -p $outdir
fractale agent --plan ./plans/scaling-study/scale-kripke.yaml --results $outdir --incremental
```

```bash
python plot_strategies.py 
```
```console
app        strategy                      runs          mean           std          best
----------------------------------------------------------------------------------------
amg2013    llm decision                    10   7.96297e+08   8.39396e+08   1.60489e+09
amg2013    llm decision (multi-node)        3    4.0525e+09   3.50288e+09   6.13248e+09
amg2013    user guided function             8    3.5526e+08   5.74021e+08   1.41708e+09
amg2013    user provided function           8   1.87753e+07    3.4875e+07   8.04864e+07

kripke     llm decision                     8   1.67036e-08   3.12912e-08   7.33812e-10
kripke     llm decision (multi-node)        4   2.01309e-08   2.21968e-08   7.79529e-10
kripke     user guided function             8   5.48985e-08   3.42945e-08   2.09771e-08

lammps     llm decision                    10      0.611914      0.241672      0.724238
lammps     llm decision (multi-node)       12       1.30983      0.815326           2.5
lammps     user guided function            10     0.0538191      0.106395      0.355524
lammps     user provided function          10       0.17211      0.293298       0.72655

laghos     llm decision                    10       192.642       107.752       352.954
laghos     user guided function             9       37.7111       49.1123       134.342

wrote data/img/strategy_comparison.svg
wrote data/img/strategy_comparison.png
```
