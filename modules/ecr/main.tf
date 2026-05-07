# ECR 저장소 생성
resource "aws_ecr_repository" "app_repo" {
  name                 = var.repository_name
  image_tag_mutability = "MUTABLE"

  # 이미지 스캔 설정
  image_scanning_configuration {
    scan_on_push = true
  }
}
# 이 리소스는 ECR 리포지토리를 생성합니다.
# - name: 리포지토리의 이름을 지정합니다.
# - image_tag_mutability: "MUTABLE"로 설정하여 이미지 태그를 변경할 수 있게 합니다.
# - image_scanning_configuration: 이미지 푸시 시 자동으로 보안 스캔을 수행하도록 설정합니다.

# ECR 저장소 수명주기 정책 설정
resource "aws_ecr_lifecycle_policy" "app_repo_lifecycle" {
  repository = aws_ecr_repository.app_repo.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "최근 10개 이미지만 유지"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
# 이 리소스는 ECR 리포지토리의 수명주기 정책을 설정합니다.
# - repository: 정책을 적용할 리포지토리를 지정합니다.
# - policy: JSON 형식으로 수명주기 규칙을 정의합니다.
#   - rulePriority: 규칙의 우선순위를 지정합니다.
#   - description: 규칙에 대한 설명을 제공합니다.
#   - selection: 어떤 이미지를 선택할지 정의합니다. 여기서는 10개 이상의 이미지가 있을 때 적용됩니다.
#   - action: 선택된 이미지에 대해 수행할 작업을 지정합니다. 여기서는 "expire"로 설정하여 이미지를 삭제합니다.