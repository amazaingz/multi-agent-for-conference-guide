"""
Free Weather Agent - Provides real-time Las Vegas weather using Open-Meteo (no API key required)
Completely free, no registration needed
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from agents.prompt_templates import weather_agent_system_prompt
from config.bedrock_config import (
    BEDROCK_MODEL_ID,
    DEFAULT_KNOWLEDGE_BASE_ID,
    MAX_RAG_RESULTS,
    MIN_RELEVANCE_SCORE,
    AWS_REGION,
)
import uuid
import requests
from datetime import datetime
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
def get_realtime_weather(city: str) -> dict:
    """
    Get real-time weather information using Open-Meteo API (free, no API key required).

    Args:
        city: City name (default: Las Vegas)

    Returns:
        Dictionary containing current weather data
    """
    try:
        # First, get coordinates for the city
        coord_result = get_city_coordinates(city)
        if coord_result["status"] == "error":
            return coord_result
        
        latitude = coord_result["latitude"]
        longitude = coord_result["longitude"]
        location_name = f"{coord_result['name']}, {coord_result.get('admin1', coord_result.get('country', ''))}"
        
        # Open-Meteo API - completely free, no API key needed
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "precipitation_probability_max",
            ],
            "hourly": ["temperature_2m", "weather_code", "relative_humidity_2m"],
            "forecast_days": 16,  # 支持最多16天预报
            "timezone": "auto",  # 自动根据坐标设置时区
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Weather code mapping (WMO codes)
        weather_descriptions = {
            0: "晴朗",
            1: "基本晴朗",
            2: "部分多云",
            3: "多云",
            45: "有雾",
            48: "雾凇",
            51: "小雨",
            53: "中雨",
            55: "大雨",
            61: "小雨",
            63: "中雨",
            65: "大雨",
            71: "小雪",
            73: "中雪",
            75: "大雪",
            77: "雪粒",
            80: "阵雨",
            81: "中阵雨",
            82: "大阵雨",
            85: "小阵雪",
            86: "大阵雪",
            95: "雷暴",
            96: "雷暴伴小冰雹",
            99: "雷暴伴大冰雹",
        }

        current = data["current"]
        weather_code = current.get("weather_code", 0)
        weather_desc = weather_descriptions.get(weather_code, "未知")

        # Format the response
        weather_info = {
            "status": "success",
            "location": location_name,
            "current": {
                "temperature": round(current["temperature_2m"], 1),
                "feels_like": round(current["apparent_temperature"], 1),
                "humidity": current["relative_humidity_2m"],
                "description": weather_desc,
                "weather_code": weather_code,
                "wind_speed": round(current["wind_speed_10m"], 1),
                "wind_direction": current["wind_direction_10m"],
                "timestamp": current["time"],
            },
            "daily_forecast": [],  # 每日预报（最多16天）
            "hourly_forecast": [],  # 小时预报
        }

        # Add daily forecast (up to 16 days)
        daily = data.get("daily", {})
        if daily and "time" in daily:
            for i in range(len(daily["time"])):
                daily_weather_code = daily["weather_code"][i] if daily.get("weather_code") else 0
                daily_desc = weather_descriptions.get(daily_weather_code, "未知")
                
                weather_info["daily_forecast"].append({
                    "date": daily["time"][i],
                    "temp_max": round(daily["temperature_2m_max"][i], 1) if daily.get("temperature_2m_max") else None,
                    "temp_min": round(daily["temperature_2m_min"][i], 1) if daily.get("temperature_2m_min") else None,
                    "description": daily_desc,
                    "precipitation_probability": daily["precipitation_probability_max"][i] if daily.get("precipitation_probability_max") else 0,
                })

        # Add hourly forecast for next 24 hours
        hourly = data.get("hourly", {})
        if hourly and "time" in hourly:
            for i in range(min(24, len(hourly["time"]))):
                forecast_weather_code = hourly["weather_code"][i] if hourly.get("weather_code") else 0
                forecast_desc = weather_descriptions.get(forecast_weather_code, "未知")

                weather_info["hourly_forecast"].append({
                    "time": hourly["time"][i],
                    "temperature": round(hourly["temperature_2m"][i], 1),
                    "description": forecast_desc,
                    "humidity": hourly["relative_humidity_2m"][i] if hourly.get("relative_humidity_2m") else None,
                })

        logger.info(f"Successfully retrieved weather data from Open-Meteo for {location_name}")
        return weather_info

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        return {
            "status": "error",
            "message": f"获取天气数据失败: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_realtime_weather: {str(e)}")
        return {
            "status": "error",
            "message": f"处理天气数据时出错: {str(e)}",
        }


@tool
def retrieve_weather_info(query: str) -> dict:
    """
    Retrieve historical weather information and tips from knowledge base.

    Args:
        query: Weather related query

    Returns:
        Dictionary containing weather information from knowledge base
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
        logger.info(f"Weather retrieve_response: {retrieve_response}")
        return retrieve_response
    except Exception as e:
        logger.error(f"Error retrieving weather info: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving weather information: {str(e)}",
        }


def init_agent(agent_name: str) -> Agent:
    """Initialize the weather agent with geocoding, real-time weather and knowledge base tools."""
    return Agent(
        name=agent_name,
        system_prompt=weather_agent_system_prompt,
        model=bedrock_model,
        tools=[get_city_coordinates, get_realtime_weather, retrieve_weather_info],
    )


@tool
def get_weather_info(query: str, user_id: str = None) -> str:
    """
    Process weather related queries and provide weather information and clothing suggestions for any city.
    Uses Open-Meteo free API for real-time data (no API key required).

    Args:
        query: Weather related question from the user (should include city name)
        user_id: Current user_id (optional)

    Returns:
        Weather information and suggestions
    """
    formatted_query = f"""请根据用户的查询提供天气信息和穿衣建议：{query}

注意：
1. 准确识别用户查询中的城市名称。不要使用默认地点。如果用户未指定地点，请在回答中询问用户。
2. 深入分析用户的具体需求（如户外活动、出行计划等），基于此查询相关天气参数（如降雨概率、风速、紫外线指数等）。
3. 使用 get_realtime_weather 工具获取指定城市的实时天气数据（使用 Open-Meteo 免费 API）。
4. 结合 retrieve_weather_info 获取的相关背景信息（如果适用）。
5. 根据天气状况和用户需求给出针对性的建议（不仅仅是通用穿衣建议）。例如：
   - 针对运动：考虑风速、空气质量。
   - 针对旅行：考虑未来几天的趋势。
6. 如果需要具体的穿衣建议，请参考温度区间：
   - < 10°C: 厚外套、保暖衣物
   - 10-20°C: 夹克、长袖卫衣
   - 20-30°C: 短袖、轻薄衣物
   - > 30°C: 防晒、透气衣物
"""

    try:
        logger.info("Routed to Free Weather Agent (Open-Meteo)")
        agent = init_agent("Weather Agent")
        agent_response = agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            return text_response

        return "很抱歉，暂时无法获取天气信息。请稍后再试。"
    except Exception as e:
        logger.error(f"Error in weather agent: {str(e)}")
        return f"处理天气查询时出错：{str(e)}"
