# ECR 저장소 이름 변수
variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}
# 이 변수는 ECR 리포지토리의 이름을 지정하는 데 사용됩니다.
# 모듈을 사용할 때 이 값을 제공하여 리포지토리 이름을 설정할 수 있습니다.