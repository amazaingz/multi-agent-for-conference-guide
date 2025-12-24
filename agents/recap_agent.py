"""
Recap Agent - Provides post-conference summaries and roadshow information using Knowledge Base + Weather/Dining Tools
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from agents.prompt_templates import recap_agent_system_prompt
from agents.weather_agent import get_realtime_weather
from agents.dining_agent import search_nearby_restaurants
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
    max_tokens=4096,
)


@tool
def retrieve_recap_info(query: str) -> dict:
    """
    Retrieve conference recap, summary from knowledge base.
    Roadshow info might be absent or limited here.

    Args:
        query: Query related to conference summary

    Returns:
        Dictionary containing retrieved information
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
        logger.info(f"Recap retrieve_response: {retrieve_response}")
        return retrieve_response
    except Exception as e:
        logger.error(f"Error retrieving recap info: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving recap information: {str(e)}",
        }


def init_agent(agent_name: str) -> Agent:
    return Agent(
        name=agent_name,
        system_prompt=recap_agent_system_prompt,
        model=bedrock_model,
        tools=[retrieve_recap_info, get_realtime_weather, search_nearby_restaurants],
    )


@tool
def get_recap_info(query: str, user_id: str = None) -> str:
    """
    Process queries related to post-conference summaries, new product releases, and roadshows.
    Integrates Knowledge Base for summaries and real-time tools for roadshow logistics (weather/dining).

    Args:
        query: User's query about conference recap, new releases, or roadshows
        user_id: Current user_id (optional)

    Returns:
        Comprehensive answer.
    """
    formatted_query = f"""请综合处理关于 re:Invent 会后回顾、新产品发布和路演的问题：{query}

注意：
1. **必须首先查询知识库**：无论用户问什么，都要先使用 retrieve_recap_info 工具查询知识库
   - 如果用户问"发布了哪些模型/产品/服务" → 调用 retrieve_recap_info("AWS re:Invent 2025 发布 新产品 新服务 模型 AI Bedrock")
   - 如果用户问"Top10 产品" → 调用 retrieve_recap_info("re:Invent 2025 Top10 产品 亮点 发布 重要")
   - 如果用户问"会议总结/回顾" → 调用 retrieve_recap_info("AWS re:Invent 2025 总结 回顾 亮点 Keynote")
2. **知识库定位**：主要用于回答大会总结、技术发布回顾等历史信息
3. **路演安排**：如果用户咨询路演（Roadshow）的具体安排，且知识库中没有相关信息，请明确告知这一点，但不要停留在那里
4. **主动服务**：即使用户没有明确问，也请主动询问或建议用户关注路演城市的天气（使用 get_realtime_weather）和周边美食（使用 search_nearby_restaurants）
5. **场景化建议**：如果用户提到了具体的路演城市（如北京、上海等），请直接调用天气和餐饮工具，为用户提供该城市的实用参会建议
6. 综合回答：将知识库的回顾信息与实时的生活服务信息（天气、餐饮）结合起来，提供有温度的建议
"""

    try:
        logger.info("Routed to Recap Agent")
        agent = init_agent("Recap Agent")
        agent_response = agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            return text_response

        return "很抱歉，暂时无法提供会后回顾信息。请稍后再试。"
    except Exception as e:
        logger.error(f"Error in recap agent: {str(e)}")
        return f"处理会后回顾时出错：{str(e)}"
