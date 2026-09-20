# ---------------------------------------------------------------------------
# IAM roles for the EKS control plane and the worker nodes
# ---------------------------------------------------------------------------

# ----- Cluster role -----
data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "eks-cluster-${var.cluster_name}"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# ----- Node role -----
# A dedicated worker-node role with the three policies a STANDARD managed node
# group requires. AmazonEKSWorkerNodePolicy grants ec2:DescribeInstances (needed
# by nodeadm to bootstrap), AmazonEKS_CNI_Policy lets the VPC CNI manage ENIs/IPs,
# and the ECR read policy allows image pulls. Using a proper node role here (not
# a reused Auto Mode "minimal" role) is what keeps nodes able to join.
data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "eks-node-${var.cluster_name}"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
  ])

  role       = aws_iam_role.node.name
  policy_arn = each.value
}
