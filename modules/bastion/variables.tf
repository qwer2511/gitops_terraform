variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "subnet_id" {
  description = "ID of the subnet for the bastion host"
  type        = string
}

variable "instance_type" {
  description = "Instance type for the bastion host"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of the key pair to use for the bastion host"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "create_instance_profile" {
  default = false
}