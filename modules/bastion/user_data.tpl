#!/bin/bash 
# user_data.tpl
# 시스템 업데이트 및 필요한 패키지 설치
sudo apt-get update && apt-get upgrade -y
sudo apt-get install -y unzip curl wget jq

echo "Installing AWS CLI"
sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo unzip awscliv2.zip
sudo ./aws/install

echo "Installing kubectl"
sudo curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo chmod +x kubectl
sudo mv kubectl /usr/local/bin/

echo "Configuring AWS CLI"
mkdir -p /home/ubuntu/.aws
echo "[default]" > /home/ubuntu/.aws/config
echo "region = ap-northeast-2" >> /home/ubuntu/.aws/config

echo "Configuring kubeconfig"
aws eks get-token --cluster-name k8s-cluster --region ap-northeast-2
aws eks update-kubeconfig --name k8s-cluster --region ap-northeast-2

echo "Setting permissions"
chown -R ubuntu:ubuntu /home/ubuntu/.kube /home/ubuntu/.aws

echo "Setting environment variables"
echo "export KUBECONFIG=/home/ubuntu/.kube/config" >> /home/ubuntu/.bashrc
echo "source <(kubectl completion bash)" >> /home/ubuntu/.bashrc

echo "Testing kubectl"
kubectl version --client
kubectl get nodes

echo "Get password for argocd"
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d

echo "Script execution completed"
