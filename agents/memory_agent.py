"""
Memory Agent - Manages attendee information and conversation history
"""

from strands import Agent, tool
from strands.models import BedrockModel
from agents.prompt_templates import memory_agent_system_prompt
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
from config.bedrock_config import (
    BEDROCK_MODEL_ID,
    BEDROCK_AGENTCORE_MEMORY_ID,
    AWS_REGION,
)
from tools.logger_config import get_logger

logger = get_logger(__name__)

bedrock_model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    temperature=0.3,
    top_p=0.3,
)


def init_agent(agent_name: str, user_id: str, session_id: str) -> Agent:
    provider = AgentCoreMemoryToolProvider(
        memory_id=BEDROCK_AGENTCORE_MEMORY_ID,
        actor_id=f"user_{user_id}",
        session_id=f"session_user_{user_id}",
        namespace=f"/users/user_{user_id}",
        region=AWS_REGION,
    )
    return Agent(
        name=agent_name,
        system_prompt=memory_agent_system_prompt,
        model=bedrock_model,
        tools=provider.tools,
    )


@tool
def process_attendee_info(user_id: str, session_id: str, query: str) -> str:
    """
    Process and manage attendee information using memory capabilities.

    Args:
        user_id: Attendee user id
        session_id: Current chat session id
        query: Query about attendee information

    Returns:
        Attendee history or confirmation of stored information
    """
    formatted_query = f"{query}"

    try:
        logger.info(
            f"Routed to Memory Agent: user_id:{user_id}, session_id:{session_id}, query:{query}"
        )
        agent = init_agent("Memory Agent", user_id, session_id)
        agent_response = agent(formatted_query)
        text_response = str(agent_response)
        logger.info(f"Memory agent response: {text_response}")
        
        if len(text_response) > 0:
            return text_response

        return "没有关于这个参会者的任何信息。"
    except Exception as e:
        logger.error(f"Error in memory agent: {str(e)}")
        return f"处理参会者信息时出错：{str(e)}"
