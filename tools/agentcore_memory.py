from config.bedrock_config import BEDROCK_AGENTCORE_MEMORY_ID, AWS_REGION
from bedrock_agentcore.memory import MemoryClient
from typing import Tuple, List


def update_memory(user_id: str, message: Tuple[str, str]) -> None:
    params = {
        "memory_id": BEDROCK_AGENTCORE_MEMORY_ID,
        "actor_id": f"user_{user_id}",
        "session_id": f"session_user_{user_id}",
        "messages": [message],
    }

    memory_client = MemoryClient(region_name=AWS_REGION)
    response = memory_client.create_event(**params)
