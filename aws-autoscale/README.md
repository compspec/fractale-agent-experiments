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
eksctl delete cluster --config-file ./eks-config.yaml  --wait
```

## Cluster Experiments

Let's allow for creation up to 4 nodes. Command to get efa instances:

```
aws ec2 describe-instance-types --region us-east-1 --filters Name=network-info.efa-supported,Values=true --query "InstanceTypes[*].[InstanceType]" --output text  | sort
```

I chose the top performing instance. The reason is because the autoscaler uses them as templates, so we need one to exist. This time we need to install the EFA device plugin. I didn't see eksctl did it.

```bash
eksctl create cluster --config-file ./eks-config-4-nodes.yaml 

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
eksctl create cluster --config-file ./eks-config-5-nodes.yaml 
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

