"""Minimal Agent loop using a local OpenAI-compatible Qwen3 endpoint."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in a specific IANA timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone name, e.g. America/Vancouver",
                    }
                },
                "required": ["timezone"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the real current weather for a specific city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["city", "unit"],
                "additionalProperties": False,
            },
        },
    },
]

WEATHER_CONDITIONS = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
}


def _json_response(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"User-Agent": "minimal-agent-tool-loop/0.1"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def get_current_time(timezone: str) -> str:
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        return _json_response({"error": f"Unknown IANA timezone: {timezone}"})

    return _json_response(
        {
            "timezone": timezone,
            "datetime": now.isoformat(timespec="seconds"),
            "day_of_week": now.strftime("%A"),
        }
    )


def get_weather(city: str, unit: str) -> str:
    try:
        location_data = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1, "language": "en", "format": "json"},
        )
        locations = location_data.get("results", [])
        if not locations:
            return _json_response({"error": f"City not found: {city}"})

        location = locations[0]
        temperature_unit = "fahrenheit" if unit == "fahrenheit" else "celsius"
        weather_data = _get_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code",
                "temperature_unit": temperature_unit,
                "timezone": "auto",
            },
        )
        current = weather_data["current"]
        code = int(current["weather_code"])
        return _json_response(
            {
                "city": location["name"],
                "country": location.get("country"),
                "observed_at": current["time"],
                "temperature": current["temperature_2m"],
                "unit": temperature_unit,
                "conditions": WEATHER_CONDITIONS.get(code, f"weather code {code}"),
                "humidity": current["relative_humidity_2m"],
                "source": "Open-Meteo",
            }
        )
    except (KeyError, OSError, TimeoutError, ValueError) as exc:
        return _json_response({"error": f"Weather lookup failed: {exc}"})


def execute_tool(name: str, arguments: str | dict[str, Any]) -> str:
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError as exc:
        return _json_response({"error": f"Invalid tool arguments: {exc.msg}"})

    try:
        if name == "get_current_time":
            return get_current_time(timezone=parsed["timezone"])
        if name == "get_weather":
            return get_weather(city=parsed["city"], unit=parsed["unit"])
        return _json_response({"error": f"Unknown tool: {name}"})
    except (KeyError, TypeError) as exc:
        return _json_response({"error": f"Missing or invalid argument: {exc}"})


def build_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        # Keep localhost traffic away from macOS/system proxy settings.
        http_client=httpx.Client(trust_env=False),
    )


def run_agent(
    prompt: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    max_iterations: int | None = None,
    trace: bool = True,
) -> str:
    client = client or build_client()
    model = model or os.getenv("MODEL_NAME", "qwen3:0.6b")
    max_iterations = max_iterations or int(os.getenv("MAX_ITERATIONS", "6"))
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use tools for real-time information. "
                "For Vancouver time use the IANA timezone America/Vancouver. "
                "Do not invent tool results."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    for iteration in range(1, max_iterations + 1):
        if trace:
            print(f"\n--- iteration {iteration}/{max_iterations} ---")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            # Qwen3 0.6B may reason about a tool but emit an empty answer when
            # left on auto. Require at least one call for this real-time demo;
            # after results arrive, restore auto so the model can finish.
            tool_choice="required" if iteration == 1 else "auto",
            parallel_tool_calls=True,
            reasoning_effort="none",
            temperature=0,
        )
        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))

        if not assistant_message.tool_calls:
            answer = assistant_message.content or ""
            if trace:
                print(f"assistant: {answer}")
            return answer

        for tool_call in assistant_message.tool_calls:
            name = tool_call.function.name
            arguments = tool_call.function.arguments
            if trace:
                print(f"tool call: {name}({arguments})")
            result = execute_tool(name, arguments)
            if trace:
                print(f"tool result: {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    raise RuntimeError(
        f"Agent did not finish within {max_iterations} iterations; stopped by Harness limit."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt",
        nargs="?",
        default="What's the current time and weather in Vancouver?",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--no-trace", action="store_true")
    args = parser.parse_args()
    run_agent(
        args.prompt,
        model=args.model,
        max_iterations=args.max_iterations,
        trace=not args.no_trace,
    )


if __name__ == "__main__":
    main()
