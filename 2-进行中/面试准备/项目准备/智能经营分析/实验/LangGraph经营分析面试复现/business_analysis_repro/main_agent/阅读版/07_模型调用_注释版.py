# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/model.py
# 原文件 SHA-256：2b34c88ab028476b2b051d82d3916052a551bbe2f97ecac2131e3f3d911a7b8e
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

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


# ── 可替换模型接口｜原文件 20–25 行 ──
# 本地测试注入一个可控 complete 实现，不需要每个测试都请求 Kimi。
class Model(Protocol):
    """测试可注入可控模型，避免把网络随机性混入边界测试。"""

    def complete(
        self, stage: str, instruction: str, payload: dict, schema: type[BaseModel]
    ) -> BaseModel: ...


class ModelFailure(RuntimeError):
    pass


# ── 创建模型客户端｜原文件 32–48 行 ──
# 从 settings 获取本地配置，不把密钥复制进 State 或提示词。
# 这里只创建客户端；真正网络调用在原文件第 78 行。
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

    # ── 每次模型请求的上下文｜原文件 50–56 行 ──
    # SystemMessage=本阶段指令+JSON Schema；HumanMessage=调用方显式传入的 payload。
    # 不会凭 thread_id 自动读取之前所有模型对话，Trace 也不会自动拼进去。
    def complete(self, stage, instruction, payload, schema):
        system = instruction + "\n仅返回符合以下 JSON Schema 的 JSON，不要 Markdown 代码块：\n"
        system += json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        # 最多两次显式尝试：所有请求均能在 Trace 中看到；SDK 暗中重试已关闭。
        # ── 模型请求层面的有限重试｜原文件 58–74 行 ──
        # 一次 complete 最多两次尝试；按同任务 Trace 中 model_request 数量执行总调用上限。
        # 它限制的是这个本地任务的调用数，不是模型账户的 TPM/RPM 限流器。
        for attempt in range(1, 3):
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
                # ── 调用 Kimi 并校验返回结构｜原文件 75–88 行 ──
                # 先请求并记录响应/usage，再由 Pydantic 检查字段类型；之后才返回给节点。
                # 格式合格仍可能有业务错误，需要图中的准入和结果校验。
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
                    parsed = schema.model_validate_json(response.content)
                    span["parsed"] = parsed
                    return parsed
                # ── 可重试与不可重试错误｜原文件 89–117 行 ──
                # JSON/结构错误和部分瞬时网络错误可再试一次；认证等错误不会被无限重试。
                # 这与 graph 里重取能力结果、重写回答是三种不同层次的修复。
                except Exception as exc:
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
