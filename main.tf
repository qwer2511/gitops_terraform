# VPC 모듈 사용
# 이 모듈은 AWS Virtual Private Cloud(VPC)를 생성합니다.
# VPC는 AWS 내의 격리된 가상 네트워크로, 보안과 네트워크 구성의 기초가 됩니다.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name                 = "${var.cluster_name}-vpc"  # VPC 이름 설정
  cidr                 = var.vpc_cidr               # VPC의 IP 주소 범위
  azs                  = var.azs                    # 사용할 가용 영역 (여러 AZ를 사용하여 고가용성 확보)
  private_subnets      = var.private_subnets        # 프라이빗 서브넷 (내부 리소스용)
  public_subnets       = var.public_subnets         # 퍼블릭 서브넷 (인터넷 연결 리소스용)
  enable_nat_gateway   = true                       # NAT 게이트웨이 활성화 (프라이빗 서브넷에서 인터넷 접근 가능)
  single_nat_gateway   = true                       # 단일 NAT 게이트웨이 사용 (비용 절감)
  enable_dns_hostnames = true                       # DNS 호스트네임 활성화

  # EKS 클러스터를 위한 태그 설정
  # 이 태그들은 EKS가 VPC 리소스를 식별하고 사용하는 데 필요합니다.
  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  public_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"  # 외부 로드 밸런서용 태그
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"           = "1"  # 내부 로드 밸런서용 태그
  }
}

# IAM 모듈 사용
# IAM(Identity and Access Management)은 AWS 리소스에 대한 액세스를 안전하게 제어합니다.
# 이 모듈은 EKS 클러스터와 노드 그룹에 필요한 IAM 역할과 정책을 생성합니다.
module "iam" {
  source       = "./modules/iam"
  cluster_name = var.cluster_name
}

# EKS 모듈 사용
# EKS(Elastic Kubernetes Service)는 관리형 Kubernetes 서비스입니다.
# 이 모듈은 EKS 클러스터를 생성하고 구성합니다.
module "eks" {
  source          = "./modules/eks"
  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnets
  node_groups     = local.node_groups

  # IAM 모듈에서 생성한 역할 ARN 사용
  cluster_role_arn = module.iam.eks_cluster_role_arn
  node_role_arn    = module.iam.eks_node_group_role_arn

  aws_auth_roles = var.aws_auth_roles
  aws_auth_users = var.aws_auth_users
}

# aws_auth configMap 설정
# aws-auth ConfigMap은 AWS IAM 사용자/역할과 Kubernetes RBAC 시스템을 연결합니다.
# 이를 통해 AWS IAM 엔터티가 EKS 클러스터에 접근할 수 있습니다.
resource "kubernetes_config_map_v1_data" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = yamlencode(
      concat(
        [for ng in module.eks.node_groups : {
          rolearn  = ng.iam_role_arn
          username = "system:node:{{EC2PrivateDNSName}}"
          groups   = ["system:bootstrappers", "system:nodes", "system:masters"]
        }],
        [{
          rolearn  = module.bastion.bastion_iam_role_arn
          username = "system:node:{{EC2PrivateDNSName}}"
          groups   = ["system:nodes", "system:masters"]
        }],
        var.aws_auth_roles
      )
    )
    mapUsers = yamlencode(var.aws_auth_users)
  }

  force = true
}

# 클러스터 범위의 RBAC 역할 생성
# RBAC(Role-Based Access Control)는 Kubernetes의 접근 제어 시스템입니다.
# 이 리소스는 ArgoCD에 대한 전체 접근 권한을 가진 역할을 생성합니다.
resource "kubernetes_role" "argocd_full_access" {
  metadata {
    name      = "argocd-full-access"
    namespace = "argocd"
  }

  rule {
    api_groups = ["*"]
    resources  = ["*"]
    verbs      = ["*"]
  }
  depends_on = [module.eks]
}

# Role을 EC2 노드에 바인딩
# 이 리소스는 위에서 생성한 역할을 EC2 노드에 바인딩합니다.
# 이를 통해 EC2 노드가 ArgoCD 리소스에 접근할 수 있게 됩니다.
resource "kubernetes_role_binding" "argocd_full_access_binding" {
  metadata {
    name      = "argocd-full-access-binding"
    namespace = "argocd"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.argocd_full_access.metadata[0].name
  }

  subject {
    kind      = "Group"
    name      = "system:nodes"
    api_group = "rbac.authorization.k8s.io"
  }
  depends_on = [module.eks, kubernetes_role.argocd_full_access]
}

# 노드 그룹 정의를 동적으로 생성
# 이 로컬 값은 EKS 노드 그룹을 동적으로 정의합니다.
locals {
  node_groups = {
    for key, group in var.node_groups :
    key => merge(group, {
      iam_role_arn = module.iam.eks_node_group_role_arn
    })
  }
}

# Security Group 모듈 사용
# 보안 그룹은 인바운드 및 아웃바운드 트래픽을 제어하는 가상 방화벽입니다.
# 이 모듈은 VPC 내의 다양한 리소스에 대한 보안 그룹을 설정합니다.
module "security_groups" {
  source                      = "./modules/security_groups"
  vpc_id                      = module.vpc.vpc_id
  cluster_name                = var.cluster_name
  vpc_cidr                    = var.vpc_cidr
  cluster_security_group_id   = module.eks.cluster_security_group_id
  bastion_security_group_id   = module.bastion.bastion_security_group_id
}

# ECR 모듈 호출
# ECR(Elastic Container Registry)는 Docker 컨테이너 이미지를 저장하고 관리하는 서비스입니다.
# 이 모듈은 ECR 리포지토리를 생성합니다.
module "ecr" {
  source          = "./modules/ecr"
  repository_name = "${var.cluster_name}-repo"
}

# Bastion 호스트 모듈 사용
# Bastion 호스트는 프라이빗 네트워크에 안전하게 접근하기 위한 진입점 역할을 합니다.
# 이 모듈은 Bastion 호스트를 생성하고 설정합니다.
module "bastion" {
  source        = "./modules/bastion"
  cluster_name  = var.cluster_name
  vpc_id        = module.vpc.vpc_id
  subnet_id     = module.vpc.public_subnets[0]
  key_name      = var.bastion_key_name
  region        = var.region
}

# ArgoCD 모듈 사용
# ArgoCD는 GitOps를 위한 선언적 연속 배포 도구입니다.
# 이 모듈은 ArgoCD를 EKS 클러스터에 설치하고 구성합니다.
module "argocd" {
  source     = "./modules/argocd"
  depends_on = [module.eks]
}
