## re:Invent 参会指南 Multi-Agent 系统

### 介绍
基于 Strands SDK 的 multi-agent 模式，使用 AWS Bedrock AgentCore Runtime、Memory、Bedrock Knowledge Base 等云原生 agent 基础设施实现的 re:Invent 参会智能助手系统。

### 1.目的
旨在为 AWS re:Invent 参会者提供全方位的智能参会指南服务。该系统通过多个专业 Agent 协同工作，帮助参会者获取天气信息、美食推荐、议程规划等服务，提升参会体验。系统由一个总控 Agent 和三个专业 Agent（气象助手、美食向导、议程规划师）协同工作，为参会者提供无缝、高效的服务体验。

### 2.系统架构
本系统采用分层的多 Agent 架构，由用户接口层、应用逻辑层和数据存储层组成。Multi-Agent 位于应用逻辑层，通过协同工作来完成参会服务任务。

*   **用户接口层**: 支持 Web Service 接口的方式，暴露服务。
*   **应用逻辑层**:
    *   **总控 Agent (Supervisor)**: 作为系统的"大脑"，接收所有来自用户的请求，并将任务分发给不同的专业 agent。
    *   **记忆管理 Agent (Memory Agent)**: 管理参会者的历史对话和偏好信息。
    *   **气象助手 (Weather Agent)**: 提供 Las Vegas 当地天气信息和穿衣建议。
    *   **美食向导 (Dining Agent)**: 推荐会场周边餐厅和美食。
    *   **议程规划师 (Session Agent)**: 帮助规划参会议程，推荐相关 session。
*   **数据存储层**: 包括知识库、参会者信息数据库、议程数据库和对话历史记录。

### 3. 工作流程
1. 欢迎参会者，询问是否需要帮助
2. 如果是首次使用，询问参会者的 user id 以提供个性化服务
3. 根据参会者提供的 user id，使用 update_user_id 更新用户信息，并获取历史对话记录
4. 根据参会者的需求，智能路由到相应的专业 Agent：
   - 天气相关问题 → 气象助手
   - 餐饮美食问题 → 美食向导
   - 议程安排问题 → 议程规划师
5. 各专业 Agent 结合知识库提供专业建议
6. 持续跟踪参会者需求，提供个性化服务
#### 架构图
![架构图](./docs/agents-orchestrator.png)

### 4. 测试&部署
#### 4.1 Install Dependencies
```bash
uv sync
```

#### 4.2 Configure AWS
确保你的运行环境已经配置了 IAM 角色权限（通过 CloudFormation 部署时已自动配置）。
如果在本地开发，请确保已配置 AWS CLI 默认凭证或 IAM 角色。

```bash
# 可选：设置默认区域（如果未在 ~/.aws/config 中配置）
export AWS_DEFAULT_REGION="us-east-1"
```

#### 4.3 Create Knowledge Base
1. Upload documents to S3
2. Create KB in Bedrock Console
3. Copy KB ID

#### 4.4 Create Agentcore Memory
```bash
python create_memory.py
```

#### 4.5 Update Config
update parameters
Edit `config/bedrock_config.py`:
```python
KNOWLEDGE_BASE_ID = "your-actual-kb-id"
BEDROCK_AGENTCORE_MEMORY_ID = "your-memory-id"
```

#### 4.6 Run test
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```
```bash
curl -X POST http://localhost:8080/invocations   -H "Content-Type: application/json"   -d '{ "input": {"prompt": "你好，我想了解一下 re:Invent 期间 Las Vegas 的天气情况"}}' 
```
#### 4.7 Deploy to Bedrock Agentcore runtime

**方式一：自动化部署（推荐）**

运行部署脚本，自动创建和部署 AgentCore Runtime：

```bash
python deploy_to_agentcore.py
```

部署成功后，将输出的 `AGENTCORE_RUNTIME_ARN` 更新到 `config/bedrock_config.py` 中。

详细部署指南请参考：[DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md)

**方式二：手动部署**

参考官方文档：
https://strandsagents.com/latest/documentation/docs/user-guide/deploy/deploy_to_bedrock_agentcore/#option-b-custom-agent

#### 4.8 Test Deployed Agent

部署完成后，使用以下命令测试：

```bash
python agentcore_tools/invoke.py "你好，我想了解一下 re:Invent 期间 Las Vegas 的天气情况"
```
