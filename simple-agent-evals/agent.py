"""
Simple Strands Agent with DuckDuckGo Search, Weather, and Directions tools.

This agent demonstrates:
- Multi-tool agent using Strands SDK
- Braintrust observability using OpenTelemetry
- Anthropic Claude Haiku 4.5 as the model
- Tools imported from tools.py (kept separate for reuse and testing)
"""

import asyncio
import logging
import os
from typing import Optional

from braintrust.otel import BraintrustSpanProcessor
from dotenv import load_dotenv
from opentelemetry.sdk.trace import TracerProvider
from strands import Agent
from strands.telemetry import StrandsTelemetry

from tools import (
    duckduckgo_search,
    get_directions,
    get_weather,
    get_time,
    currency_exchange,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()


# Constants
AGENT_MODEL_ID = "claude-haiku-4-5-20251001"
AGENT_MAX_TOKENS = 4096
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")


def _load_system_prompt() -> str:
    """
    Load the system prompt from prompts/system_prompt.txt.

    Returns:
        System prompt string
    """
    if not os.path.exists(SYSTEM_PROMPT_PATH):
        raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_PATH}")

    with open(SYSTEM_PROMPT_PATH, "r") as f:
        prompt = f.read().strip()

    logger.info(f"Loaded system prompt from {SYSTEM_PROMPT_PATH} ({len(prompt)} chars)")
    return prompt


def _get_env_var(
    key: str,
    default: Optional[str] = None
) -> str:
    """Get environment variable or raise error if not found."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} not set")
    return value


def _setup_observability() -> TracerProvider:
    """
    Set up OpenTelemetry with Braintrust for observability.

    Returns:
        Configured TracerProvider instance
    """
    logger.info("Setting up Braintrust observability")

    braintrust_api_key = _get_env_var("BRAINTRUST_API_KEY")
    braintrust_project = _get_env_var("BRAINTRUST_PROJECT")

    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BraintrustSpanProcessor(
            api_key=braintrust_api_key,
            parent=braintrust_project
        )
    )

    from opentelemetry import trace
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"Braintrust observability configured for project: {braintrust_project}")
    return tracer_provider


def _create_agent() -> Agent:
    """
    Create and configure the Strands agent with all three tools.

    Returns:
        Configured Agent instance
    """
    logger.info("Creating Strands agent with search, weather, and directions tools")

    tracer_provider = _setup_observability()
    telemetry = StrandsTelemetry(tracer_provider=tracer_provider)

    anthropic_api_key = _get_env_var("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

    system_prompt = _load_system_prompt()

    from strands.models import AnthropicModel

    model = AnthropicModel(
        model_id=AGENT_MODEL_ID,
        max_tokens=AGENT_MAX_TOKENS
    )

    agent = Agent(
        system_prompt=system_prompt,
        model=model,
        tools=[duckduckgo_search, get_weather, get_directions, get_time, currency_exchange]
    )

    logger.info("Agent created successfully")
    return agent


def create_agent_for_eval() -> Agent:
    """
    Create agent for use in evaluations (no interactive loop).
    This is the public entry point that eval.py imports.

    Returns:
        Configured Agent instance
    """
    return _create_agent()


def main() -> None:
    """Main function to run the agent interactively."""
    logger.info("Starting Simple Agent Evals")

    agent = _create_agent()

    print("\n" + "=" * 80)
    print("Simple Agent with Search, Weather, and Directions")
    print("=" * 80 + "\n")

    print("Ask me anything! I can search the web, check weather, and get directions.")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            response = asyncio.run(agent.invoke_async(user_input))
            print(f"\nAgent: {response}\n")

        except EOFError:
            print("\n\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
