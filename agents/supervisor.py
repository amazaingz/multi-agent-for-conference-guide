from strands import Agent, tool
from typing import Dict, Any, List
from models.context import CustomerServiceAgentContext, create_initial_context
from strands.models import BedrockModel
from agents.prompt_templates import supervisor_agent_system_prompt
from agents.weather_agent import get_weather_info
from agents.dining_agent import get_dining_recommendations
from agents.session_agent import get_session_planning
from agents.memory_agent import process_attendee_info
from tools.agentcore_memory import update_memory
from config.bedrock_config import BEDROCK_AGENTCORE_MEMORY_ID, AWS_REGION
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
from tools.logger_config import get_logger
import time

logger = get_logger(__name__)


bedrock_model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    temperature=0.3,
    top_p=0.8,
)


class SupervisorAgent:
    """Supervisor agent manages interactions and maintains conversation state."""

    def __init__(self, session_id: str):
        self.conversation_history: List[Dict[str, Any]] = []
        self.session_id: str = session_id
        self.user_id: str = None
        self.context = create_initial_context()
        self.current_agent_name = "Supervisor-Agent"
        self.memories = "当前参会者未提供个人信息"

        @tool
        def update_user_id(user_id: str) -> str:
            """
            When attendee provides the user id, run this tool to record user id.

            Args:
                user_id: Attendee provided user id
            Returns:
                Confirmation message
            """
            logger.info(f"use tool: update_user_id: {user_id}")
            self.user_id = user_id

            bedrock_memory_provider = AgentCoreMemoryToolProvider(
                memory_id=BEDROCK_AGENTCORE_MEMORY_ID,
                actor_id=f"user_{user_id}",
                session_id=f"session_user_{user_id}",
                namespace=f"/users/user_{user_id}",
                region=AWS_REGION,
            )

            histories = process_attendee_info(
                self.user_id,
                self.session_id,
                "您保存了该参会者的哪些信息？请列出所有信息。",
            )
            self.update_system_prompt(histories)
            self.memories = histories
            # Add memory tools to the agent
            self.current_agent.tools.add_tools(bedrock_memory_provider.tools)

            return f"User ID {user_id} 已记录"

        # Create the agent with all tools
        self.current_agent = Agent(
            name="Supervisor Agent",
            system_prompt=self._build_system_prompt(),
            model=bedrock_model,
            state={"session_id": session_id},
            tools=[
                update_user_id,
                get_weather_info,
                get_dining_recommendations,
                get_session_planning,
            ],
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current context."""
        base_prompt = supervisor_agent_system_prompt
        context_info = f"当前的session_id: {self.session_id}"
        if self.user_id is not None:
            context_info += f", user_id: {self.user_id}"

        return f"{base_prompt}. {context_info}"

    def update_system_prompt(self, updates_prompt: str) -> None:
        """Update the system prompt of the current agent."""
        self.current_agent.system_prompt += f"\n下面是此参会者的历史信息,请先基于历史信息给予总结回复，然后再提供服务。\n 历史信息:{updates_prompt}"
        logger.info(f"System prompt updated: {self.current_agent.system_prompt}")

    def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message and return the response with events."""
        messages = []
        # Add user message to conversation history
        tmp_msg = {"role": "user", "content": message, "timestamp": time.time()}
        self.context.update_descriptions(tmp_msg)
        self.conversation_history.append(tmp_msg)
        update_memory(self.user_id, (message, "USER"))

        # Process the message with the current agent
        try:
            # Get agent response
            conversation_prompt = self._build_conversation_prompt(message)
            agent_result = self.current_agent(conversation_prompt)
            logger.info(f"agent result####: {agent_result}")

            # Extract string content from AgentResult
            if hasattr(agent_result, "content"):
                response = str(agent_result.content)
            else:
                response = str(agent_result)

            chat_type = "0"
            if "###gossip###" in response:
                chat_type = "1"
                response = response.replace("###gossip###", "")

            messages.append(
                {
                    "content": response,
                    "chat_type": chat_type,
                    "agent": self.current_agent_name,
                }
            )

            # Add to conversation history
            self.conversation_history.append(
                {"role": "assistant", "content": response, "timestamp": time.time()}
            )
            self.context.update_descriptions(
                {"role": "assistant", "content": response, "timestamp": time.time()}
            )

            update_memory(self.user_id, (response, "ASSISTANT"))

        except Exception as e:
            error_message = f"十分抱歉，系统暂时繁忙，请稍后再试。"
            logger.info(f"Error: {str(e)}")
            messages.append(
                {
                    "content": error_message,
                    "chat_type": "1",
                    "agent": self.current_agent_name,
                }
            )
        tmp_str = self._build_response(messages)
        logger.info(f"build_response result: {tmp_str}")
        return tmp_str

    def _build_conversation_prompt(self, current_message: str) -> str:
        """Build a conversation prompt from the history."""
        return current_message

    def _build_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """Build the response object."""
        return {
            "messages": messages,
        }
