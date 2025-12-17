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
    max_tokens=4096,
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
def search_nearby_restaurants(city: str, cuisine_type: str = None, radius_km: float = 5.0) -> dict:
    """
    Search for restaurants near a city using OpenStreetMap Overpass API (free, no API key required).
    For Chinese cities, also includes way and relation elements for better coverage.

    Args:
        city: City name to search restaurants in
        cuisine_type: Optional cuisine type filter (e.g., "chinese", "italian", "japanese")
        radius_km: Search radius in kilometers (default: 5.0)

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
        
        # Build Overpass query - include node, way, and relation for better coverage
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Enhanced query for better coverage in all regions including China
        query = f"""
        [out:json][timeout:30];
        (
          nwr["amenity"="restaurant"](around:{radius_m},{lat},{lon});
          nwr["amenity"="cafe"](around:{radius_m},{lat},{lon});
          nwr["amenity"="fast_food"](around:{radius_m},{lat},{lon});
          nwr["cuisine"](around:{radius_m},{lat},{lon});
        );
        out center 100;
        """
        
        response = requests.post(overpass_url, data={"data": query}, timeout=35)
        response.raise_for_status()
        data = response.json()
        
        restaurants = []
        seen_names = set()  # Avoid duplicates
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("name:zh") or tags.get("name:en")
            
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            
            # Filter by cuisine type if specified
            if cuisine_type:
                element_cuisine = tags.get("cuisine", "").lower()
                if cuisine_type.lower() not in element_cuisine:
                    continue
            
            # Get coordinates (center for ways/relations)
            elem_lat = element.get("lat") or element.get("center", {}).get("lat")
            elem_lon = element.get("lon") or element.get("center", {}).get("lon")
            
            restaurant_info = {
                "name": name,
                "type": tags.get("amenity", "restaurant"),
                "cuisine": tags.get("cuisine", "未指定"),
                "address": tags.get("addr:street") or tags.get("addr:full", ""),
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "latitude": elem_lat,
                "longitude": elem_lon
            }
            restaurants.append(restaurant_info)
        
        # If no results found, return helpful message
        if len(restaurants) == 0:
            return {
                "status": "success",
                "location": location_name,
                "search_radius_km": radius_km,
                "total_found": 0,
                "restaurants": [],
                "note": f"OpenStreetMap 在 {location_name} 的餐厅数据较少。建议使用大众点评、美团等本地平台搜索。"
            }
        
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
            "status": "partial",
            "location": city,
            "message": f"搜索 {city} 餐厅超时。建议使用大众点评、美团等本地平台搜索该城市的餐厅。"
        }
    except Exception as e:
        logger.error(f"Error searching restaurants in {city}: {str(e)}")
        return {
            "status": "partial",
            "location": city,
            "message": f"搜索 {city} 餐厅时遇到问题。建议使用大众点评、美团等本地平台搜索。"
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
1. 准确识别查询中的城市或具体地点。如果地点不明确，请要求用户提供。
2. 详细分析用户的饮食偏好（菜系、口味、价格预算、用餐氛围、特殊饮食习惯如素食/过敏等）。
3. 使用 search_nearby_restaurants 工具搜索符合条件的实时餐厅信息。
4. 灵活使用 retrieve_dining_info 获取特色推荐或详细评论（如果适用）。
5. 推荐理由应直接回应用户的特定需求。
6. 提供完整的餐厅信息：名称、特色、地址、以及为何符合用户需求的说明。
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
