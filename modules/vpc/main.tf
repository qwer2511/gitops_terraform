# VPC 모듈 사용
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"  # 최신 주 버전으로 업데이트

  name                 = "${var.cluster_name}-vpc"  # VPC 이름 설정
  cidr                 = var.vpc_cidr               # VPC의 CIDR 블록
  azs                  = var.azs                    # 사용할 가용 영역
  private_subnets      = var.private_subnets        # 프라이빗 서브넷 CIDR
  public_subnets       = var.public_subnets         # 퍼블릭 서브넷 CIDR
  enable_nat_gateway   = true                       # NAT 게이트웨이 활성화
  single_nat_gateway   = true                       # 단일 NAT 게이트웨이 사용 (비용 절감)
  enable_dns_hostnames = true                       # DNS 호스트네임 활성화

  # EKS 클러스터를 위한 태그 설정
  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"  # EKS 클러스터와 VPC 리소스 연결
  }
}