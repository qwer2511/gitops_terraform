variable "namespace" {
  description = "Kubernetes namespace for ArgoCD"
  default     = "argocd"
}
# ArgoCD를 설치할 Kubernetes 네임스페이스를 지정합니다.

variable "argocd_version" {
  description = "Version of ArgoCD Helm chart"
  default     = "5.51.0"
}
# 설치할 ArgoCD Helm 차트의 버전을 지정합니다.

variable "admin_password" {
  description = "ArgoCD admin password"
  default     = "It12341!"
}
# ArgoCD 관리자 계정의 비밀번호를 지정합니다.
# 주의: 실제 운영 환경에서는 이 비밀번호를 변수로 받아 사용하거나, 더 안전한 방법으로 관리해야 합니다.