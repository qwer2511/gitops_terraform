output "worker_group_security_group_id" {
  description = "ID of the worker group security group"
  value       = aws_security_group.worker_group.id
}
# 이 출력은 생성된 워커 노드 보안 그룹의 ID를 제공합니다.
# 다른 모듈이나 리소스에서 이 보안 그룹을 참조해야 할 때 사용할 수 있습니다.