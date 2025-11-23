import boto3
import json
import sys
import uuid
from config.bedrock_config import AWS_REGION, AGENTCORE_RUNTIME_ARN

# Get specific argument
if len(sys.argv) > 1:
    print(f"argv:${sys.argv[1]}")
else:
    print(f"argv:None")
    exit()

# 生成唯一的会话 ID（或使用固定 ID 来维护对话历史）
session_id = str(uuid.uuid4())

client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
payload = json.dumps({"input": {"prompt": sys.argv[1]}})

response = client.invoke_agent_runtime(
    agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
    runtimeSessionId=session_id,  # 使用唯一会话 ID
    payload=payload,
    qualifier="DEFAULT",
)
response_body = response["response"].read()
response_data = json.loads(response_body)
print("Agent Response:", response_data)
