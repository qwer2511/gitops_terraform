
output "bastion_security_group_id" {
  value       = aws_security_group.bastion.id
  description = "ID of the bastion host security group"
}

output "bastion_public_ip" {
  description = "Public IP of the bastion host"
  value       = aws_instance.bastion.public_ip
}

output "bastion_instance_id" {
  description = "Instance ID of the bastion host"
  value       = aws_instance.bastion.id
}

output "bastion_iam_role_arn" {
  description = "ARN of the IAM role attached to the bastion host"
  value       = aws_iam_role.bastion.arn
}

output "bastion_iam_instance_profile_arn" {
  description = "ARN of the IAM instance profile attached to the bastion host"
  value       = aws_iam_instance_profile.bastion.arn
}