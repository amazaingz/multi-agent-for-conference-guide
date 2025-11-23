"""
Dining Agent - Provides restaurant and food recommendations for any location
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from agents.prompt_templates import dining_agent_system_prompt
from config.bedrock_config import (
    BEDROCK_MODEL_ID,
    DEFAULT_KNOWLEDGE_BASE_ID,
    MAX_RAG_RESULTS,
    MIN_RELEVANCE_SCORE,
    AWS_REGION,
)
import uuid
import requests
from tools.logger_config import get_logger

logger = get_logger(__name__)

bedrock_model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    temperature=0.3,
    top_p=0.3,
)


@tool
def get_city_coordinates(city: str) -> dict:
    """
    Get coordinates for a city using Open-Meteo Geocoding API (free, no API key required).
    Prioritizes results with higher population to avoid small towns with same names.

    Args:
        city: City name to search for

    Returns:
        Dictionary containing latitude, longitude, and full location name
    """
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": city,
            "count": 5,  # Get multiple results to choose the best one
            "language": "zh",
            "format": "json"
        }
        
        response = requests.get(geocoding_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            return {
                "status": "error",
                "message": f"未找到城市: {city}"
            }
        
        # Sort by population (if available) to get major cities first
        results = data["results"]
        results.sort(key=lambda x: x.get("population", 0), reverse=True)
        
        result = results[0]
        return {
            "status": "success",
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "name": result["name"],
            "country": result.get("country", ""),
            "admin1": result.get("admin1", ""),
            "population": result.get("population", 0)
        }
    except Exception as e:
        logger.error(f"Error geocoding city {city}: {str(e)}")
        return {
            "status": "error",
            "message": f"获取城市坐标失败: {str(e)}"
        }


@tool
def search_nearby_restaurants(city: str, cuisine_type: str = None, radius_km: float = 2.0) -> dict:
    """
    Search for restaurants near a city using OpenStreetMap Overpass API (free, no API key required).

    Args:
        city: City name to search restaurants in
        cuisine_type: Optional cuisine type filter (e.g., "chinese", "italian", "japanese")
        radius_km: Search radius in kilometers (default: 2.0)

    Returns:
        Dictionary containing list of nearby restaurants
    """
    try:
        # First get city coordinates
        coord_result = get_city_coordinates(city)
        if coord_result["status"] == "error":
            return coord_result
        
        lat = coord_result["latitude"]
        lon = coord_result["longitude"]
        location_name = f"{coord_result['name']}, {coord_result.get('admin1', coord_result.get('country', ''))}"
        
        # Convert km to meters for Overpass API
        radius_m = int(radius_km * 1000)
        
        # Build Overpass query
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for restaurants and cafes
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="restaurant"](around:{radius_m},{lat},{lon});
          node["amenity"="cafe"](around:{radius_m},{lat},{lon});
          node["amenity"="fast_food"](around:{radius_m},{lat},{lon});
        );
        out body 50;
        """
        
        response = requests.post(overpass_url, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        restaurants = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "未命名餐厅")
            
            # Filter by cuisine type if specified
            if cuisine_type:
                element_cuisine = tags.get("cuisine", "").lower()
                if cuisine_type.lower() not in element_cuisine:
                    continue
            
            restaurant_info = {
                "name": name,
                "type": tags.get("amenity", "restaurant"),
                "cuisine": tags.get("cuisine", "未指定"),
                "address": tags.get("addr:street", ""),
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "latitude": element.get("lat"),
                "longitude": element.get("lon")
            }
            restaurants.append(restaurant_info)
        
        return {
            "status": "success",
            "location": location_name,
            "search_radius_km": radius_km,
            "total_found": len(restaurants),
            "restaurants": restaurants[:20]  # Limit to 20 results
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout searching restaurants in {city}")
        return {
            "status": "error",
            "message": "搜索餐厅超时，请稍后重试"
        }
    except Exception as e:
        logger.error(f"Error searching restaurants in {city}: {str(e)}")
        return {
            "status": "error",
            "message": f"搜索餐厅失败: {str(e)}"
        }


@tool
def retrieve_dining_info(query: str) -> dict:
    """
    Retrieve dining and restaurant information from knowledge base.

    Args:
        query: Dining related query

    Returns:
        Dictionary containing restaurant information
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
        logger.info(f"Dining retrieve_response: {retrieve_response}")
        return retrieve_response
    except Exception as e:
        logger.error(f"Error retrieving dining info: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving dining information: {str(e)}",
        }


def init_agent(agent_name: str) -> Agent:
    return Agent(
        name=agent_name,
        system_prompt=dining_agent_system_prompt,
        model=bedrock_model,
        tools=[get_city_coordinates, search_nearby_restaurants, retrieve_dining_info],
    )


@tool
def get_dining_recommendations(query: str, user_id: str = None) -> str:
    """
    Process dining related queries and provide restaurant recommendations for any location.

    Args:
        query: Dining related question from the user (should include location or city)
        user_id: Current user_id (optional)

    Returns:
        Restaurant recommendations and dining suggestions
    """
    formatted_query = f"""请根据用户的查询提供餐厅推荐：{query}

注意：
1. 从用户查询中识别城市/地点名称，如果没有明确指定，默认使用 Las Vegas
2. 识别用户想要的菜系类型（如中餐、日料、意大利菜等）
3. 优先使用 search_nearby_restaurants 工具搜索指定城市的实时餐厅信息
4. 如果查询是关于 re:Invent 会场或 Las Vegas 特定区域，可以使用 retrieve_dining_info 获取知识库中的详细推荐
5. 结合实时搜索结果和知识库信息（如果相关）给出全面的推荐
6. 提供餐厅名称、类型、菜系、地址等信息
7. 如果有特殊需求（素食、清真等），在推荐时考虑这些因素
"""

    try:
        logger.info("Routed to Dining Agent")
        agent = init_agent("Dining Agent")
        agent_response = agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            return text_response

        return "很抱歉，暂时无法提供餐厅推荐。请稍后再试。"
    except Exception as e:
        logger.error(f"Error in dining agent: {str(e)}")
        return f"处理餐厅推荐时出错：{str(e)}"
