variable "cluster_role_arn" {
  description = "ARN of the IAM role for the EKS cluster"
  type        = string
}

variable "node_role_arn" {
  description = "ARN of the IAM role for the EKS node group"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version to use for the EKS cluster"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the cluster and its nodes will be provisioned"
  type        = string
}

variable "private_subnets" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "node_groups" {
  description = "Map of EKS managed node group definitions to create"
  type        = any
  default     = {}
}

variable "aws_auth_users" {
  description = "List of user maps to add to the aws-auth configmap"
  type        = list(any)
  default     = []
}

variable "aws_auth_roles" {
  description = "List of role maps to add to the aws-auth configmap"
  type        = list(any)
  default     = []
}

# 변수 설명:
# - cluster_role_arn, node_role_arn: EKS 클러스터와 노드 그룹에 사용될 IAM 역할의 ARN
# - cluster_name, cluster_version: EKS 클러스터의 이름과 버전
# - vpc_id, private_subnets: 클러스터가 배포될 VPC와 서브넷 정보
# - node_groups: EKS 관리형 노드 그룹 설정
# - aws_auth_users, aws_auth_roles: aws-auth ConfigMap에 추가할 사용자와 역할 정보