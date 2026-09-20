variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "itcdevops"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "dev-euw2-eks-01"
}

variable "k8s_version" {
  description = "Kubernetes version for the EKS control plane"
  type        = string
  default     = "1.36"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Two public subnets across two AZs. Matches the existing dev-euw2-vpc layout.
variable "public_subnets" {
  description = "Map of AZ => subnet CIDR for the (public) node subnets"
  type        = map(string)
  default = {
    "eu-west-2a" = "10.0.1.0/24"
    "eu-west-2b" = "10.0.2.0/24"
  }
}

# t2.medium is the largest instance type the account SCP (p-yz1hiqdn) permits.
# Do NOT change to t3/Graviton — those are denied by the SCP, and Auto Mode
# (which only launches Nitro instances) will not work in this account at all.
variable "node_instance_type" {
  description = "Worker node instance type (must be SCP-allowed: t2.nano/micro/small/medium)"
  type        = string
  default     = "t2.medium"
}

variable "node_ami_type" {
  description = "EKS node AMI type. t2 is x86-only, so use an x86_64 AMI."
  type        = string
  default     = "AL2023_x86_64_STANDARD"
}

variable "node_desired_size" {
  type    = number
  default = 1
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 2
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "ekslab"
    ManagedBy   = "terraform"
  }
}
