# ---------------------------------------------------------------------------
# EKS control plane + managed node group
#
# This is a STANDARD cluster (NOT EKS Auto Mode). Auto Mode only provisions
# Nitro-generation instances, all of which the account SCP denies, so it can
# never launch a node here. Leaving out any compute/storage auto-mode config
# keeps this a standard cluster where t2.medium works.
# ---------------------------------------------------------------------------

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  version  = var.k8s_version
  role_arn = aws_iam_role.cluster.arn

  access_config {
    authentication_mode = "API"
  }

  vpc_config {
    subnet_ids              = [for s in aws_subnet.public : s.id]
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  tags = var.tags

  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
}

resource "aws_eks_node_group" "this" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "ng-t2medium"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = [for s in aws_subnet.public : s.id]

  instance_types = [var.node_instance_type]
  ami_type       = var.node_ami_type

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  tags = var.tags

  # Node IAM policies must exist before the nodes try to join.
  depends_on = [aws_iam_role_policy_attachment.node]
}
