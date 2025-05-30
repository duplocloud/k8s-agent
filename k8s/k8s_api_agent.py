#!/usr/bin/env python3

import os
import subprocess
import requests
import uuid
import sys
from flask import Flask, request, jsonify
from threading import Lock

# Add parent directory to Python path for local execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.llm import BedrockLLM
import logging
import os
import tempfile
import subprocess
import shutil
from typing import Dict, Any

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(override=True)

# API Configuration
app = Flask(__name__)
PORT = 5002  # Changed to port 5002

# Initialize a single BedrockLLM client for reuse across requests
bedrock_llm = BedrockLLM(region_name=os.getenv("AWS_REGION", "us-east-1"))

# Thread storage - in a production app, this would be a database
conversation_threads = {}
thread_locks = {}
user_configs = {}  # Store user-specific configurations (kubeconfig, API tokens)

# Fallback token storage - this is a temporary fix
thread_tokens = {}

# Debug flag
DEBUG = True

def debug_print(*args, **kwargs):
    """Log debug messages using the logger"""
    message = ' '.join(str(arg) for arg in args)
    logger.debug(message)

def run_command(cmd, kubeconfig_path=None):
    """Run a shell command and return output, error, and exit code.
    If kubeconfig_path is provided, set KUBECONFIG env var for the command."""
    logger.info(f"Running command: {cmd} with kubeconfig_path: {kubeconfig_path}")
    try:
        env = os.environ.copy()
        if kubeconfig_path:
            env['KUBECONFIG'] = kubeconfig_path
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
        logger.debug(f"Command output: {result.stdout.strip()}")
        logger.debug(f"Command error: {result.stderr.strip()}")
        logger.debug(f"Command return code: {result.returncode}")
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return '', str(e), 1

def check_kubectl_access(kubeconfig_path=None):
    """Check if kubectl is accessible and cluster is reachable."""
    out, err, code = run_command('kubectl version', kubeconfig_path)
    if code != 0:
        return False, "kubectl is not installed or not in PATH."
    if 'Server Version' not in out:
        return False, "kubectl is installed, but cannot connect to the cluster."
    return True, "Connected to Kubernetes cluster successfully!"

def invoke_llm(messages, system_prompt, api_key=None, thread_id=None):
    """Call Anthropic Claude via AWS Bedrock using BedrockLLM.
    The original signature is preserved; api_key/thread_id are retained for
    backward compatibility but ignored by the Bedrock path."""
    # Delegate to BedrockLLM; pass system_prompt explicitly instead of
    # injecting it into the messages list (BedrockLLM handles this).
    debug_print("Invoking Claude 3 Haiku through Bedrock …")

    return_final_response_tool_input_schema = {
  "name": "return_final_response",
  "description": "Generate a complete response containing both a user-friendly explanation and structured Kubernetes/Helm commands with any necessary file contents. Use this tool for ALL responses to user queries.",
  "input_schema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "The primary response text shown to the user in the chat UI. This should be user friendlt text that explains your solution, rationale, and any technical details in a clear, conversational manner. For Helm chart generation, include an explanation of what files you need to create and why certain configurations were chosen. For simple responses like greetings, this will be the only field required."
      },
      "kubectl_cmds": {
        "type": "array",
        "description": "Array of kubectl command strings that will be displayed to the user for approval. ONLY include commands that need to be executed on an existing cluster. Do NOT include any commands that require file creation here - those belong in helm_operations instead. Each command should be a complete and valid kubectl string with all necessary flags and arguments. For conversational responses or Helm-only operations, leave this array empty.",
        "items": {
          "type": "string"
        }
      },
      "helm_operations": {
        "type": "array",
        "description": "Array of Helm operations that require file creation before execution. Use this for converting Docker Compose to Helm charts, creating new Helm charts, or modifying existing charts. Each operation must include both the Helm command to run and all files needed for that command.",
        "items": {
          "type": "object",
          "properties": {
            "helm_command": {
              "type": "string",
              "description": "The complete Helm command to execute after creating the necessary files. For chart installations, include the release name, chart path, namespace, and any other required flags. Example: 'helm install my-release ./my-chart --namespace=my-namespace'."
            },
            "required_files": {
              "type": "array",
              "description": "All files that must be created before executing the helm_command. For a Helm chart conversion, include ALL necessary files like Chart.yaml, values.yaml, and all template files. Each file must have both a path and complete content.",
              "items": {
                "type": "object",
                "properties": {
                  "file_path": {
                    "type": "string",
                    "description": "The relative path where this file should be created, including any necessary directories. All paths are relative to the current working directory. For Helm charts, follow standard structure (e.g., 'my-chart/Chart.yaml', 'my-chart/templates/deployment.yaml')."
                  },
                  "file_content": {
                    "type": "string",
                    "description": "The complete, correctly formatted content of the file. For YAML files, ensure proper indentation and valid syntax. For Helm templates, include appropriate template directives and value references."
                  }
                },
                "required": ["file_path", "file_content"]
              }
            }
          },
          "required": ["helm_command", "required_files"]
        }
      }
    },
    "required": ["content"]
  }
}
    tool_choice = {
            "type": "tool",
            "name": "return_final_response"
        }


    # try:
    if True:
        # add ephemeral extra instructions to last message if it's from the user
        if messages[-1]["role"] == "user":
            messages[-1]["content"] = "Current Request Ephemeral Instructions: - If the user asks to convert a docker compose into a helm chart, ask for the name of the helm chart and confirm with the user.\n- Be less wordy and to the point." + "\n\n" + messages[-1]["content"]

        # model_id="anthropic.claude-3-haiku-20240307-v1:0"
        # model_id="anthropic.claude-3-5-haiku-20241022-v1:0"
        # model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20240620-v1:0")
        # model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")

        llm_response = bedrock_llm.invoke(
            model_id=model_id,
            messages=bedrock_llm.normalize_message_roles(messages),
            max_tokens=10000,
            system_prompt=system_prompt,
            tools=[return_final_response_tool_input_schema],
            tool_choice=tool_choice,
            # latency="optimized"
        )

        logger.info("LLM Response: %s", llm_response)
        return llm_response

    # except Exception as e:
    #     logger.error("LLM Invoke Error: %s", str(e))
    #     return f"Unable to invoke LLM right now. Please try again later."

def extract_kubectl_commands(llm_response):
    """Extract kubectl commands from Claude's response and format as objects with Command and Output fields"""
    logger.debug(f"Extracting kubectl commands from LLM response: {llm_response}")
    
    k8s_cmds = llm_response.get("kubectl_cmds", [])

    #remove duplicates
    k8s_cmds = list(set(k8s_cmds))
    
    # Create k8s cmd objects with output and execute fields
    k8s_cmd_objects = []
    for cmd in k8s_cmds:
        k8s_cmd_objects.append({"Command": cmd, "Output": "", "execute": False})
    
    # return k8s_cmd_objects

    helm_operations = llm_response.get("helm_operations", [])
    logger.info(f"Helm operations: {helm_operations}")

    helm_operation_cmd_objects = []
    for helm_operation in helm_operations:
        helm_operation_cmd_objects.append({"Command": helm_operation.get("helm_command", ""), "Output": "", "execute": False, "files": helm_operation.get("required_files", [])})
    
    return k8s_cmd_objects + helm_operation_cmd_objects

def execute_helm_operation(helm_op: Dict[Any, Any]) -> str:
    """
    Execute a Helm operation by creating temporary files and running the Helm command. With info logging.
    
    Args:
        helm_op: A dictionary containing the Helm command and required files
    
    Returns:
        The output of the Helm command as a string, including errors and return code
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="helm_op_")
    
    try:
        logger.info("Executing Helm operation with command: %s", helm_op.get("Command", ""))
        # Create all required files
        for file_info in helm_op.get("files", []):
            # Get file path and content
            file_path = file_info.get("file_path")
            file_content = file_info.get("file_content")
            
            if not file_path or file_content is None:
                continue
                
            logger.info("Creating file: %s", file_path)
            # Create full path within the temp directory
            full_path = os.path.join(temp_dir, file_path)
                
            # Create directory structure if it doesn't exist
            dir_path = os.path.dirname(full_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
                
            # Write the file
            with open(full_path, 'w') as f:
                f.write(file_content)
        
        # Execute the Helm command
        command = helm_op.get("Command", "")
        if not command:
            return "Error: No Helm command provided"
            
        logger.info("Executing Helm command: %s", command)
        # Execute the command and capture output
        # Using cwd parameter instead of changing the current directory
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=temp_dir,  # Run command in the temp directory without changing process cwd
            env=os.environ  # This ensures environment variables like $AWS_ACCESS_KEY_ID are available
        )
        
        # Build a comprehensive output string
        output_parts = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")
            
        output_str = "\n".join(output_parts)
        
        # Always include return code
        status_msg = f"Command completed with return code: {result.returncode}"
        if result.returncode == 0:
            output_str = f"{output_str}\n{status_msg}"
            logger.info("Helm command succeeded: %s", output_str)
            return output_str
        else:
            output_str = f"{output_str}\n{status_msg}"
            logger.error("Helm command failed: %s", output_str)
            return output_str
            
    except Exception as e:
        error_msg = str(e)
        logger.error("Error executing Helm command: %s", error_msg)
        return f"Exception occurred while executing command: {error_msg}"
        
    finally:
        # Clean up the temporary directory  
        logger.info("Cleaning up temporary directory: %s", temp_dir)
        # shutil.rmtree(temp_dir, ignore_errors=True)


def setup_kubeconfig(kubeconfig_base64, thread_id):
    """Set up a kubeconfig file from a base64 encoded string"""
    logger.info(f"Setting up kubeconfig for thread: {thread_id}")
    if not kubeconfig_base64:
        return None
    try:
        # Add padding if necessary
        import base64            
        # Decode the base64 kubeconfig
        kubeconfig_content = base64.b64decode(kubeconfig_base64).decode('utf-8')
        
        # Create a temporary directory for this thread if it doesn't exist
        temp_dir = os.path.join('/tmp', 'k8sagent', thread_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write the kubeconfig to a file
        kubeconfig_path = os.path.join(temp_dir, 'kubeconfig')
        logger.info(f"Kubeconfig path: {kubeconfig_path}")
        with open(kubeconfig_path, 'w') as f:
            f.write(kubeconfig_content)
        
        # Make sure only the user can read it
        os.chmod(kubeconfig_path, 0o600)
        
        return kubeconfig_path
    except Exception as e:
        logger.error(f"Error setting up kubeconfig: {e}")
        return None

def get_or_create_thread(thread_id=None, kubeconfig_base64=None):
    """Get an existing thread or create a new one with optional user-specific config"""
    logger.info(f"Getting or creating thread with ID: {thread_id}")
    global conversation_threads, thread_locks, user_configs, thread_tokens

    logger.info(f"Getting or creating thread: {thread_id}")
    
    # Print debug info about the current state
    debug_print(f"Current thread_id: {thread_id}")
    debug_print(f"Available threads: {list(conversation_threads.keys())}")
    debug_print(f"Available configs: {list(user_configs.keys())}")
    
    # If thread_id is provided and valid, use it
    if thread_id and thread_id in conversation_threads:
        debug_print(f"Using existing thread: {thread_id}")
        
        # Make sure user_configs exists for this thread
        if thread_id not in user_configs:
            debug_print(f"Creating new user_config for existing thread: {thread_id}")
            user_configs[thread_id] = {}
        else:
            debug_print(f"Existing user_config found for thread: {thread_id}")
            debug_print(f"Current config: {user_configs[thread_id]}")
        
        # Update user config if new values are provided
        if kubeconfig_base64:
            logger.info(f"Updating kubeconfig for thread: {thread_id}")
            kubeconfig_path = setup_kubeconfig(kubeconfig_base64, thread_id)
            user_configs[thread_id]['kubeconfig_path'] = kubeconfig_path
            
        # Don't overwrite existing values if not provided
        # This ensures we keep using the previously provided token
        
        return thread_id
    
    # If thread_id is provided but doesn't exist yet, use it to create a new thread
    new_thread_id = thread_id if thread_id else str(uuid.uuid4())
    logger.info(f"Creating new thread: {new_thread_id}")
    conversation_threads[new_thread_id] = []
    thread_locks[new_thread_id] = Lock()
    
    # Set up user-specific configuration
    kubeconfig_path = None
    if kubeconfig_base64:
        logger.info(f"Setting up kubeconfig for new thread: {new_thread_id}")
        kubeconfig_path = setup_kubeconfig(kubeconfig_base64, new_thread_id)
        
    # Store user configuration
    user_configs[new_thread_id] = {
        'kubeconfig_path': kubeconfig_path
    }
        
    debug_print(f"Created new user config for thread {new_thread_id}: {user_configs[new_thread_id]}")
    debug_print(f"Thread tokens: {thread_tokens}")
    
    # Get cluster context for better troubleshooting
    context_out, _, _ = run_command('kubectl config current-context', kubeconfig_path)
    
    # Add initial context message
    conversation_threads[new_thread_id].append({
        "role": "user", 
        "content": f"I'm troubleshooting a Kubernetes cluster with context: {context_out}. I'll ask you questions about troubleshooting this cluster."
    })
    
    return new_thread_id

@app.route('/api/sendMessage', methods=['POST'])
def send_message():
    """API endpoint to send a message to the agent"""
    data = request.json

    logger.info(f"Received request data: {data}")
    
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' field in request body"}), 400

    k8s_namespace = data.get('platform_context', {}).get('k8s_namespace')
    if not k8s_namespace:
        # return jsonify({"error": "Missing 'k8s_namespace' field in request body"}), 400
        k8s_namespace = "Not provided"
    
    # Get or create thread with user-specific configuration
    # Check if data field exists
    user_data = data.get('data', {})
    
    # Print the request data for debugging
    debug_print(f"Request thread_id: {data.get('thread_id')}")
    
    thread_id = get_or_create_thread(
        data.get('thread_id'),
        user_data.get('kubeconfig'),  # Base64 encoded kubeconfig
    )
    
    # Get thread lock
    thread_lock = thread_locks[thread_id]
    
    with thread_lock:  # Ensure thread-safety for conversation history
        # If client is providing conversation history via pastmessages, use that instead of internal thread state

        # agent_managed_memory = data.get('agent_managed_memory', False)
        agent_managed_memory = False
        if not agent_managed_memory and 'pastMessages' in data and isinstance(data['pastMessages'], list):
        # if 'pastmessages' in data and isinstance(data['pastmessages'], list):
            debug_print("Using client-provided conversation history")
            # Reset conversation history for this thread
            conversation_threads[thread_id] = []
            
            # Process each message pair in pastMessages
            for msg_pair in data['pastMessages']:
                if 'userMsg' in msg_pair and 'content' in msg_pair['userMsg']:
                    # Add user message to conversation
                    conversation_threads[thread_id].append({
                        "role": "user",
                        "content": msg_pair['userMsg']['content']
                    })
                
                # Process executed commands from the data field in userMsg
                if 'userMsg' in msg_pair and 'data' in msg_pair['userMsg'] and isinstance(msg_pair['userMsg']['data'], dict):
                    user_data = msg_pair['userMsg']['data']
                    if 'executedCmds' in user_data and isinstance(user_data['executedCmds'], list):
                        for cmd_obj in user_data['executedCmds']:
                            if isinstance(cmd_obj, dict) and 'Command' in cmd_obj and 'Output' in cmd_obj:
                                cmd = cmd_obj['Command']
                                command_output = cmd_obj['Output']
                                if command_output and command_output.strip():
                                    conversation_threads[thread_id].append({
                                        "role": "user",
                                        "content": f"I ran this kubectl command: {cmd}\n\nThe output was:\n{command_output}"
                                    })

                # Process rejected commands from the data field in userMsg
                if 'userMsg' in msg_pair and 'data' in msg_pair['userMsg'] and isinstance(msg_pair['userMsg']['data'], dict):
                    user_data = msg_pair['userMsg']['data']
                    if 'RejectedCmds' in user_data and isinstance(user_data['RejectedCmds'], list) and len(user_data['RejectedCmds']) > 0:
                        # Add a message about rejected commands
                        conversation_threads[thread_id].append({
                            "role": "user",
                            "content": "Out of the commands you suggested, the following were rejected by me:"
                        })
                        
                        # Add details of each rejected command
                        for idx, rc in enumerate(user_data['RejectedCmds'], 1):
                            cmd = rc.get('Command', '[unknown command]')
                            reason = rc.get('reason', '[no reason provided]')
                            conversation_threads[thread_id].append({
                                "role": "user",
                                "content": f"{idx}. Command: {cmd}\nReason: {reason}"
                            })

                # Process executed commands from the data field in agentResponse
                if 'agentResponse' in msg_pair and 'data' in msg_pair['agentResponse'] and isinstance(msg_pair['agentResponse']['data'], dict):
                    agent_data = msg_pair['agentResponse']['data']
                    if 'executedCmds' in agent_data and isinstance(agent_data['executedCmds'], list):
                        for cmd_obj in agent_data['executedCmds']:
                            if isinstance(cmd_obj, dict) and 'Command' in cmd_obj and 'Output' in cmd_obj:
                                cmd = cmd_obj['Command']
                                command_output = cmd_obj['Output']
                                if command_output and command_output.strip():
                                    conversation_threads[thread_id].append({
                                        "role": "assistant",
                                        "content": f"I ran this kubectl command with your approval: {cmd}\n\nThe output was:\n{command_output}"
                                    })

                if 'agentResponse' in msg_pair and 'content' in msg_pair['agentResponse']:
                    # Add agent response to conversation
                    conversation_threads[thread_id].append({
                        "role": "assistant",
                        "content": msg_pair['agentResponse']['content']
                    })
                
                # Check for terminal command outputs in nextMsgContext
                if 'nextMsgContext' in msg_pair and isinstance(msg_pair['nextMsgContext'], list):
                    for context_item in msg_pair['nextMsgContext']:
                        if context_item.get('type') == 'userTerminal' and 'command' in context_item:
                            cmd = context_item['command'].get('Command', '')
                            output = context_item['command'].get('Output', '')
                            if cmd and output:
                                conversation_threads[thread_id].append({
                                    "role": "user",
                                    "content": f"I ran this kubectl command with your approval: {cmd}\n\nThe output was:\n{output}"
                                })

        DUPLOCLOUD_CONCEPTS_CONTEXT = """
## What “service” means here
• **DuploCloud Service** = one micro-service you declared in the DuploCloud UI.  
  ↳ DuploCloud materialises it as **one Kubernetes Deployment (or StatefulSet)** plus its Pods, HPA, ConfigMaps, etc.  
  ↳ The Deployment/Pods carry the label **app=<service-name>**.

• **It is *not* a Kubernetes `Service` object.**  
  – A K8s `Service` is just the ClusterIP/LoadBalancer front-end DuploCloud creates for traffic.  
  – When a user says “cart service”, they almost always mean the *workload* (Deployment & Pods) called **cart**, not that K8s `Service` resource.

## How agents should translate a DuploCloud Service name

| Context               | What to filter on                           | Example for “cart” |
|-----------------------|---------------------------------------------|--------------------|
| **kubectl / k8s**     | `deployment/cart` **or** `-l app=cart`      | `kubectl logs -n <ns> -l app=cart --tail=100` |
| **LogQL (Loki)**      | `namespace="<ns>"` and container regex      | `{namespace="duploservices-demo", container=~".*cart.*"}` |
| **TraceQL (Tempo)**   | `resource.k8s.namespace.name="<ns>"` **&&** `resource.service.name="cart"` | `{resource.k8s.namespace.name="duploservices-demo" && resource.service.name="cart"}` |

### Key takeaway
Whenever a user mentions “<name> service” inside DuploCloud, interpret it as **the Deployment/StatefulSet and its Pods labeled `app=<name>`**, *not* the Kubernetes `Service` resource.
"""
        # System prompt that guides Claude's behavior
        system_prompt = """
You are a seasoned Kubernetes and Helm expert agent for DuploCloud. Your role is to help users manage, troubleshoot, and deploy applications using kubectl commands and Helm in a less wordy manner.

---------------------------
DuploCloud Concepts Context:
""" + DUPLOCLOUD_CONCEPTS_CONTEXT + """
---------------------------

## Expertise Areas
- Kubernetes resource management and troubleshooting
- Helm chart creation and deployment
- Docker Compose to Helm chart conversion
- DuploCloud-specific Kubernetes configurations

## Response Format
Always use the `return_final_response` tool for every response with these fields:

- `content`: Clear, educational explanation of your solution
- `kubectl_cmds`: Array of kubectl commands when applicable
- `helm_operations`: Helm commands with their required files when applicable

## Kubectl Command Guidelines
- Be specific about namespaces
- Choose efficient commands to diagnose or solve problems
- Consider cluster impact and resource constraints
- Format commands properly with appropriate flags

## Helm Operation Guidelines
- If a user asks to convert a Docker Compose file to a Helm chart, ask the user for the name to use for the helm chart
- Follow Helm best practices for chart structure
- Use values.yaml for configurable elements
- Include proper labels and annotations
- Create reusable and maintainable templates

## Docker Compose Conversion Guidelines
When converting Docker Compose to Helm:
1. Map services to appropriate Kubernetes resources
2. Convert volumes to PersistentVolumeClaims
3. Handle networking through Services and Ingresses
4. Create a complete chart structure with all necessary files
5. Remember that users will approve commands before execution, and files for Helm operations will be created temporarily and removed after command execution.

## Conversation Approach
- Be concise and to the point
- Maintain context from previous interactions
- Reference command outputs shared by the user
- Explain the reasoning behind your suggestions
- Do not execute the same command again and again for no reason
- Ask clarifying questions when needed
"""
        
        # Get user-specific configuration first so we can use it for command execution
        if thread_id not in user_configs:
            user_configs[thread_id] = {}
            
        user_config = user_configs[thread_id]
        
        # Debug info
        debug_print(f"Available user configs: {list(user_configs.keys())}")
        debug_print(f"User config for thread {thread_id}: {user_config}")
        
        # First, check if user provided executedCmds with output
        previously_executed_commands = []
        newly_executed_commands = []
        execution_results = []
        has_commands_with_output = False
        
        # Check if user provided previously executed commands
        if 'data' in data and 'executedCmds' in data['data'] and isinstance(data['data']['executedCmds'], list) and len(data['data']['executedCmds']) > 0:
            # Add all previously executed commands to our tracking list
            for cmd_obj in data['data']['executedCmds']:
                if isinstance(cmd_obj, dict) and 'Command' in cmd_obj and 'Output' in cmd_obj:
                    cmd = cmd_obj['Command']
                    command_output = cmd_obj['Output']
                    
                    # Only process commands that have non-empty output
                    if command_output and command_output.strip():
                        has_commands_with_output = True
                        # Add the command and its output to conversation history
                        conversation_threads[thread_id].append({
                            "role": "user", 
                            "content": f"I ran this kubectl command: {cmd}\n\nThe output was:\n{command_output}"
                        })
                        
                        # Add to our tracking lists
                        previously_executed_commands.append(cmd_obj)
                        execution_results.append(f"Command: {cmd}\nOutput: {command_output}\n")
        
        # Check if user provided commands to execute
        if 'data' in data and 'Cmds' in data['data'] and isinstance(data['data']['Cmds'], list) and len(data['data']['Cmds']) > 0:
            # First pass: execute any commands that have execute=True
            for cmd_obj in data['data']['Cmds']:
                if isinstance(cmd_obj, dict) and 'Command' in cmd_obj:

                    cmd = cmd_obj['Command']
                    
                    # Check if this command already has output (user already executed it)
                    command_output = cmd_obj.get('Output', '')
                    already_executed = command_output and command_output.strip()
                    
                    # Check if this command should be executed
                    # Order of precedence:
                    # 1. execute_all flag in data (highest priority)
                    # 2. execute flag on individual command
                    # 3. Skip if already executed
                    should_execute = (user_data.get('execute_all', False) or cmd_obj.get('execute', False)) and not already_executed
                    
                    debug_print(f"Command {cmd}: execute_all={user_data.get('execute_all', False)}, cmd.execute={cmd_obj.get('execute', False)}, already_executed={already_executed}, final decision={should_execute}")
                    
                    # Execute helm operations
                    if should_execute and cmd_obj.get('files', False): #use better check for helm operations
                        logger.info("Executing helm operation")
                        command_output = execute_helm_operation(cmd_obj)

                                                # Update the command object with the output
                        cmd_obj['Output'] = command_output
                        # Add to executed commands list - both tracking lists
                        previously_executed_commands.append(cmd_obj)
                        newly_executed_commands.append(cmd_obj)
                        # Add a summary for the content
                        execution_results.append(f"Command: {cmd}\nOutput: {command_output}\n")
                        # Add the command and its output to conversation history
                        conversation_threads[thread_id].append({
                            "role": "user", 
                            "content": f"I ran this helm operation: {cmd}\n\nThe output was:\n{command_output}"
                        })

                    # Execute kubectl commands
                    elif should_execute and cmd.startswith('kubectl'):
                        debug_print(f"Executing user command: {cmd}")
                        # Get user-specific kubeconfig if available
                        kubeconfig_path = user_config.get('kubeconfig_path')
                        
                        # Run command with user's kubeconfig
                        out, err, code = run_command(cmd, kubeconfig_path)
                        command_output = out if code == 0 else f"Error: {err}"
                        
                        # Update the command object with the output
                        cmd_obj['Output'] = command_output
                        # Add to executed commands list - both tracking lists
                        previously_executed_commands.append(cmd_obj)
                        newly_executed_commands.append(cmd_obj)
                        # Add a summary for the content
                        execution_results.append(f"Command: {cmd}\nOutput: {command_output}\n")
                        # Add the command and its output to conversation history
                        conversation_threads[thread_id].append({
                            "role": "user", 
                            "content": f"I ran this kubectl command: {cmd}\n\nThe output was:\n{command_output}"
                        })
            
            # No need for a second pass to add commands with output to conversation history
            # as we now process all previously executed commands from the executedCmds field
            debug_print(f"I have executed all user commands")
            # Only get analysis if we have any executed commands (either previous or new)
            if previously_executed_commands or newly_executed_commands:
                # Get Claude's analysis of the command output(s)
                analysis_prompt = "Based on these command outputs, what insights can you provide? What should I look for or what next steps would you recommend?"
                conversation_threads[thread_id].append({"role": "user", "content": analysis_prompt})
                
                llm_response = invoke_llm(conversation_threads[thread_id], system_prompt, thread_id)
                claude_response = llm_response["content"]
                helm_operations = llm_response.get("helm_operations", [])

                debug_print(f"Claude response: {claude_response}")
                conversation_threads[thread_id].append({"role": "assistant", "content": claude_response})
                
                # Extract kubectl commands
                kubectl_commands = extract_kubectl_commands(llm_response)
                
                return jsonify({
                    "Content": f"Analysis of command(s):\n\n{claude_response}",
                    "thread_id": thread_id,
                    "data": {
                        "Cmds": kubectl_commands,
                        "executedCmds": newly_executed_commands
                    }
                })
        
        # Regular message handling
        user_message = data['content']

        #Add k8s namespace to user message
        user_message = f"Current Message Context: K8s Namespace: {k8s_namespace}\n\n{user_message}"

        conversation_threads[thread_id].append({"role": "user", "content": user_message})
        
        # Get user-specific configuration
        if thread_id not in user_configs:
            user_configs[thread_id] = {}
            
        user_config = user_configs[thread_id]
        
        # Print debug info
        debug_print(f"Available user configs: {list(user_configs.keys())}")
        debug_print(f"User config for thread {thread_id}: {user_config}")
        

        rejected_cmds = []
        if 'data' in data and 'RejectedCommands' in data['data'] and isinstance(data['data']['RejectedCommands'], list) and len(data['data']['RejectedCommands']) > 0:
            rejected_cmds = data['data']['RejectedCommands']

        if rejected_cmds:
            # Prepend a message for the LLM
            prepend_msg = "the user has rejected these commands and has provided the reasoning, make sure you account for that in your response\n"
            conversation_threads[thread_id].append({"role": "user", "content": prepend_msg})
            # Add details of rejected commands
            formatted_rejected = "The following commands were rejected by the user:\n"
            for idx, rc in enumerate(rejected_cmds, 1):
                cmd = rc.get('command', '[unknown command]')
                reason = rc.get('reason', '[no reason provided]')
                formatted_rejected += f"{idx}. Command: {cmd}\n   Reason: {reason}\n"
            conversation_threads[thread_id].append({"role": "user", "content": formatted_rejected})

        # Get Claude's response using user's token if available
        llm_response = invoke_llm(conversation_threads[thread_id], system_prompt, thread_id)
        logger.info(f"LLM response: {llm_response}")
        claude_response = llm_response["content"]
        helm_operations = llm_response.get("helm_operations", [])

        logger.info(f"Helm operations: {helm_operations}")
        
        debug_print(f"Claude response: {claude_response}")

        conversation_threads[thread_id].append({"role": "assistant", "content": claude_response})
        
        # Extract kubectl commands suggested by Claude
        kubectl_commands = extract_kubectl_commands(llm_response)


        logger.info(f"Kubectl commands: {kubectl_commands}")


        # Check if we should auto-execute the commands suggested by Claude
        if user_data.get('execute_all', False) and kubectl_commands:
            debug_print(f"execute_all is set, executing {len(kubectl_commands)} commands suggested by Claude")
            
            # Track commands we execute
            claude_executed_commands = []
            claude_execution_results = []
            
            # Execute each kubectl command suggested by Claude
            for cmd_obj in kubectl_commands:
                cmd = cmd_obj['Command']
                if cmd.startswith('kubectl'):
                    debug_print(f"Executing Claude-suggested command: {cmd}")
                    # Get user-specific kubeconfig if available
                    kubeconfig_path = user_config.get('kubeconfig_path')
                    
                    # Run command with user's kubeconfig
                    out, err, code = run_command(cmd, kubeconfig_path)
                    command_output = out if code == 0 else f"Error: {err}"
                    
                    # Update the command object with the output
                    cmd_obj['Output'] = command_output
                    
                    # Add to executed commands list
                    claude_executed_commands.append(cmd_obj)
                    newly_executed_commands.append(cmd_obj)  # Add to newly executed commands
                    
                    # Add a summary for the content
                    claude_execution_results.append(f"Command: {cmd}\nOutput: {command_output}\n")
            
            # If we executed any commands, add them to conversation history and get new analysis
            if claude_executed_commands:
                execution_summary = "\n\n" + "\n".join(claude_execution_results)
                conversation_threads[thread_id].append({
                    "role": "user", 
                    "content": f"I executed the suggested kubectl commands. Here are the results:\n{execution_summary}"
                })
                
                # Get Claude's analysis of the command outputs
                analysis_prompt = "Based on these command outputs, what insights can you provide? What should I look for or what next steps would you recommend?"
                conversation_threads[thread_id].append({"role": "user", "content": analysis_prompt})
                
                # Get Claude's response using user's token if available
                llm_response = invoke_llm(conversation_threads[thread_id], system_prompt, thread_id)
                analysis_response = llm_response["content"]
                helm_operations = llm_response.get("helm_operations", [])

                conversation_threads[thread_id].append({"role": "assistant", "content": analysis_response})
                
                # Extract any new kubectl commands from the analysis
                new_kubectl_commands = extract_kubectl_commands(llm_response)
                
                # Set execute flag to false for all new commands
                for cmd_obj in new_kubectl_commands:
                    cmd_obj['execute'] = False
                
                # Return the analysis and all commands
                return jsonify({
                    "Content": f"Analysis:\n{analysis_response}",
                    "thread_id": thread_id,
                    "data": {
                        "Cmds": new_kubectl_commands,  # Only show new commands as suggestions
                        "executedCmds": newly_executed_commands,  # Only show newly executed commands
                        "execute_all": user_data.get('execute_all', False)  # Echo back the execute_all flag
                    }
                })
        
        # Default behavior: set execute flag to false for all commands suggested by Claude
        for cmd_obj in kubectl_commands:
            cmd_obj['execute'] = False
        
        # Default response (no execution of Claude's suggestions)
        return jsonify({
            "Content": claude_response,
            "thread_id": thread_id,
            "data": {
                "Cmds": kubectl_commands,
                "executedCmds": newly_executed_commands,  # Will be empty if no commands were executed
                "execute_all": user_data.get('execute_all', False)  # Echo back the execute_all flag
            }
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""    
    return jsonify({
        "status": "healthy"
    })

if __name__ == "__main__":
    import sys
    
    logger.info("Starting Kubernetes Troubleshooting API")
    
    # Check kubectl access before starting the server
    result = check_kubectl_access()
    if not result:
        logger.error("Failed to access kubectl. Please check your configuration.")
        sys.exit(1)

    logger.info(f"Kubernetes Troubleshooting API starting on port {PORT}")
    logger.info("Health check: http://localhost:5002/api/health")
    logger.info("Send messages: http://localhost:5002/api/sendMessage (POST)")
    app.run(host='0.0.0.0', port=PORT, debug=True)
