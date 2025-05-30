#!/bin/bash

set -eu -o pipefail

# Script to build and push Docker image to Docker Hub
# Usage: ./build.sh

# Configuration
DOCKER_REPO="docker.io/duplocloud/ai-agents"
IMAGE_TAG=${1:-k8s_agent_latest}

echo "Building and pushing Docker image with tag: $IMAGE_TAG"

# Step 1: Build Docker image
echo "Building Docker image..."
# Use parent directory as context and specify the Dockerfile location
docker build -t $DOCKER_REPO:$IMAGE_TAG -f Dockerfile ..

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to build Docker image"
    exit 1
fi

# Step 2: Push Docker image to Docker Hub
echo "Pushing Docker image to Docker Hub..."
docker push $DOCKER_REPO:$IMAGE_TAG

# Check if push was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to push Docker image"
    exit 1
fi

echo "Successfully built and pushed $DOCKER_REPO:$IMAGE_TAG"