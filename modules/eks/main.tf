module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_group_defaults = {
    ami_type       = "AL2_x86_64"
    instance_types = ["t3.medium"]
  }

  eks_managed_node_groups = var.node_groups

  # aws-auth configmap
  manage_aws_auth_configmap = true
  aws_auth_users = var.aws_auth_users
  aws_auth_roles = var.aws_auth_roles
}

# 주요 설정 설명:
# 1. cluster_name, cluster_version: EKS 클러스터의 이름과 Kubernetes 버전을 설정합니다.
# 2. vpc_id, subnet_ids: 클러스터가 배포될 VPC와 서브넷을 지정합니다.
# 3. cluster_endpoint_public_access: 클러스터 API 서버에 대한 공개 접근을 허용합니다.
# 4. eks_managed_node_group_defaults: 노드 그룹의 기본 설정을 정의합니다.
# 5. eks_managed_node_groups: 사용자 정의 노드 그룹 설정을 적용합니다.
# 6. manage_aws_auth_configmap, aws_auth_users, aws_auth_roles: AWS IAM 사용자/역할과 Kubernetes RBAC 시스템을 연결합니다.