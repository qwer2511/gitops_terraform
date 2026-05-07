# 클러스터 API 서버로의 접근을 위한 보안 그룹 규칙
resource "aws_security_group_rule" "cluster_api_bastion" {
  description              = "Allow bastion host to communicate with the cluster API Server"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = var.cluster_security_group_id
  source_security_group_id = var.bastion_security_group_id
  to_port                  = 443
  type                     = "ingress"
}
# 이 규칙은 Bastion 호스트가 EKS 클러스터의 API 서버와 통신할 수 있도록 합니다.
# HTTPS 포트(443)를 통해 Bastion 호스트에서 클러스터 API 서버로의 인바운드 트래픽을 허용합니다.

# 워커 노드를 위한 보안 그룹
resource "aws_security_group" "worker_group" {
  name_prefix = "${var.cluster_name}-worker_group_mgmt"
  vpc_id      = var.vpc_id

  # 노드 간 모든 통신 허용
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }
  # 이 규칙은 워커 노드 간의 모든 트래픽을 허용합니다. 이는 클러스터 내부 통신에 필요합니다.

  # 아웃바운드 트래픽 허용
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # 이 규칙은 워커 노드에서 인터넷으로의 모든 아웃바운드 트래픽을 허용합니다.

  tags = {
    Name = "${var.cluster_name}-worker-sg"
  }
}

resource "aws_security_group_rule" "worker_ingress_vpc" {
  description       = "Allow VPC CIDR to communicate with worker nodes"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.worker_group.id
  cidr_blocks       = [var.vpc_cidr]
  type              = "ingress"
}
# 이 규칙은 VPC 내의 모든 리소스가 워커 노드와 통신할 수 있도록 합니다.
# VPC CIDR 블록에서 워커 노드로의 모든 TCP 트래픽을 허용합니다.

# 클러스터 API 서버에서 워커 노드로의 접근 허용
resource "aws_security_group_rule" "cluster_ingress_node_https" {
  description              = "Allow pods to communicate with the cluster API Server"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = var.cluster_security_group_id
  source_security_group_id = aws_security_group.worker_group.id
  to_port                  = 443
  type                     = "ingress"
}
# 이 규칙은 워커 노드에서 실행되는 파드가 클러스터 API 서버와 통신할 수 있도록 합니다.
# 워커 노드의 보안 그룹에서 클러스터 API 서버의 보안 그룹으로 HTTPS 트래픽을 허용합니다.