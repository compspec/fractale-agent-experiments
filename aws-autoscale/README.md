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
  fractale agent --plan ./plans/amg2023.yaml --results $outdir --incremental
done
```

And with testing providing a function:

```bash
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/amg2023-function.yaml --results $outdir --incremental
done
```


## 3. Kripke

```bash
outdir=./results/kripke-1
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/kripke.yaml --results $outdir --incremental
done
```

which nodes are less likely to not have jobs - start subgraph or subtree and start traversing much lower based on likelihood of subtree having availability. You could parallelize the graph traversals.


## 4. LAMMPS

```bash
outdir=./results/lammps-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/lammps.yaml --results $outdir --incremental
done
```

## 5. Laghos

```bash
outdir=./results/laghos-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/laghos.yaml --results $outdir --incremental
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

```bash
eksctl create cluster --config-file ./eks-config-4-nodes.yaml 

aws eks update-kubeconfig --region us-east-1 --name efa-cluster
sleep 5
kubectl apply -f eks-efa-autoscaler.yaml
sleep 5
kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/refs/heads/main/examples/dist/flux-operator.yaml

```

## 1. AMG2023

```bash
outdir=./results/amg2023-4-nodes
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/amg2023-4-nodes.yaml --results $outdir --incremental
done
```

When you are done:

```bash
eksctl delete cluster --config-file ./eks-config-4-nodes.yaml  --wait
```

