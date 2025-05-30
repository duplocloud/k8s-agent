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

### How the Agent Works

1. **Initial Request**: You send a natural language query about your Kubernetes cluster
2. **Command Suggestions**: The agent analyzes your query and suggests appropriate kubectl commands in the `Cmds` array (with `execute: false`) 
3. **Command Approval**: You can approve these commands by sending them back in a new request with `execute: true`
4. **Command Execution**: The agent executes approved commands and returns results in the `executedCmds` array
5. **Analysis**: The agent analyzes the command outputs and suggests next steps
6. **Conversation Context**: The `thread_id` is used to maintain conversation context across multiple requests

### Request and Response Structure

Both requests and responses use a similar JSON structure:

- Requests use lowercase `content`, responses use uppercase `Content`
- Commands are managed through the `data` object containing `Cmds` and `executedCmds` arrays
- The `kubeconfig` field is placed inside the `data` object
- Each response includes a `thread_id` that should be included in subsequent requests

### Example Workflow

#### 1. Initial Request with Kubeconfig

```json
{
  "content": "List my pods in the duploservices-andy namespace",
  "thread_id": "optional-thread-id-for-conversation-context",
  "data": {
    "Cmds": [],
    "execute_all": false,
    "executedCmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content"
  }
}
```

> **Note:** The `kubeconfig` field inside the `data` object can be provided in the first message of the thread. It is optional. If provided, it will be used for this specific user/thread. If not provided, the system will use the default configuration. AWS credentials are automatically detected from environment variables or instance metadata when running in DuploCloud.

#### 2. Agent Response with Command Suggestions

```json
{
  "Content": "To list pods in the duploservices-andy namespace:\n\nkubectl get pods -n duploservices-andy\n\nThis will show all pods in the duploservices-andy namespace, their status, and other basic information.",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get pods -n duploservices-andy",
        "Output": "",
        "execute": false
      }
    ],
    "execute_all": false,
    "executedCmds": []
  },
  "thread_id": "conversation-thread-id"
}
```

#### 3. Approving Commands

To approve the suggested command, send it back with `execute: true`:

```json
{
  "content": "approved",
  "thread_id": "conversation-thread-id",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl get pods -n duploservices-andy",
        "Output": "",
        "execute": true
      }
    ],
    "execute_all": false,
    "executedCmds": []
  }
}
```

#### 4. Agent Response with Executed Commands and Analysis

```json
{
  "Content": "Analysis of command(s):\n\nBased on the output, there are two pods with issues:\n\n1. dummy-250527154358-865cfbb7db-9h6tm: In CrashLoopBackOff state\n2. k8s-demo-7fc788997c-pwdv6: Has CreateContainerConfigError\n\nNext steps:\n1. Check logs for the crashing pod\n2. Describe the pod with config error\n\nWould you like me to provide kubectl commands for these steps?",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl logs -n duploservices-andy dummy-250527154358-865cfbb7db-9h6tm",
        "Output": "",
        "execute": false
      },
      {
        "Command": "kubectl describe pod -n duploservices-andy k8s-demo-7fc788997c-pwdv6",
        "Output": "",
        "execute": false
      }
    ],
    "executedCmds": [
      {
        "Command": "kubectl get pods -n duploservices-andy",
        "Output": "NAME                                        READY   STATUS                       RESTARTS        AGE\naws-6d9f676d48-jw2gb                        1/1     Running                      0               6d18h\nchroma-vector-db-6ff6d5bf74-4dzvb           1/1     Running                      0               6d18h\ncompliance-soc2-fb8487595-nm4xq             1/1     Running                      0               6d18h\ndummy-250527154358-865cfbb7db-9h6tm         1/2     CrashLoopBackOff             873 (61s ago)   3d3h\necs-to-eks-poc-7899fccddd-hr7dd             1/1     Running                      0               79s\ngrafana-agent-7ccb67c59c-td9l7              1/1     Running                      0               6d18h\nk8s-demo-7fc788997c-pwdv6                   0/1     CreateContainerConfigError   0               3d10h\nk8s-dummy-250527160138-66db598d69-xzg4d     1/2     CrashLoopBackOff             871 (67s ago)   3d3h\nk8s-f74bcd594-52lxh                         1/1     Running                      0               6d18h\nkubernetes-agent-59f5c8d76d-gg72m           1/1     Running                      0               46h\ntest-7b568d7988-6wsz7                       1/1     Running                      0               4d21h\ntest-7b568d7988-q8kb5                       1/1     Running                      0               4d6h\nvectordb-duplo-managed-db-6655b8ccd-v8sjk   1/1     Running                      0               4d18h",
        "execute": true
      }
    ]
  },
  "thread_id": "conversation-thread-id"
}
```

#### 5. Sending Externally Executed Commands

You can also send commands you executed yourself outside the agent:

```json
{
  "content": "What is the issue with my pods?",
  "thread_id": "new-thread-id",
  "data": {
    "Cmds": [],
    "execute_all": false,
    "executedCmds": [
      {
        "Command": "kubectl get pods -n duploservices-andy",
        "Output": "NAME                                        READY   STATUS                       RESTARTS        AGE\naws-6d9f676d48-jw2gb                        1/1     Running                      0               6d18h\nchroma-vector-db-6ff6d5bf74-4dzvb           1/1     Running                      0               6d18h\ncompliance-soc2-fb8487595-nm4xq             1/1     Running                      0               6d18h\ndummy-250527154358-865cfbb7db-9h6tm         1/2     CrashLoopBackOff             873 (61s ago)   3d3h\necs-to-eks-poc-7899fccddd-hr7dd             1/1     Running                      0               79s\ngrafana-agent-7ccb67c59c-td9l7              1/1     Running                      0               6d18h\nk8s-demo-7fc788997c-pwdv6                   0/1     CreateContainerConfigError   0               3d10h\nk8s-dummy-250527160138-66db598d69-xzg4d     1/2     CrashLoopBackOff             871 (67s ago)   3d3h\nk8s-f74bcd594-52lxh                         1/1     Running                      0               6d18h\nkubernetes-agent-59f5c8d76d-gg72m           1/1     Running                      0               46h\ntest-7b568d7988-6wsz7                       1/1     Running                      0               4d21h\ntest-7b568d7988-q8kb5                       1/1     Running                      0               4d6h\nvectordb-duplo-managed-db-6655b8ccd-v8sjk   1/1     Running                      0               4d18h",
        "execute": true
      }
    ]
  }
}
```

#### 6. Agent Response with Analysis and Next Steps

```json
{
  "Content": "Based on the output, there are three main issues:\n\n1. Pod \"dummy-250527154358-865cfbb7db-9h6tm\" is in CrashLoopBackOff state.\n2. Pod \"k8s-dummy-250527160138-66db598d69-xzg4d\" is also in CrashLoopBackOff state.\n3. Pod \"k8s-demo-7fc788997c-pwdv6\" has a CreateContainerConfigError.\n\nTo investigate further, we need to check the logs and describe these pods.",
  "data": {
    "Cmds": [
      {
        "Command": "kubectl logs -n duploservices-andy dummy-250527154358-865cfbb7db-9h6tm",
        "Output": "",
        "execute": false
      },
      {
        "Command": "kubectl logs -n duploservices-andy k8s-dummy-250527160138-66db598d69-xzg4d",
        "Output": "",
        "execute": false
      },
      {
        "Command": "kubectl describe pod -n duploservices-andy k8s-demo-7fc788997c-pwdv6",
        "Output": "",
        "execute": false
      }
    ],
    "execute_all": false,
    "executedCmds": []
  },
  "thread_id": "new-thread-id"
}
```

### Additional Request Options

#### Using Auto-Execute for All Commands

You can set `execute_all: true` to automatically execute all commands suggested by the agent:

```json
{
  "content": "Check for failed pods in all namespaces",
  "thread_id": "optional-thread-id",
  "data": {
    "Cmds": [],
    "kubeconfig": "base64-encoded-kubeconfig-content",
    "execute_all": true
  }
}
```

### Key Points

- **Thread ID**: Always included in responses and should be used in subsequent requests for conversation continuity
- **Command Approval Flow**: The agent suggests commands (`Cmds` with `execute: false`) → You approve them (set `execute: true`) → Agent executes and returns results
- **External Command Results**: Commands executed outside the agent can be sent via the `executedCmds` array
- **Kubeconfig**: Always include inside the `data` object, not at the top level
- **Analysis**: The agent provides analysis of command outputs and suggests next steps

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
