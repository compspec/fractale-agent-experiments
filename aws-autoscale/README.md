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

import base64
original_string = "You are the only exception."
string_bytes = original_string.encode('utf-8')
encoded_bytes = base64.b64encode(string_bytes)
encoded_string = encoded_bytes.decode('utf-8')
print(encoded_string)
pip download --only-binary :all: --python-version 3.9 --abi cp39 --platform linux_x86_64 my_package
print(f"Original string: {original_string}")
print(f"Base64 encoded string: {encoded_string}")

## 2. AMG2023

```bash
outdir=./results/amg2023
mkdir -p $outdir
for i in seq(1 10)
  do
  fractale agent --plan ./plans/amg2023.yaml --results $outdir --incremental
done
```

When you are done:

```bash
eksctl delete cluster --config-file ./eks-config.yaml  --wait
```
