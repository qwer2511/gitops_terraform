# Bastion 호스트를 위한 보안 그룹 생성
resource "aws_security_group" "bastion" {
  name        = "${var.cluster_name}-bastion-sg"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  # SSH 접근 허용 (22번 포트)
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 모든 아웃바운드 트래픽 허용
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-bastion-sg"
  }
}

# 최신 Ubuntu 22.04 AMI 조회
data "aws_ami" "ubuntu_22_04" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Bastion EC2 인스턴스 생성
resource "aws_instance" "bastion" {
  ami           = data.aws_ami.ubuntu_22_04.id
  instance_type = var.instance_type
  key_name      = var.key_name
  vpc_security_group_ids = [aws_security_group.bastion.id]
  subnet_id              = var.subnet_id
  associate_public_ip_address = true

  tags = {
    Name = "${var.cluster_name}-bastion"
  }

  iam_instance_profile = aws_iam_instance_profile.bastion.name
}

# Bastion 호스트를 위한 IAM 역할 생성
resource "aws_iam_role" "bastion" {
  name = "${var.cluster_name}-bastion-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Bastion 호스트에 EKS 관련 정책 연결
resource "aws_iam_role_policy_attachment" "bastion_eks_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.bastion.name
}

resource "aws_iam_role_policy_attachment" "bastion_eks_worker_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.bastion.name
}

resource "aws_iam_role_policy_attachment" "bastion_ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.bastion.name
}

# Bastion 호스트를 위한 IAM 인스턴스 프로파일 생성
resource "aws_iam_instance_profile" "bastion" {
  name = "${var.cluster_name}-bastion-profile"
  role = aws_iam_role.bastion.name
}