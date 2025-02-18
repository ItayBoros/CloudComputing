# Multi Instances Project 🚀

This project is part of my cloud computing course and includes Dockerized services and APIs for stock management and capital gains calculations.

## 🚀 Getting Started

### 🔧 Prerequisites
- Docker & Docker Compose
- Python 3.x
- Git

### 📥 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ItayBoros/CloudComputing.git
   cd CloudComputing
   ```
2.	Add your NINJA API KEY where required.
3.	Build and run the services:
   ```bash
   docker compose up --build
   ```
5.	Verify that everything is running:
   ```bash
   docker ps
   ```


# Kubernetes Project 🚀

This project sets up a cloud-native application using Kubernetes (K8s) for container orchestration. The deployment includes microservices running in Docker containers within a scalable, fault-tolerant infrastructure.

## 🔧 Manual Deployment

Copy and paste the following commands into your terminal:
   ```bash
   # Delete any existing Kind cluster
   kind delete cluster

   # Create a new Kind cluster with the specified configuration
   kind create cluster --config kind-config.yaml

   # Apply the namespace configuration
   kubectl apply -f namespace.yaml

   # Deploy the Stocks Application
   cd stocks
   docker build -t stocks-app:latest .
   kind load docker-image stocks-app:latest
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml

   # Deploy the Capital Gains Service
   cd ../capital-gains
   docker build -t capital-gains-service:latest .
   kind load docker-image capital-gains-service:latest
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml

   # Deploy the Database
   cd ../database
   kubectl apply -f PersistentVolume.yaml
   kubectl apply -f PersistentVolumeClaim.yaml
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml

   # Deploy Nginx and its configuration
   cd ../nginx
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   kubectl apply -f configMap.yaml

   # Verify the pods in the project namespace
   kubectl get pods -n project-3-cloud
   ```
Enjoy your deployment! If you run into any issues or have questions, please contact me at itaybor15@gmail.com.
