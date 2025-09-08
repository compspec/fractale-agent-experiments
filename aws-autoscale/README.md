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

## 3. Kripke

```bash
outdir=./results/kripke-2
mkdir -p $outdir
for i in $(seq 1 10)
  do
  fractale agent --plan ./plans/kripke.yaml --results $outdir --incremental
done
```

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
