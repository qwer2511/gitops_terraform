output "cluster_iam_role_name" {
  value = aws_iam_role.eks_cluster.name
}
# EKS 클러스터 IAM 역할의 이름을 출력합니다.

output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}
# EKS 클러스터 IAM 역할의 ARN을 출력합니다.

output "eks_node_group_role_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = aws_iam_role.eks_node_group.arn
}
# EKS 노드 그룹 IAM 역할의 ARN을 출력합니다.