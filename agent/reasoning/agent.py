"""
Voice AI Agent — Core Reasoning Engine
Uses OpenAI GPT-4o (or any OpenAI-compatible LLM) to interpret user intent
and orchestrate tool calls.
"""
import json
import os
from typing import Any, Dict, Tuple

import openai

from agent.tools.appointment_tools import TOOL_DEFINITIONS, execute_tool
from agent.prompt.system_prompt import build_system_prompt


class VoiceAgent:
    """Stateless reasoning agent. All context is passed in per call."""

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-..."))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def process(
        self,
        user_text: str,
        language: str,
        session_context: Dict[str, Any],
        patient_context: Dict[str, Any],
    ) -> Tuple[str, list]:
        """
        Run one turn of the conversation.

        Returns:
            (response_text_in_user_language, list_of_tool_results)
        """
        system_prompt = build_system_prompt(
            language=language,
            session_context=session_context,
            patient_context=patient_context,
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Inject conversation history from session
        for msg in session_context.get("history", [])[-6:]:   # last 3 turns
            messages.append(msg)

        messages.append({"role": "user", "content": user_text})

        tool_results = []
        response_text = ""

        # ── Agentic loop: keep calling until no more tool use ──────────────
        for _ in range(5):   # max 5 tool-call rounds
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=512,
            )

            choice = completion.choices[0]

            if choice.finish_reason == "tool_calls":
                # Execute each requested tool
                tool_call_results_msg = []
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    result = await execute_tool(tc.function.name, args)
                    tool_results.append({"tool": tc.function.name, "result": result})
                    tool_call_results_msg.append({
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "content": json.dumps(result),
                    })

                # Add assistant + tool results to message history and loop
                messages.append(choice.message)
                messages.extend(tool_call_results_msg)

            else:
                # Final text response
                response_text = choice.message.content or ""
                break

        return response_text, tool_results
