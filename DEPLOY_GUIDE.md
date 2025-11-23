# 部署到 Bedrock AgentCore Runtime 指南

## 前提条件

1. **AWS 凭证配置**
   - 确保已配置 AWS CLI 凭证或 IAM 角色
   - 需要有创建 ECR、IAM 角色、CodeBuild 项目的权限

2. **已创建的资源**
   - Knowledge Base (已在 `bedrock_config.py` 中配置)
   - AgentCore Memory (已在 `bedrock_config.py` 中配置)

## 部署步骤

### 1. 安装依赖

```bash
uv sync
# 或者
pip install -r requirements.txt
```

### 2. 运行部署脚本

```bash
python deploy_to_agentcore.py
```

部署过程大约需要 3-5 分钟，包括：
- 创建 ECR 仓库
- 创建 IAM 执行角色
- 使用 CodeBuild 构建容器镜像
- 部署到 AgentCore Runtime

### 3. 更新配置

部署成功后，脚本会输出 AgentCore Runtime ARN，类似：

```
AGENTCORE_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/reinvent_attendee_guide_agent-XXXXXXXXX"
```

将这个 ARN 复制到 `config/bedrock_config.py` 文件中，替换现有的 `AGENTCORE_RUNTIME_ARN` 值。

### 4. 测试部署

使用 `agentcore_tools/invoke.py` 测试部署的 agent：

```bash
python agentcore_tools/invoke.py "你好，我想了解一下 re:Invent 期间 Las Vegas 的天气情况"
```

## 文件说明

- **agentcore_runtime_main.py**: AgentCore Runtime 的入口文件，包含 agent 初始化和请求处理逻辑
- **deploy_to_agentcore.py**: 自动化部署脚本
- **requirements.txt**: 部署所需的 Python 依赖
- **agentcore_tools/invoke.py**: 调用已部署 agent 的测试脚本

## 架构说明

部署后的架构：

```
用户请求
    ↓
AgentCore Runtime (托管服务)
    ↓
agentcore_runtime_main.py (入口)
    ↓
SupervisorAgent (总控 Agent)
    ↓
├── WeatherAgent (天气助手)
├── DiningAgent (美食向导)
└── SessionAgent (议程规划师)
    ↓
Knowledge Base + Memory
```

## 可观测性

部署后可以在 AWS Console 中查看：

1. **CloudWatch Logs**: 查看 agent 运行日志
   - 日志组: `/aws/bedrock-agentcore/runtimes/reinvent_attendee_guide_agent-XXXXX-DEFAULT`

2. **CloudWatch APM**: 查看性能指标和追踪
   - 导航到: CloudWatch → GenAI Observability → Agent Core

3. **X-Ray**: 查看分布式追踪
   - 可以看到完整的请求链路

## 更新部署

如果修改了代码，重新运行部署脚本即可：

```bash
python deploy_to_agentcore.py
```

脚本会自动更新现有的 AgentCore Runtime。

## 故障排查

### 部署失败

1. 检查 AWS 凭证是否正确配置
2. 检查 IAM 权限是否足够
3. 查看 CodeBuild 日志了解构建错误

### Agent 调用失败

1. 检查 `AGENTCORE_RUNTIME_ARN` 是否正确配置
2. 检查 Knowledge Base ID 和 Memory ID 是否有效
3. 查看 CloudWatch Logs 中的错误信息

### 会话管理

- 每次调用会生成新的 session_id
- 如果需要保持对话历史，可以在调用时传递相同的 `runtimeSessionId`

## 成本优化

- AgentCore Runtime 按使用量计费
- 使用 Amazon Nova Pro 模型以降低成本
- 可以配置自动扩展策略
