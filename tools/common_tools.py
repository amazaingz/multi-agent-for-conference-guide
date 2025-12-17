from strands import tool
from typing import Dict, Any
from models.context import CustomerServiceAgentContext, generate_confirmation_number
from strands_tools import retrieve, think
from config.bedrock_config import AWS_REGION, MIN_RELEVANCE_SCORE, MAX_RAG_RESULTS
from tools.logger_config import get_logger
import uuid

logger = get_logger(__name__)


@tool
def order_status_tool(order_number: str) -> str:
    """Lookup the status for a order."""
    return f"Order {order_number} is scheduled to deliver."


def retrieve_from_kb(query: str, kb_id: str) -> Dict[str, Any]:
    """
    Retrieve information from a knowledge base based on a query.

    Args:
        query: The search query
        kb_id: Knowledge Base ID
        min_score: Minimum relevance score
        region: AWS region

    Returns:
        Dictionary containing retrieval results
    """

    try:
        # Call the retrieve tool directly
        retrieve_response = retrieve.retrieve(
            {
                "toolUseId": str(uuid.uuid4()),
                "input": {
                    "text": query,
                    "score": min_score,
                    "numberOfResults": MAX_RAG_RESULTS,
                    "knowledgeBaseId": kb_id,
                    "region": region,
                },
            }
        )

        return retrieve_response
    except Exception as e:
        logger.error(f"Error details: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving from knowledge base: {str(e)}",
        }
