# ECR 저장소 URL 출력
output "repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.app_repo.repository_url
}
# 이 출력은 생성된 ECR 리포지토리의 URL을 제공합니다.
# 이 URL은 Docker 이미지를 푸시하거나 풀할 때 사용됩니다.