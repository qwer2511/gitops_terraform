output "kubeconfig_command" {
  description = "Command to generate kubeconfig file for the cluster"
  value       = "aws eks get-token --cluster-name ${module.eks.cluster_name} | kubectl apply -f -"
}

output "node_groups_iam_role_arns" {
  description = "IAM role ARNs of node groups"
  value       = { for k, v in module.eks.eks_managed_node_groups : k => v.iam_role_arn }
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ids attached to the cluster control plane"
  value       = module.eks.cluster_security_group_id
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "node_groups" {
  description = "Outputs from EKS node groups"
  value       = module.eks.eks_managed_node_groups
}

# 출력 설명:
# - kubeconfig_command: 클러스터에 접근하기 위한 kubeconfig 생성 명령
# - node_groups_iam_role_arns: 노드 그룹의 IAM 역할 ARN
# - cluster_endpoint: EKS 클러스터 API 서버 엔드포인트
# - cluster_security_group_id: 클러스터 컨트롤 플레인에 연결된 보안 그룹 ID
# - cluster_name: 생성된 EKS 클러스터의 이름
# - cluster_certificate_authority_data: 클러스터와 통신하는 데 필요한 인증서 데이터
# - node_groups: EKS 관리형 노드 그룹에 대한 정보