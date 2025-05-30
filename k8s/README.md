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
  "content": "Hello!",
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

**Example Agent Response with executed commands as well as suggested commands:**
```json

{
    "Content": "Analysis of command(s):\n\nBased on the output, there are two pods with issues:\n\n1. dummy-250527154358-865cfbb7db-9h6tm: In CrashLoopBackOff state\n2. k8s-demo-7fc788997c-pwdv6: Has CreateContainerConfigError\n\nNext steps:\n1. Check logs for the crashing pod:\n   kubectl logs -n duploservices-andy dummy-250527154358-865cfbb7db-9h6tm\n2. Describe the pod with config error:\n   kubectl describe pod -n duploservices-andy k8s-demo-7fc788997c-pwdv6\n\nThese commands will provide more details about the issues.",
    "data": {
        "Cmds": [
            {
                "Command": "kubectl describe pod -n duploservices-andy k8s-demo-7fc788997c-pwdv6",
                "Output": "",
                "execute": false
            },
            {
                "Command": "kubectl logs -n duploservices-andy dummy-250527154358-865cfbb7db-9h6tm",
                "Output": "",
                "execute": false
            }
        ],
        "executedCmds": [
            {
                "Command": "kubectl get pods -n duploservices-andy",
                "Output": "NAME                                        READY   STATUS                       RESTARTS          AGE\naws-6d9f676d48-jw2gb                        1/1     Running                      0                 6d17h\nchroma-vector-db-6ff6d5bf74-4dzvb           1/1     Running                      0                 6d17h\ncompliance-soc2-fb8487595-nm4xq             1/1     Running                      0                 6d17h\ndummy-250527154358-865cfbb7db-9h6tm         1/2     CrashLoopBackOff             867 (5m4s ago)    3d2h\necs-to-eks-poc-7899fccddd-bmqc8             1/1     Running                      0                 10m\ngrafana-agent-7ccb67c59c-td9l7              1/1     Running                      0                 6d17h\nk8s-demo-7fc788997c-pwdv6                   0/1     CreateContainerConfigError   0                 3d9h\nk8s-dummy-250527160138-66db598d69-xzg4d     2/2     Running                      866 (5m13s ago)   3d2h\nk8s-f74bcd594-52lxh                         1/1     Running                      0                 6d17h\nkubernetes-agent-59f5c8d76d-gg72m           1/1     Running                      0                 46h\ntest-7b568d7988-6wsz7                       1/1     Running                      0                 4d20h\ntest-7b568d7988-q8kb5                       1/1     Running                      0                 4d6h\nvectordb-duplo-managed-db-6655b8ccd-v8sjk   1/1     Running                      0                 4d17h",
                "execute": true
            }
        ]
    },
    "thread_id": "optional-thread-id-for-conversation-context"
}
```

- If no `thread_id` is provided, a new conversation thread will be created
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
  "content": "Check for failed pods in kube-system namespace",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

- "Why is my deployment not scaling in the production namespace?" with default kubeconfig and anthropic token:
```json
{
  "content": "Why is my deployment not scaling in the production namespace?",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": []
  }
}
```

- "Show recent events in the default namespace" with custom kubeconfig and anthropic token:
```json
{
  "content": "Show recent events in the default namespace",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

- "List all pods with high restart counts" with default kubeconfig and anthropic token:
```json
{
  "content": "List all pods with high restart counts",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": []
  }
}
```

- "Diagnose why my StatefulSet is stuck" with custom kubeconfig and anthropic token:
```json
{
  "content": "Diagnose why my StatefulSet is stuck",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
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

## License

MIT
