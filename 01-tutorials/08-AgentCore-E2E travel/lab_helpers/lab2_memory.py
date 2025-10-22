#!/usr/bin/python
"""AgentCore Memory integration for Strands agents."""

import logging
import os
import sys
import uuid
from typing import Dict

import boto3
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from boto3.session import Session
from botocore.exceptions import ClientError
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)

boto_session = Session()
REGION = boto_session.region_name

logger = logging.getLogger(__name__)
from scripts.utils import get_ssm_parameter, put_ssm_parameter

ACTOR_ID = "customer_001"
SESSION_ID = str(uuid.uuid4())

memory_client = MemoryClient(region_name=REGION)
memory_name = "TravelAgentMemory"


def create_or_get_memory_resource():
    try:
        memory_id = get_ssm_parameter("/app/travelagent/agentcore/memory_id")
        memory_client.gmcp_client.get_memory(memoryId=memory_id)
        return memory_id
    except:
        try:
            strategies = [
                {
                    StrategyType.USER_PREFERENCE.value: {
                        "name": "CustomerPreferences",
                        "description": "Captures customer preferences and behavior",
                        "namespaces": ["travelagent/customer/{actorId}/preferences"],
                    }
                },
                {
                    StrategyType.SEMANTIC.value: {
                        "name": "TravelAgentSemantic",
                        "description": "Stores facts from conversations",
                        "namespaces": ["travelagent/customer/{actorId}/semantic"],
                    }
                },
            ]
            print("Creating AgentCore Memory resources. This can a couple of minutes..")
            # *** AGENTCORE MEMORY USAGE *** - Create memory resource with semantic and user_pref strategy
            response = memory_client.create_memory_and_wait(
                name=memory_name,
                description="Travel agent memory",
                strategies=strategies,
                event_expiry_days=90,  # Memories expire after 90 days
            )
            memory_id = response["id"]
            try:
                put_ssm_parameter("/app/travelagent/agentcore/memory_id", memory_id)
            except:
                raise
            return memory_id
        except:
            return None


def delete_memory(memory_hook):
    try:
        ssm_client = boto3.client("ssm", region_name=REGION)

        memory_client.delete_memory(memory_id=memory_hook.memory_id)
        ssm_client.delete_parameter(Name="/app/travelagent/agentcore/memory_id")
    except Exception:
        pass


class TravelAgentMemoryHooks(HookProvider):
    """Memory hooks for travel agent"""

    def __init__(
        self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str
    ):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve customer context before processing travel query"""
        messages = event.agent.messages
        if (
            messages[-1]["role"] == "user"
            and "toolResult" not in messages[-1]["content"][0]
        ):
            user_query = messages[-1]["content"][0]["text"]

            try:
                all_context = []

                for context_type, namespace in self.namespaces.items():
                    # *** AGENTCORE MEMORY USAGE *** - Retrieve customer context from each namespace
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.actor_id),
                        query=user_query,
                        top_k=3,
                    )
                    # Post-processing: Format memories into context strings
                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get("content", {})
                            if isinstance(content, dict):
                                text = content.get("text", "").strip()
                                if text:
                                    all_context.append(
                                        f"[{context_type.upper()}] {text}"
                                    )

                # Inject customer context into the query
                if all_context:
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0][
                        "text"
                    ] = f"Customer Context:\n{context_text}\n\n{original_text}"
                    logger.info(f"Retrieved {len(all_context)} customer context items")

            except Exception as e:
                logger.error(f"Failed to retrieve customer context: {e}")

    def save_interaction(self, event: AfterInvocationEvent):
        """Save customer interaction after agent response"""
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                # Get last customer query and agent response
                customer_query = None
                agent_response = None

                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif (
                        msg["role"] == "user"
                        and not customer_query
                        and "toolResult" not in msg["content"][0]
                    ):
                        customer_query = msg["content"][0]["text"]
                        break

                if customer_query and agent_response:
                    # *** AGENTCORE MEMORY USAGE *** - Save the interaction
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[
                            (customer_query, "USER"),
                            (agent_response, "ASSISTANT"),
                        ],
                    )
                    logger.info("Saved interaction to memory")

        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register travel agent memory hooks"""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_interaction)
        logger.info("Travel agent memory hooks registered")


def get_memory_hooks():
    """Setup memory resource and return Memory hooks for agent"""
    memory_id = create_or_get_memory_resource()
    memory_hooks = MemoryHook(
        memory_client=memory_client,
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id=SESSION_ID,
    )

    return memory_hooks