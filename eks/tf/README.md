# ekslab — standard EKS cluster (eu-west-2, itcdevops)

Terraform for a **standard** (non-Auto-Mode) EKS cluster with a t2.medium
managed node group, matching the `dev-euw2-vpc` layout.

## Why these specific choices
- **Not Auto Mode**: the `itcdevops` account is under an Org SCP (`p-yz1hiqdn`)
  that denies `ec2:RunInstances` for everything except `t2.nano/micro/small/medium`.
  EKS Auto Mode only launches Nitro-generation instances, all SCP-denied, so it
  can never create a node here. This config is a standard cluster instead.
- **`t2.medium`, x86 AMI**: t2.medium is the largest SCP-allowed type; t2 is
  x86-only, hence `AL2023_x86_64_STANDARD`. Do not switch to t3/Graviton — denied.
- **Public subnets + auto-assign public IP**: gives nodes outbound egress via the
  IGW so the VPC CNI can pull from ECR. Node-to-control-plane traffic stays
  internal via the private endpoint. (For a private/prod design, swap to private
  subnets + a NAT gateway, or VPC endpoints for ecr/ec2/sts/s3.)

## Usage
```bash
cd /home/danish/workshop4/ekslab
terraform init
terraform plan
terraform apply

# then:
aws eks update-kubeconfig --name dev-euw2-eks-01 --region eu-west-2 --profile itcdevops
kubectl get nodes -o wide   # expect 2 nodes -> Ready
```

## Scope
This is a self-contained, from-scratch build — it creates its own VPC, subnets,
IGW, route table, **cluster IAM role, and node IAM role**, so it can be applied in
any account with no pre-existing EKS resources. It does not reference or import the
manually-built `dev-euw2-eks-01`; running `apply` provisions a fresh, independent
stack. Override `cluster_name`, `region`, CIDRs, etc. via variables per account.

The node role is created here with the full standard policy set
(`AmazonEKSWorkerNodePolicy` + `AmazonEKS_CNI_Policy` +
`AmazonEC2ContainerRegistryReadOnly`) — this is what lets worker nodes bootstrap
and join. (Reusing an Auto Mode "minimal" node role is what previously blocked
nodes from joining.)

Remember the instance-type constraint only applies where an SCP enforces it — in an
account without that SCP you can raise `node_instance_type` to a t3/m-series size.
