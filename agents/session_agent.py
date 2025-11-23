"""
Session Agent - Helps plan re:Invent agenda and recommends relevant sessions
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from agents.prompt_templates import session_agent_system_prompt
from config.bedrock_config import (
    BEDROCK_MODEL_ID,
    DEFAULT_KNOWLEDGE_BASE_ID,
    MAX_RAG_RESULTS,
    MIN_RELEVANCE_SCORE,
    AWS_REGION,
)
import uuid
from tools.logger_config import get_logger

logger = get_logger(__name__)

bedrock_model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    temperature=0.3,
    top_p=0.3,
)


@tool
def retrieve_session_info(query: str) -> dict:
    """
    Retrieve session and agenda information from knowledge base.

    Args:
        query: Session related query

    Returns:
        Dictionary containing session information
    """
    try:
        retrieve_response = retrieve.retrieve(
            {
                "toolUseId": str(uuid.uuid4()),
                "input": {
                    "text": query,
                    "score": MIN_RELEVANCE_SCORE,
                    "numberOfResults": MAX_RAG_RESULTS,
                    "knowledgeBaseId": DEFAULT_KNOWLEDGE_BASE_ID,
                    "region": AWS_REGION,
                },
            }
        )
        logger.info(f"Session retrieve_response: {retrieve_response}")
        return retrieve_response
    except Exception as e:
        logger.error(f"Error retrieving session info: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving session information: {str(e)}",
        }


def init_agent(agent_name: str) -> Agent:
    return Agent(
        name=agent_name,
        system_prompt=session_agent_system_prompt,
        model=bedrock_model,
        tools=[retrieve_session_info],
    )


@tool
def get_session_planning(query: str, user_id: str = None) -> str:
    """
    Process session planning queries and provide agenda recommendations.

    Args:
        query: Session planning question from the user
        user_id: Current user_id (optional)

    Returns:
        Session recommendations and agenda planning suggestions
    """
    formatted_query = f"请帮助规划 re:Invent 议程：{query}"

    try:
        logger.info("Routed to Session Agent")
        agent = init_agent("Session Agent")
        agent_response = agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            return text_response

        return "很抱歉，暂时无法提供议程规划建议。请稍后再试。"
    except Exception as e:
        logger.error(f"Error in session agent: {str(e)}")
        return f"处理议程规划时出错：{str(e)}"
