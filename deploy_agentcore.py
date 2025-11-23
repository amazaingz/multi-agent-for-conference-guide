
from bedrock_agentcore_starter_toolkit import Runtime
import boto3
from tools.logger_config import get_logger

logger = get_logger(__name__)

# 获取当前 AWS 区域
region = boto3.session.Session().region_name
logger.info(f"部署区域: {region}")

# 初始化 Runtime
agentcore_runtime = Runtime()

# 配置并部署
logger.info("开始配置和部署...")
config_response = agentcore_runtime.configure(
    entrypoint="agentcore_runtime_main.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name="reinvent_attendee_guide_agent"
)

logger.info("开始部署 (这可能需要几分钟)...")
launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)

logger.info("=" * 80)
logger.info("✓ 部署成功!")
logger.info("=" * 80)
logger.info(f"AgentCore Runtime ARN: {launch_result.agent_arn}")
logger.info("=" * 80)
logger.info("\n请将以下 ARN 更新到 config/bedrock_config.py 中:")
logger.info(f'AGENTCORE_RUNTIME_ARN = "{launch_result.agent_arn}"')
logger.info("=" * 80)

# 检查状态
import time
logger.info("\n检查状态...")
status_response = agentcore_runtime.status()
status = status_response.endpoint['status']

end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
while status not in end_status:
    logger.info(f"状态: {status} - 等待中...")
    time.sleep(10)
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']

if status == 'READY':
    logger.info("✓ AgentCore Runtime 已就绪!")
else:
    logger.warning(f"⚠ 状态: {status}")

# 自动更新 config/bedrock_config.py 中的 ARN
config_file = "config/bedrock_config.py"
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并替换 AGENTCORE_RUNTIME_ARN
    import re
    pattern = r'AGENTCORE_RUNTIME_ARN = ".*?"'
    replacement = f'AGENTCORE_RUNTIME_ARN = "{launch_result.agent_arn}"'
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"✓ 已自动更新 {config_file} 中的 AGENTCORE_RUNTIME_ARN")
    else:
        logger.warning(f"⚠ 未找到 AGENTCORE_RUNTIME_ARN，请手动添加")
except Exception as e:
    logger.error(f"✗ 更新配置文件失败: {str(e)}")
    logger.info(f"请手动将以下 ARN 添加到 {config_file}:")
    logger.info(f'AGENTCORE_RUNTIME_ARN = "{launch_result.agent_arn}"')

print("\n" + "=" * 80)
print("✓ 部署完成!")
print(f"ARN: {launch_result.agent_arn}")
print(f"已自动更新到 {config_file}")
print("=" * 80)
