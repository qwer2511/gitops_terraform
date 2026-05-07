# EKS 클러스터를 위한 IAM 역할 생성
resource "aws_iam_role" "eks_cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
    ]
  })
}
# 이 역할은 EKS 서비스가 사용자 대신 다른 AWS 서비스를 호출할 수 있도록 합니다.
# 'eks.amazonaws.com' 서비스가 이 역할을 맡을 수 있습니다.

# EKS 클러스터 정책 연결
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}
# 이 정책은 EKS 클러스터가 필요한 AWS 리소스에 접근할 수 있는 권한을 제공합니다.

# VPC 리소스 컨트롤러 정책 연결
resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}
# 이 정책은 EKS가 VPC 내의 리소스(예: 보안 그룹)를 관리할 수 있게 합니다.

# EKS 노드 그룹을 위한 IAM 역할 생성
resource "aws_iam_role" "eks_node_group" {
  name = "${var.cluster_name}-node-group"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}
# 이 역할은 EKS 노드 그룹의 EC2 인스턴스가 사용합니다.
# 'ec2.amazonaws.com' 서비스가 이 역할을 맡을 수 있습니다.

# EKS 노드 그룹 정책 연결
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group.name
}
# 이 정책은 EKS 워커 노드가 EKS 클러스터와 통신하는 데 필요한 권한을 제공합니다.

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group.name
}
# 이 정책은 Amazon VPC CNI 플러그인이 VPC 네트워킹을 구성하는 데 필요한 권한을 제공합니다.

resource "aws_iam_role_policy_attachment" "ec2_container_registry_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group.name
}
# 이 정책은 EKS 노드가 ECR(Elastic Container Registry)에서 컨테이너 이미지를 가져올 수 있게 합니다.