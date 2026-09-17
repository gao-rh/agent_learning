"""Kimi 适配层：模型上下文在这里显式构造，并记录实际请求/响应。

不读取整份 State，不上传 Trace，不把 API key 写进消息或日志。
JSON Mode 只确保 JSON 语法，Pydantic 再校验形状，业务准入另由代码负责。
"""

import json
import time
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import tracing_context
from pydantic import BaseModel, ValidationError

from ..settings import get_kimi_settings
from .trace import Trace


class Model(Protocol):
    """测试可注入可控模型，避免把网络随机性混入边界测试。"""

    def complete(
        self, stage: str, instruction: str, payload: dict, schema: type[BaseModel]
    ) -> BaseModel: ...


class ModelFailure(RuntimeError):
    pass


class KimiModel:
    def __init__(self, trace: Trace, max_calls: int = 16):
        settings = get_kimi_settings()
        trace.secrets += (settings.api_key,)
        self.trace = trace
        self.max_calls = max_calls
        self.model_name = settings.model_name
        self.client = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=60,
            max_retries=0,
            max_tokens=1800,
            temperature=0.6,
            extra_body={"thinking": {"type": "disabled"}},
        ).bind(response_format={"type": "json_object"})

    def complete(self, stage, instruction, payload, schema):
        system = instruction + "\n仅返回符合以下 JSON Schema 的 JSON，不要 Markdown 代码块：\n"
        system += json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        # 最多两次显式尝试：所有请求均能在 Trace 中看到；SDK 暗中重试已关闭。
        for attempt in range(1, 3):
            getattr(self.trace, "check_cancel", lambda: None)()
            used = sum(e["kind"] == "model_request" for e in self.trace.read())
            if used >= self.max_calls:
                raise ModelFailure("本任务达到模型调用次数上限。")
            with self.trace.span("model", stage, {"attempt": attempt}) as span:
                self.trace.event(
                    "model_request",
                    stage,
                    model=self.model_name,
                    messages=[{"role": m.type, "content": m.content} for m in messages],
                    parameters={
                        "max_tokens": 1800,
                        "temperature": 0.6,
                        "thinking": "disabled",
                        "format": "json_object",
                    },
                )
                try:
                    # 即使宿主环境开了 LangSmith，也只在本地写这次实验的 Trace。
                    with tracing_context(enabled=False):
                        response = self.client.invoke(messages)
                    self.trace.event(
                        "model_response",
                        stage,
                        content=response.content,
                        usage=response.usage_metadata or {},
                        metadata=response.response_metadata,
                    )
                    getattr(self.trace, "check_cancel", lambda: None)()
                    parsed = schema.model_validate_json(response.content)
                    span["parsed"] = parsed
                    return parsed
                except Exception as exc:
                    getattr(self.trace, "check_cancel", lambda: None)()
                    # 认证/业务等不可重试异常立即返回；只重试格式和瞬时网络故障。
                    code = getattr(exc, "status_code", None)
                    retryable = (
                        isinstance(exc, (ValidationError, TimeoutError))
                        or code
                        in {
                            408,
                            429,
                            500,
                            502,
                            503,
                            504,
                        }
                        or type(exc).__name__ in {"APITimeoutError", "APIConnectionError"}
                    )
                    span["failure"] = {"type": type(exc).__name__, "message": str(exc)}
                    self.trace.event(
                        "model_error", stage, error=span["failure"], retry=retryable and attempt < 2
                    )
                    if not retryable or attempt == 2:
                        raise ModelFailure(f"模型调用失败：{type(exc).__name__}") from exc
                    if isinstance(exc, ValidationError):
                        messages.append(
                            HumanMessage(content="上次输出未通过结构校验，请严格遵循 JSON Schema。")
                        )
                    else:
                        time.sleep(1)
        raise AssertionError("unreachable")
