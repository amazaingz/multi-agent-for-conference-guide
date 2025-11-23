from tools.logger_config import get_logger
from bedrock_agentcore.memory import MemoryClient
from config.bedrock_config import AWS_REGION

logger = get_logger(__name__)


def create_memory(memory_name: str) -> None:

    try:
        client = MemoryClient(region_name=AWS_REGION)
        memory = client.create_memory_and_wait(
            name=memory_name,
            strategies=[
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "UserPreference",
                        "namespaces": ["/users/{actorId}"],
                    }
                }
            ],
        )
        logger.info(
            f"Successfully created AgentCore Memory with ID: {memory.get('id')}"
        )
        logger.info(f"Memory details: {memory}")
    except Exception as e:
        logger.info(f"Error creating AgentCore Memory: {e}")


if __name__ == "__main__":
    create_memory("memory22")
