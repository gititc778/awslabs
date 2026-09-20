# ---------------------------------------------------------------------------
# VPC + public networking
# Two public subnets (auto-assign public IP) routed to an Internet Gateway.
# The public IP + IGW route give the nodes outbound egress to ECR / EC2 API /
# STS so the VPC CNI can pull its image and initialise — without that the
# nodes register but stay NotReady. (Node -> control-plane traffic stays
# internal via the cluster's private endpoint regardless.)
# ---------------------------------------------------------------------------

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true # required by EKS
  enable_dns_hostnames = true # required by EKS

  tags = merge(var.tags, { Name = "dev-euw2-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "dev-euw2-igw" })
}

resource "aws_subnet" "public" {
  for_each = var.public_subnets

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value
  map_public_ip_on_launch = true # nodes get a public IP -> egress via IGW

  tags = merge(var.tags, {
    Name                     = "dev-euw2-pub-${substr(each.key, length(each.key) - 1, 1)}"
    "kubernetes.io/role/elb" = "1" # lets EKS place public load balancers here
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "dev-euw2-public-rt" })
}

resource "aws_route" "default_igw" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}
