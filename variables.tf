# 변수 정의
# 이 변수들은 인프라 구성을 유연하게 만들어 줍니다.

variable "region" {
  default = "ap-northeast-2"  # AWS 리전 설정
}

variable "cluster_name" {
  default = "k8s-cluster"  # EKS 클러스터 이름
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"     # VPC의 CIDR 블록
}

variable "azs" {
  default = ["ap-northeast-2a", "ap-northeast-2c"]  # 사용할 가용 영역
}

variable "private_subnets" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]  # 프라이빗 서브넷 CIDR
}

variable "public_subnets" {
  default = ["10.0.4.0/24", "10.0.5.0/24"]  # 퍼블릭 서브넷 CIDR
}


variable "cluster_version" {
  default = "1.30"    # EKS 클러스터 버전
}

variable "namespace" {
  default = "petclinic"  # 기본 네임스페이스 설정
}

variable "node_groups" {
  description = "Map of EKS managed node group definitions to create"
  type = map(object({
    name           = string
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
  }))
  default = {
    eks_node_gitops = {
      name           = "eks_node_gitops"
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
      disk_size      = 20
    }
  }
}

variable "aws_auth_roles" {
  description = "List of role maps to add to the aws-auth configmap"
  type = list(object({
    rolearn  = string
    username = string
    groups   = list(string)
  }))
  default = []
}

variable "aws_auth_users" {
  description = "List of user maps to add to the aws-auth configmap"
  type = list(object({
    userarn  = string
    username = string
    groups   = list(string)
  }))
  default = []
}

variable "bastion_key_name" {
  description = "The key name of the Key Pair to use for the bastion instance"
  type        = string
  default     = "powermvp"
}
