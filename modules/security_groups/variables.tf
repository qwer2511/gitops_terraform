variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "cluster_security_group_id" {
  description = "Security group ID of the EKS cluster"
  type        = string
}

variable "bastion_security_group_id" {
  description = "Security group ID of the bastion host"
  type        = string
}
# 이 변수들은 보안 그룹 설정에 필요한 외부 정보를 받아옵니다.
# 클러스터 이름, VPC ID, VPC CIDR, 클러스터 보안 그룹 ID, Bastion 호스트 보안 그룹 ID 등이 포함됩니다.