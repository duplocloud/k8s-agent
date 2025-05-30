FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5002

# Install kubectl and required packages
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg2 wget unzip git --no-install-recommends && \
    curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin
RUN kubectl

# Install Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
    chmod 700 get_helm.sh && \
    ./get_helm.sh && \
    rm get_helm.sh

# Install DuploCloud CLI
RUN wget https://github.com/duplocloud/duplo-jit/releases/download/v0.5.7/duplo-jit_0.5.7_linux_amd64.zip
RUN unzip duplo-jit_0.5.7_linux_amd64.zip -d /usr/local/bin
RUN chmod +x /usr/local/bin/duplo-jit

# Set working directory
WORKDIR /app

# Copy requirements file
COPY k8s/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy python files from k8s directory
COPY k8s/*.py .

# Copy common package
COPY common/ /app/common/

# Create directory for kubeconfig files
RUN mkdir -p /tmp/kubeconfigs

# Expose port
EXPOSE $PORT

# Run the application
CMD ["python", "k8s_api_agent.py"]
