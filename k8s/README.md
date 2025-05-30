# Kubernetes AI Troubleshooting Agent

An AI-powered agent for troubleshooting Kubernetes clusters using natural language queries, available as a REST API.

## Features

- Natural language interface for Kubernetes troubleshooting
- Powered by AWS Bedrock (Anthropic's Claude 3.5 Sonnet) to interpret your requests
- Suggests appropriate kubectl commands based on your questions
- Maintains conversation context for coherent troubleshooting
- Supports namespace-specific diagnostics
- Available as REST API

## Requirements

- Python 3.7+
- kubectl configured with access to your Kubernetes cluster
- AWS credentials with access to Bedrock (Anthropic's Claude 3.5 Sonnet model must be enabled in your AWS account and region)

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your AWS credentials (not needed when running in DuploCloud):
   ```
   # Create a .env file or set environment variables
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1  # Region where Bedrock/Claude is enabled
   ```

## Usage Options

### REST API Agent

Start the REST API server:
```
python k8s_api_agent.py
```

This starts a Flask server on port 5002 with the following endpoints:

#### Send Message API

**Endpoint:** `POST /api/sendMessage`

**Request and Response Structure:**

Both requests and responses use a similar structure, with `Cmds` as an array of objects containing `Command` and `Output` fields, nested under a `data` field. Note that requests use lowercase `content` while responses use uppercase `Content`.

**Request Body Options:**

1. Regular question:
```json
{
  "content": "This is the user message",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

> **Note:** The `kubeconfig` field inside the `data` object is optional. If provided, it will be used for this specific user/thread. If not provided, the system will use the default configuration. AWS credentials are automatically detected from environment variables or instance metadata when running in DuploCloud.

2. Command execution (manual):
```json
{
  "content": "run: kubectl get pods -n kube-system",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

3. Command analysis (for commands run outside the agent):
```json
{
  "content": "Please analyze this command output",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get pods -n kube-system",
        "Output": "NAME                                  READY   STATUS    RESTARTS   AGE\ncoredns-5d78c9869d-q8s9h              1/1     Running   0          45d\nkube-proxy-wlqbg                      1/1     Running   0          45d"
      }
    ],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

4. Auto-execute all suggested commands (global execute flag):
```json
{
  "content": "Check for failed pods in all namespaces",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content",
    "execute": true
  }
}
```

5. Execute specific commands only:
```json
{
  "content": "Check for failed pods in all namespaces",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get pods --all-namespaces",
        "Output": "",
        "execute": true
      },
      {
        "Command": "kubectl get nodes",
        "Output": "",
        "execute": false
      }
    ],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

**Response:**
```json
{
  "Content": "This is the message from the agent",
  "thread_id": "conversation-thread-id",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get deployments -n kube-system",
        "Output": "",
        "execute": false
      },
      {
        "Command": "kubectl describe pod coredns-5d78c9869d-q8s9h -n kube-system",
        "Output": "",
        "execute": false
      }
    ]
  }
}
```

**Response with executed commands:**
```json
{
  "Content": "This is the message from the agent with executed command results",
  "thread_id": "conversation-thread-id",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get deployments -n kube-system",
        "Output": "NAME      READY   UP-TO-DATE   AVAILABLE   AGE\ncoredns   2/2     2            2           45d",
        "execute": true
      },
      {
        "Command": "kubectl describe pod coredns-5d78c9869d-q8s9h -n kube-system",
        "Output": "",
        "execute": false
      }
    ]
  }
}
```

- If no `thread_id` is provided, a new conversation thread will be created
- To execute a command, send a message with `Content` starting with `run:` followed by the kubectl command
- To analyze command output from commands run outside the agent, include the commands and their outputs in the `Cmds` array
- In responses, the `Cmds` array contains suggested kubectl commands (with empty `Output` fields) and executed commands (with populated `Output` fields)

#### Health Check API

**Endpoint:** `GET /api/health?data.kubeconfig=base64-encoded-kubeconfig-content`

Checks the health of the API and verifies kubectl access. You can optionally provide a base64-encoded kubeconfig to test connectivity to a specific cluster.

**Response:**
```json
{
  "status": "healthy",
  "kubectl_access": true,
  "kubectl_message": "Connected to Kubernetes cluster successfully!"
}
```

## Example Queries

- "Check for failed pods in kube-system namespace" with custom kubeconfig and anthropic token:
```json
{
  "Content": "Check for failed pods in kube-system namespace",
  "thread_id": "optional-thread-id-for-conversation-context",
  "kubeconfig": "base64-encoded-kubeconfig-content",
  "data": {
    "Cmds": []
  }
}
```

- "Why is my deployment not scaling in the production namespace?" with default kubeconfig and anthropic token:
```json
{
  "Content": "Why is my deployment not scaling in the production namespace?",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": []
  }
}
```

- "Show recent events in the default namespace" with custom kubeconfig and anthropic token:
```json
{
  "Content": "Show recent events in the default namespace",
  "thread_id": "optional-thread-id-for-conversation-context",
  "kubeconfig": "base64-encoded-kubeconfig-content",
  "data": {
    "Cmds": []
  }
}
```

- "List all pods with high restart counts" with default kubeconfig and anthropic token:
```json
{
  "Content": "List all pods with high restart counts",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": []
  }
}
```

- "Diagnose why my StatefulSet is stuck" with custom kubeconfig and anthropic token:
```json
{
  "Content": "Diagnose why my StatefulSet is stuck",
  "thread_id": "optional-thread-id-for-conversation-context",
  "kubeconfig": "base64-encoded-kubeconfig-content",
  "data": {
    "Cmds": []
  }
}
```
- "Why is my deployment not scaling in the production namespace?"
- "Show recent events in the default namespace"
- "List all pods with high restart counts"
- "Diagnose why my StatefulSet is stuck"

## How It Works

1. You send a natural language query about your Kubernetes cluster
2. The agent uses Anthropic LLMs to interpret your request
3. It suggests appropriate kubectl commands with explanations
4. You can choose to run the suggested commands
5. The agent analyzes command outputs and provides insights
6. Conversation context is maintained for coherent troubleshooting

## Example Query request bodies to test docker compose to helm chart conversion

# cURL request and response for testing "convert the following docker compose into a helm chart and install it"

Request 1:
```
curl --location 'https://venkatk8sagent-andy.test10-apps.duplocloud.net/api/sendMessage' \
--header 'Content-Type: application/json' \
--data '{

  "content": "can you convert this docker compose into a helm chart and install it \n\nversion: '\''3'\''\n\nservices:\n  browser-agent:\n    platform: linux/amd64\n    image: nginx:latest\n    container_name: browser-agent\n    ports:\n      - \"5001:5001\"\n    environment:\n      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}\n      - LOG_LEVEL=INFO\n      - LOG_DIR=logs\n      - MAX_TOKENS=100000\n      - BASE_THROTTLING_DELAY=2\n      - MAX_THROTTLING_RETRIES=5\n      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}\n      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}\n      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}\n    restart: unless-stopped",

  "thread_id": "helmtest1",

  "data": {
        "Cmds": [

        ]
    
  },
      "platform_context" : {
    "k8s_namespace" : "duploservices-andy"
    }
}
'
```

Response 1:

```
{
    "Content": "Certainly! I'll convert your Docker Compose file into a Helm chart and provide you with the necessary files and commands to install it. Here's an explanation of the process and the resulting Helm chart:\n\n1. Chart Structure:\n   We'll create a new Helm chart called \"browser-agent\" with the following structure:\n   - browser-agent/\n     - Chart.yaml\n     - values.yaml\n     - templates/\n       - deployment.yaml\n       - service.yaml\n     - .helmignore\n\n2. Conversion Details:\n   - The Docker service will be converted to a Kubernetes Deployment.\n   - We'll create a Kubernetes Service to expose the port.\n   - Environment variables will be stored in the values.yaml file for easy configuration.\n   - The container image and tag will be configurable in the values.yaml file.\n\n3. Installation:\n   After creating the chart, we'll install it using the Helm install command.\n\nNow, let's go through the Helm chart creation and installation process.\n",
    "data": {
        "Cmds": [
            {
                "Command": "helm install browser-agent ./browser-agent --namespace=duploservices-andy",
                "Output": "",
                "execute": false,
                "files": [
                    {
                        "file_content": "apiVersion: v2\nname: browser-agent\ndescription: A Helm chart for the Browser Agent application\ntype: application\nversion: 0.1.0\nappVersion: \"1.0.0\"",
                        "file_path": "browser-agent/Chart.yaml"
                    },
                    {
                        "file_content": "replicaCount: 1\n\nimage:\n  repository: nginx\n  tag: latest\n  pullPolicy: IfNotPresent\n\nservice:\n  type: ClusterIP\n  port: 5001\n\nenvironment:\n  BEDROCK_MODEL_ID: \"\"\n  LOG_LEVEL: INFO\n  LOG_DIR: logs\n  MAX_TOKENS: \"100000\"\n  BASE_THROTTLING_DELAY: \"2\"\n  MAX_THROTTLING_RETRIES: \"5\"\n  AWS_ACCESS_KEY_ID: \"\"\n  AWS_SECRET_ACCESS_KEY: \"\"\n  AWS_DEFAULT_REGION: \"\"\n\nresources: {}\n\nnodeSelector: {}\n\ntolerations: []\n\naffinity: {}",
                        "file_path": "browser-agent/values.yaml"
                    },
                    {
                        "file_content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  replicas: {{ .Values.replicaCount }}\n  selector:\n    matchLabels:\n      {{- include \"browser-agent.selectorLabels\" . | nindent 6 }}\n  template:\n    metadata:\n      labels:\n        {{- include \"browser-agent.selectorLabels\" . | nindent 8 }}\n    spec:\n      containers:\n        - name: {{ .Chart.Name }}\n          image: \"{{ .Values.image.repository }}:{{ .Values.image.tag }}\"\n          imagePullPolicy: {{ .Values.image.pullPolicy }}\n          ports:\n            - name: http\n              containerPort: 5001\n              protocol: TCP\n          env:\n            {{- range $key, $value := .Values.environment }}\n            - name: {{ $key }}\n              value: {{ $value | quote }}\n            {{- end }}\n          resources:\n            {{- toYaml .Values.resources | nindent 12 }}\n      {{- with .Values.nodeSelector }}\n      nodeSelector:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.affinity }}\n      affinity:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.tolerations }}\n      tolerations:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}",
                        "file_path": "browser-agent/templates/deployment.yaml"
                    },
                    {
                        "file_content": "apiVersion: v1\nkind: Service\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  type: {{ .Values.service.type }}\n  ports:\n    - port: {{ .Values.service.port }}\n      targetPort: http\n      protocol: TCP\n      name: http\n  selector:\n    {{- include \"browser-agent.selectorLabels\" . | nindent 4 }}",
                        "file_path": "browser-agent/templates/service.yaml"
                    },
                    {
                        "file_content": "{{/*\nExpand the name of the chart.\n*/}}\n{{- define \"browser-agent.name\" -}}\n{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCreate a default fully qualified app name.\nWe truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).\nIf release name contains chart name it will be used as a full name.\n*/}}\n{{- define \"browser-agent.fullname\" -}}\n{{- if .Values.fullnameOverride }}\n{{- .Values.fullnameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- $name := default .Chart.Name .Values.nameOverride }}\n{{- if contains $name .Release.Name }}\n{{- .Release.Name | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- printf \"%s-%s\" .Release.Name $name | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n{{- end }}\n{{- end }}\n\n{{/*\nCreate chart name and version as used by the chart label.\n*/}}\n{{- define \"browser-agent.chart\" -}}\n{{- printf \"%s-%s\" .Chart.Name .Chart.Version | replace \"+\" \"_\" | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCommon labels\n*/}}\n{{- define \"browser-agent.labels\" -}}\nhelm.sh/chart: {{ include \"browser-agent.chart\" . }}\n{{ include \"browser-agent.selectorLabels\" . }}\n{{- if .Chart.AppVersion }}\napp.kubernetes.io/version: {{ .Chart.AppVersion | quote }}\n{{- end }}\napp.kubernetes.io/managed-by: {{ .Release.Service }}\n{{- end }}\n\n{{/*\nSelector labels\n*/}}\n{{- define \"browser-agent.selectorLabels\" -}}\napp.kubernetes.io/name: {{ include \"browser-agent.name\" . }}\napp.kubernetes.io/instance: {{ .Release.Name }}\n{{- end }}",
                        "file_path": "browser-agent/templates/_helpers.tpl"
                    },
                    {
                        "file_content": "# Patterns to ignore when building packages.\n# This supports shell glob matching, relative path matching, and\n# negation (prefixed with !).\n.DS_Store\n# Common VCS dirs\n.git/\n.gitignore\n.bzr/\n.bzrignore\n.hg/\n.hgignore\n.svn/\n# Common backup files\n*.swp\n*.bak\n*.tmp\n*.orig\n*~\n# Various IDEs\n.project\n.idea/\n*.tmproj\n.vscode/",
                        "file_path": "browser-agent/.helmignore"
                    }
                ]
            }
        ],
        "execute_all": false,
        "executedCmds": []
    },
    "thread_id": "helmtest1"
}
```

Request 2:
(Approve the files and command)

```
curl --location 'https://venkatk8sagent-andy.test10-apps.duplocloud.net/api/sendMessage' \
--header 'Content-Type: application/json' \
--data '{






  "content": "can you convert this docker compose into a helm chart and install it \n\nversion: '\''3'\''\n\nservices:\n  browser-agent:\n    platform: linux/amd64\n    image: nginx:latest\n    container_name: browser-agent\n    ports:\n      - \"5001:5001\"\n    environment:\n      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}\n      - LOG_LEVEL=INFO\n      - LOG_DIR=logs\n      - MAX_TOKENS=100000\n      - BASE_THROTTLING_DELAY=2\n      - MAX_THROTTLING_RETRIES=5\n      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}\n      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}\n      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}\n    restart: unless-stopped",

  "thread_id": "helmtest1",

  "data": {
        "Cmds": [
                        {
                "Command": "helm install browser-agent ./browser-agent --namespace=duploservices-andy",
                "Output": "",
                "execute": true,
                "files": [
                    {
                        "file_content": "apiVersion: v2\nname: browser-agent\ndescription: A Helm chart for the Browser Agent application\ntype: application\nversion: 0.1.0\nappVersion: \"1.0.0\"",
                        "file_path": "browser-agent/Chart.yaml"
                    },
                    {
                        "file_content": "replicaCount: 1\n\nimage:\n  repository: nginx\n  tag: latest\n  pullPolicy: IfNotPresent\n\nservice:\n  type: ClusterIP\n  port: 5001\n\nenvironment:\n  BEDROCK_MODEL_ID: \"\"\n  LOG_LEVEL: INFO\n  LOG_DIR: logs\n  MAX_TOKENS: \"100000\"\n  BASE_THROTTLING_DELAY: \"2\"\n  MAX_THROTTLING_RETRIES: \"5\"\n  AWS_ACCESS_KEY_ID: \"\"\n  AWS_SECRET_ACCESS_KEY: \"\"\n  AWS_DEFAULT_REGION: \"\"\n\nresources: {}\n\nnodeSelector: {}\n\ntolerations: []\n\naffinity: {}",
                        "file_path": "browser-agent/values.yaml"
                    },
                    {
                        "file_content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  replicas: {{ .Values.replicaCount }}\n  selector:\n    matchLabels:\n      {{- include \"browser-agent.selectorLabels\" . | nindent 6 }}\n  template:\n    metadata:\n      labels:\n        {{- include \"browser-agent.selectorLabels\" . | nindent 8 }}\n    spec:\n      containers:\n        - name: {{ .Chart.Name }}\n          image: \"{{ .Values.image.repository }}:{{ .Values.image.tag }}\"\n          imagePullPolicy: {{ .Values.image.pullPolicy }}\n          ports:\n            - name: http\n              containerPort: 5001\n              protocol: TCP\n          env:\n            {{- range $key, $value := .Values.environment }}\n            - name: {{ $key }}\n              value: {{ $value | quote }}\n            {{- end }}\n          resources:\n            {{- toYaml .Values.resources | nindent 12 }}\n      {{- with .Values.nodeSelector }}\n      nodeSelector:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.affinity }}\n      affinity:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.tolerations }}\n      tolerations:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}",
                        "file_path": "browser-agent/templates/deployment.yaml"
                    },
                    {
                        "file_content": "apiVersion: v1\nkind: Service\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  type: {{ .Values.service.type }}\n  ports:\n    - port: {{ .Values.service.port }}\n      targetPort: http\n      protocol: TCP\n      name: http\n  selector:\n    {{- include \"browser-agent.selectorLabels\" . | nindent 4 }}",
                        "file_path": "browser-agent/templates/service.yaml"
                    },
                    {
                        "file_content": "{{/*\nExpand the name of the chart.\n*/}}\n{{- define \"browser-agent.name\" -}}\n{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCreate a default fully qualified app name.\nWe truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).\nIf release name contains chart name it will be used as a full name.\n*/}}\n{{- define \"browser-agent.fullname\" -}}\n{{- if .Values.fullnameOverride }}\n{{- .Values.fullnameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- $name := default .Chart.Name .Values.nameOverride }}\n{{- if contains $name .Release.Name }}\n{{- .Release.Name | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- printf \"%s-%s\" .Release.Name $name | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n{{- end }}\n{{- end }}\n\n{{/*\nCreate chart name and version as used by the chart label.\n*/}}\n{{- define \"browser-agent.chart\" -}}\n{{- printf \"%s-%s\" .Chart.Name .Chart.Version | replace \"+\" \"_\" | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCommon labels\n*/}}\n{{- define \"browser-agent.labels\" -}}\nhelm.sh/chart: {{ include \"browser-agent.chart\" . }}\n{{ include \"browser-agent.selectorLabels\" . }}\n{{- if .Chart.AppVersion }}\napp.kubernetes.io/version: {{ .Chart.AppVersion | quote }}\n{{- end }}\napp.kubernetes.io/managed-by: {{ .Release.Service }}\n{{- end }}\n\n{{/*\nSelector labels\n*/}}\n{{- define \"browser-agent.selectorLabels\" -}}\napp.kubernetes.io/name: {{ include \"browser-agent.name\" . }}\napp.kubernetes.io/instance: {{ .Release.Name }}\n{{- end }}",
                        "file_path": "browser-agent/templates/_helpers.tpl"
                    },
                    {
                        "file_content": "# Patterns to ignore when building packages.\n# This supports shell glob matching, relative path matching, and\n# negation (prefixed with !).\n.DS_Store\n# Common VCS dirs\n.git/\n.gitignore\n.bzr/\n.bzrignore\n.hg/\n.hgignore\n.svn/\n# Common backup files\n*.swp\n*.bak\n*.tmp\n*.orig\n*~\n# Various IDEs\n.project\n.idea/\n*.tmproj\n.vscode/",
                        "file_path": "browser-agent/.helmignore"
                    }
                ]
            }

        ]
    
    
  },

      "platform_context" : {
    "k8s_namespace" : "duploservices-andy"
    }
}
'
```

Response 2:

```
{
    "Content": "Analysis of command(s):\n\nBased on the output you've provided, it appears that the Helm installation of the \"browser-agent\" chart was successful. The command completed with a return code of 0, which typically indicates that there were no errors during the installation process. Let's break down the information and suggest some next steps:\n\n1. Installation Status:\n   - The chart named \"browser-agent\" was successfully installed.\n   - It was deployed in the \"duploservices-andy\" namespace.\n   - The current status is \"deployed\".\n   - This is the first revision of this release.\n\n2. Next Steps and Recommendations:\n\n   a) Verify the deployment:\n      Even though the Helm installation was successful, it's a good practice to verify that all the Kubernetes resources were created correctly and are running as expected.\n\n   b) Check the pod status:\n      Let's look at the pods created by this Helm release to ensure they're running correctly.\n\n   c) Inspect the services:\n      If your chart includes any services, we should check if they're properly created and have the correct endpoints.\n\n   d) Review any ingress resources:\n      If your application is meant to be accessible from outside the cluster, check any ingress resources that might have been created.\n\n   e) Check for any configuration issues:\n      Sometimes, even though the deployment is successful, there might be configuration issues that prevent the application from working correctly.\n\nI'll provide kubectl commands to help you with these next steps. These commands will help us gather more information about the state of your deployment.",
    "data": {
        "Cmds": [
            {
                "Command": "kubectl get ingress -n duploservices-andy -l app.kubernetes.io/instance=browser-agent",
                "Output": "",
                "execute": false
            },
            {
                "Command": "kubectl get services -n duploservices-andy -l app.kubernetes.io/instance=browser-agent",
                "Output": "",
                "execute": false
            },
            {
                "Command": "kubectl describe deployment -n duploservices-andy -l app.kubernetes.io/instance=browser-agent",
                "Output": "",
                "execute": false
            },
            {
                "Command": "kubectl get pods -n duploservices-andy -l app.kubernetes.io/instance=browser-agent",
                "Output": "",
                "execute": false
            }
        ],
        "executedCmds": [
            {
                "Command": "helm install browser-agent ./browser-agent --namespace=duploservices-andy",
                "Output": "STDOUT:\nNAME: browser-agent\nLAST DEPLOYED: Thu May  8 21:03:42 2025\nNAMESPACE: duploservices-andy\nSTATUS: deployed\nREVISION: 1\nTEST SUITE: None\n\nCommand completed with return code: 0",
                "execute": true,
                "files": [
                    {
                        "file_content": "apiVersion: v2\nname: browser-agent\ndescription: A Helm chart for the Browser Agent application\ntype: application\nversion: 0.1.0\nappVersion: \"1.0.0\"",
                        "file_path": "browser-agent/Chart.yaml"
                    },
                    {
                        "file_content": "replicaCount: 1\n\nimage:\n  repository: nginx\n  tag: latest\n  pullPolicy: IfNotPresent\n\nservice:\n  type: ClusterIP\n  port: 5001\n\nenvironment:\n  BEDROCK_MODEL_ID: \"\"\n  LOG_LEVEL: INFO\n  LOG_DIR: logs\n  MAX_TOKENS: \"100000\"\n  BASE_THROTTLING_DELAY: \"2\"\n  MAX_THROTTLING_RETRIES: \"5\"\n  AWS_ACCESS_KEY_ID: \"\"\n  AWS_SECRET_ACCESS_KEY: \"\"\n  AWS_DEFAULT_REGION: \"\"\n\nresources: {}\n\nnodeSelector: {}\n\ntolerations: []\n\naffinity: {}",
                        "file_path": "browser-agent/values.yaml"
                    },
                    {
                        "file_content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  replicas: {{ .Values.replicaCount }}\n  selector:\n    matchLabels:\n      {{- include \"browser-agent.selectorLabels\" . | nindent 6 }}\n  template:\n    metadata:\n      labels:\n        {{- include \"browser-agent.selectorLabels\" . | nindent 8 }}\n    spec:\n      containers:\n        - name: {{ .Chart.Name }}\n          image: \"{{ .Values.image.repository }}:{{ .Values.image.tag }}\"\n          imagePullPolicy: {{ .Values.image.pullPolicy }}\n          ports:\n            - name: http\n              containerPort: 5001\n              protocol: TCP\n          env:\n            {{- range $key, $value := .Values.environment }}\n            - name: {{ $key }}\n              value: {{ $value | quote }}\n            {{- end }}\n          resources:\n            {{- toYaml .Values.resources | nindent 12 }}\n      {{- with .Values.nodeSelector }}\n      nodeSelector:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.affinity }}\n      affinity:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}\n      {{- with .Values.tolerations }}\n      tolerations:\n        {{- toYaml . | nindent 8 }}\n      {{- end }}",
                        "file_path": "browser-agent/templates/deployment.yaml"
                    },
                    {
                        "file_content": "apiVersion: v1\nkind: Service\nmetadata:\n  name: {{ include \"browser-agent.fullname\" . }}\n  labels:\n    {{- include \"browser-agent.labels\" . | nindent 4 }}\nspec:\n  type: {{ .Values.service.type }}\n  ports:\n    - port: {{ .Values.service.port }}\n      targetPort: http\n      protocol: TCP\n      name: http\n  selector:\n    {{- include \"browser-agent.selectorLabels\" . | nindent 4 }}",
                        "file_path": "browser-agent/templates/service.yaml"
                    },
                    {
                        "file_content": "{{/*\nExpand the name of the chart.\n*/}}\n{{- define \"browser-agent.name\" -}}\n{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCreate a default fully qualified app name.\nWe truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).\nIf release name contains chart name it will be used as a full name.\n*/}}\n{{- define \"browser-agent.fullname\" -}}\n{{- if .Values.fullnameOverride }}\n{{- .Values.fullnameOverride | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- $name := default .Chart.Name .Values.nameOverride }}\n{{- if contains $name .Release.Name }}\n{{- .Release.Name | trunc 63 | trimSuffix \"-\" }}\n{{- else }}\n{{- printf \"%s-%s\" .Release.Name $name | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n{{- end }}\n{{- end }}\n\n{{/*\nCreate chart name and version as used by the chart label.\n*/}}\n{{- define \"browser-agent.chart\" -}}\n{{- printf \"%s-%s\" .Chart.Name .Chart.Version | replace \"+\" \"_\" | trunc 63 | trimSuffix \"-\" }}\n{{- end }}\n\n{{/*\nCommon labels\n*/}}\n{{- define \"browser-agent.labels\" -}}\nhelm.sh/chart: {{ include \"browser-agent.chart\" . }}\n{{ include \"browser-agent.selectorLabels\" . }}\n{{- if .Chart.AppVersion }}\napp.kubernetes.io/version: {{ .Chart.AppVersion | quote }}\n{{- end }}\napp.kubernetes.io/managed-by: {{ .Release.Service }}\n{{- end }}\n\n{{/*\nSelector labels\n*/}}\n{{- define \"browser-agent.selectorLabels\" -}}\napp.kubernetes.io/name: {{ include \"browser-agent.name\" . }}\napp.kubernetes.io/instance: {{ .Release.Name }}\n{{- end }}",
                        "file_path": "browser-agent/templates/_helpers.tpl"
                    },
                    {
                        "file_content": "# Patterns to ignore when building packages.\n# This supports shell glob matching, relative path matching, and\n# negation (prefixed with !).\n.DS_Store\n# Common VCS dirs\n.git/\n.gitignore\n.bzr/\n.bzrignore\n.hg/\n.hgignore\n.svn/\n# Common backup files\n*.swp\n*.bak\n*.tmp\n*.orig\n*~\n# Various IDEs\n.project\n.idea/\n*.tmproj\n.vscode/",
                        "file_path": "browser-agent/.helmignore"
                    }
                ]
            }
        ]
    },
    "thread_id": "helmtest1"
}
```


## License

MIT
