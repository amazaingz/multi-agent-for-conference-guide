## re:Invent 参会指南 Multi-Agent 系统

### 介绍
基于 Strands SDK 的 multi-agent 模式，使用 AWS Bedrock AgentCore Runtime、Memory、Bedrock Knowledge Base 等云原生 agent 基础设施实现的 re:Invent 参会智能助手系统。

### 1. 目的
旨在为 AWS re:Invent 参会者提供全方位的智能参会指南服务。该系统通过多个专业 Agent 协同工作，帮助参会者获取天气信息、美食推荐、议程规划、会后回顾等服务，提升参会体验。

### 2. 系统架构
本系统采用分层的多 Agent 架构，由用户接口层、应用逻辑层和数据存储层组成。

*   **用户接口层**: 支持 Web Service 接口（FastAPI），提供 JSON 和 Markdown 两种响应格式。
*   **应用逻辑层**:
    *   **总控 Agent (Supervisor)**: 作为系统的"大脑"，接收用户请求并智能路由到专业 Agent。支持并行调用多个子 Agent，主动行动而非反复询问。
    *   **记忆管理 Agent (Memory Agent)**: 基于 Bedrock AgentCore Memory 管理参会者的历史对话和偏好信息。
    *   **气象助手 (Weather Agent)**: 提供全球任意城市的实时天气和未来 16 天预报，支持穿衣建议。使用 Open-Meteo 免费 API，自动识别时区。
    *   **美食向导 (Dining Agent)**: 支持全球任意城市的餐厅搜索（OpenStreetMap API），对中国城市提供本地化推荐（大众点评、美团等平台建议）。
    *   **议程规划师 (Session Agent)**: 基于知识库检索，帮助规划参会议程，推荐相关 session、workshop、keynote。
    *   **会后回顾助手 (Recap Agent)**: 提供大会总结、新发布服务解读及中国行路演信息，并主动提供路演城市的天气和餐饮建议。
*   **数据存储层**: Bedrock Knowledge Base（知识库）、AgentCore Memory（对话历史）。

### 3. 工作流程
1. 用户发送请求，如果提供了 user id 则记录
2. Supervisor Agent 识别用户需求，**主动调用**相应的专业 Agent：
   - 天气、气温、穿衣建议 → 气象助手（支持未来 16 天预报）
   - 餐厅、美食、用餐推荐 → 美食向导（支持全球城市）
   - 议程、session、演讲、活动安排 → 议程规划师（基于知识库）
   - 会后总结、中国行路演、新品发布 → 会后回顾助手
3. 如果用户同时询问多个主题（如天气+餐饮+议程），系统会并行调用多个 Agent
4. 综合各专业 Agent 的结果，为用户提供完整的规划方案

#### 架构图
![架构图](./docs/agents-orchestrator.png)

### 4. 项目结构
```
├── main.py                    # FastAPI 服务入口（端口 8080/8081）
├── agents/
│   ├── supervisor.py          # 总控 Agent（max_tokens=8192）
│   ├── weather_agent.py       # 气象助手（Open-Meteo API，16天预报）
│   ├── dining_agent.py        # 美食向导（OpenStreetMap API）
│   ├── session_agent.py       # 议程规划师（知识库检索）
│   ├── memory_agent.py        # 记忆管理（AgentCore Memory）
│   ├── recap_agent.py         # 会后回顾助手
│   └── prompt_templates.py    # Agent 提示词模板
├── config/
│   ├── bedrock_config.py      # AWS Bedrock 配置
│   └── attendees.csv          # 参会者信息
├── tools/
│   ├── agentcore_memory.py    # AgentCore Memory 工具
│   └── logger_config.py       # 日志配置
├── docs/
│   ├── 2025_reInvent_Attendee Guide-CN.pdf  # 中国行参会指南
│   ├── dining_guide.md        # 餐饮指南（知识库）
│   ├── session_guide.md       # 议程指南（知识库）
│   └── weather_info.md        # 天气信息（知识库）
├── agentcore_tools/
│   └── invoke.py              # AgentCore 调用工具
└── test_weather_agent.py      # Agent 测试脚本
```

### 5. 测试 & 部署

#### 5.1 安装依赖
```bash
uv sync
```

#### 5.2 配置 AWS
确保运行环境已配置 IAM 角色权限。

```bash
export AWS_DEFAULT_REGION="us-west-2"
```

#### 5.3 创建 Knowledge Base
1. 上传 `docs/` 目录下的文档到 S3（包括 PDF 和 Markdown 文件）
2. 在 Bedrock Console 创建 Knowledge Base
3. 复制 KB ID

#### 5.4 创建 AgentCore Memory
```bash
python create_memory.py
```

#### 5.5 更新配置
编辑 `config/bedrock_config.py`:
```python
DEFAULT_KNOWLEDGE_BASE_ID = "your-kb-id"
BEDROCK_AGENTCORE_MEMORY_ID = "your-memory-id"
```

#### 5.6 本地运行
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

#### 5.7 测试示例

**综合规划（推荐）：**
```bash
# 一次性获取天气、餐饮、议程的完整规划
curl -X POST http://localhost:8080/invocations/markdown \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "我要参加 AWS re:Invent 中国行上海站，请帮我规划天气、餐饮和议程。我的用户id是user001"}}' \
  -o plan.md
```