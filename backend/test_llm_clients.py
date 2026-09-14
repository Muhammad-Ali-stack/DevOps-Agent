from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from core.llm_client import get_llm_client


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    providers = ["gemini", "groq"]
    response_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "answer": {"type": "string"},
        },
        "required": ["status", "answer"],
    }

    for provider in providers:
        api_key_name = f"{provider.upper()}_API_KEY"
        if not os.getenv(api_key_name):
            print(f"Skipping {provider}: {api_key_name} is not set.")
            continue

        client = get_llm_client(provider)
        result = client.generate(
            system_prompt="Return a tiny JSON response with status and answer.",
            user_prompt="Say hello from the monitoring agent.",
            response_schema=response_schema,
        )

        print(f"{provider}: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
