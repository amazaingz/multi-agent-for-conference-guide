"""
Bedrock Configuration for Post-Sales Agent
Configure your AWS Bedrock Knowledge Base settings here
"""

# AWS Configuration
AWS_REGION = "us-east-1"  # Change to your region

# Bedrock Knowledge Base Configuration
# Replace with your actual Knowledge Base ID after creating it in AWS Console
DEFAULT_KNOWLEDGE_BASE_ID = "EAD0TENWWO"

# RAG Configuration
MAX_RAG_RESULTS = 5  # Number of documents to retrieve from knowledge base
MIN_RELEVANCE_SCORE = 0.2  # Minimum relevance score for results (降低阈值以获取更多结果)

# Bedrock Model Configuration
# Using Amazon Nova Pro for cost efficiency
BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"
MODEL_TEMPERATURE = 0.3
MODEL_TOP_P = 0.3

# Bedrock Agent Core Memory Configuration
# BEDROCK_AGENTCORE_MEMORY_ID = "memory_strands_test1-1VqKHU3EKq"
BEDROCK_AGENTCORE_MEMORY_ID = "memory22-uuH40yFOhd"

# Bedrock AgentCore Runtime Configuration
# 从部署后的 AgentCore Runtime 获取此 ARN
# 运行 04-agentcore-runtime-strands-deploy.ipynb 部署后，在输出中找到 Runtime ARN
AGENTCORE_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:605630858339:runtime/strands_claude_getting_started-VS3rt4EOF7"
