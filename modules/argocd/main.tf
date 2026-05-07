# ArgoCD를 위한 Kubernetes 네임스페이스 생성
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = var.namespace
  }
}
# 이 리소스는 ArgoCD를 위한 전용 네임스페이스를 생성합니다.
# 네임스페이스를 분리함으로써 ArgoCD의 리소스를 다른 애플리케이션과 격리할 수 있습니다.

# Helm을 사용하여 ArgoCD 설치
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_version
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  values = [
    templatefile("${path.module}/values.yaml", {
    })
  ]
  depends_on = [kubernetes_namespace.argocd]
}
# 이 리소스는 Helm 차트를 사용하여 ArgoCD를 설치합니다.
# - repository: ArgoCD Helm 차트의 저장소 URL
# - chart: 사용할 Helm 차트의 이름
# - version: 설치할 ArgoCD의 버전
# - namespace: ArgoCD를 설치할 네임스페이스
# - values: ArgoCD 구성을 위한 values.yaml 파일을 템플릿으로 사용
# - depends_on: 네임스페이스 생성 후에 실행되도록 의존성 설정

# ArgoCD 서버 서비스 정보 조회
data "kubernetes_service" "argocd_server" {
  metadata {
    name      = "argocd-server"
    namespace = kubernetes_namespace.argocd.metadata[0].name
  }
  depends_on = [helm_release.argocd]
}
# 이 데이터 소스는 ArgoCD 서버의 서비스 정보를 조회합니다.
# 이를 통해 ArgoCD 서버의 URL 등의 정보를 얻을 수 있습니다.