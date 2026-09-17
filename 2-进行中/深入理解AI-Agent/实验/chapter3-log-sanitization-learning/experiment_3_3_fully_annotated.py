#!/usr/bin/env python3
"""实验 3-3：Regex、Local LLM、Hybrid 日志脱敏完整注释版。

这个文件不是只展示几段片段，而是一份可以独立运行的完整教学实现：

1. 内置 12 条带人工 Gold 标注的虚构日志；
2. 在本文件内完整实现 Regex 检测器；
3. 使用 ``ollama.Client.chat()`` 直接调用本地 Qwen3；
4. 实现 Regex-first / LLM-second 的 Hybrid；
5. 根据精确字符串位置执行脱敏；
6. 计算 precision、recall、typed exact、残余泄漏、utility 和 latency；
7. 提供命令行参数，既可以只跑 Regex，也可以跑完整三路实验。

为什么做成单文件
----------------

官方实现为了工程组织把配置、Regex、Agent、指标、入口拆成多个文件。对于第一次
读代码的人，这会迫使大脑不停跳转。本教学版先把完整主链路放到一个文件中，并用
“模块 1、模块 2……”分区。等你能顺着本文件从上读到下，再回头看官方的多文件组织，
就会容易很多。

它没有使用什么
--------------

- 没有 LangChain；
- 没有 LlamaIndex；
- 没有通用 Agent 框架；
- 没有 Apache 运行框架。

模型调用由 ``ollama`` Python SDK 完成。源码证据中出现的 Apache 是 Qwen 模型的
Apache License 2.0 开源许可证，与程序调用链无关。

运行示例
--------

只跑 Regex，不需要启动 Ollama：

    python experiment_3_3_fully_annotated.py --mode regex --limit 3

只跑一个案例：

    python experiment_3_3_fully_annotated.py \
      --mode regex \
      --case-id mixed_context

跑 Regex、Local LLM、Hybrid 三路：

    ollama serve
    ollama pull qwen3:0.6b
    python experiment_3_3_fully_annotated.py --mode all

保存完整 JSON 结果：

    python experiment_3_3_fully_annotated.py \
      --mode all \
      --output result.json
"""

# ``from __future__ import annotations`` 让类型注解延迟求值。
# 好处是可以直接写 ``list[Finding]`` 等现代注解，也减少某些前向引用问题。
from __future__ import annotations


# ============================================================================
# 模块 1：导入依赖
# ============================================================================

# argparse：解析 ``--mode``、``--model`` 等命令行参数。
import argparse

# json：
# 1. 把模型返回的 JSON 字符串解析为 Python 字典；
# 2. 把最终实验结果保存为 JSON 文件。
import json

# re：实现 Regex 检测器，以及少量字符串替换逻辑。
import re

# time：使用高精度计时器测量每条链路的延迟。
import time

# defaultdict：按 strategy 收集多条案例结果时，省去手动初始化列表。
from collections import defaultdict

# dataclass：把 Case、Finding、Rule 写成有字段定义的数据对象。
# asdict：把 dataclass 转成可写入 JSON 的普通字典。
from dataclasses import asdict, dataclass

# Ollama 的模型详情中可能包含 datetime；标准 json.dumps 不会自动处理它。
from datetime import date, datetime

# Path：跨平台处理输出文件路径。
from pathlib import Path

# mean：计算多条案例的平均指标。
from statistics import mean

# Callable：描述校验函数类型；Any：处理模型 SDK 返回的动态对象。
from typing import Any, Callable


# ============================================================================
# 模块 2：实验配置
# ============================================================================

# 默认模型。命令行可以通过 ``--model qwen3:1.7b`` 覆盖它。
DEFAULT_MODEL = "qwen3:0.6b"

# Ollama 默认在本机 11434 端口提供 HTTP 服务。
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

# 为了让重复实验尽可能稳定，将温度设为 0，并固定随机种子。
TEMPERATURE = 0
SEED = 37

# 最多允许模型生成多少 token。脱敏检测只需要短 JSON，不应无限生成。
MAX_OUTPUT_TOKENS = 1200

# Qwen3 支持 thinking 模式，但本任务只需要短小的结构化抽取结果。
# 若开启 thinking，小模型可能把全部生成预算消耗在重复推理中，最终 content 为空。
# 因此这里显式关闭思考，直接生成 JSON。
ENABLE_THINKING = False


# ============================================================================
# 模块 3：核心数据结构
# ============================================================================

@dataclass(frozen=True)
class GoldItem:
    """人工标注的一条正确答案。

    ``frozen=True`` 表示创建后不能修改。这很适合 Gold：实验运行期间，标准答案不应该
    被检测器或其他代码意外改写。

    Attributes:
        pii_type: 敏感信息类型，例如 ``password``、``cn_phone``。
        value: 必须从原始日志中脱敏的精确字符串。
    """

    pii_type: str
    value: str


@dataclass(frozen=True)
class Case:
    """一条测试案例。

    同一条 ``text`` 会原封不动地交给 Regex、LLM、Hybrid。这叫控制变量：输入和
    标准答案不变，只改变检测策略。
    """

    case_id: str
    text: str
    gold: tuple[GoldItem, ...]


@dataclass(frozen=True)
class Finding:
    """检测器提出的一条敏感信息候选。

    为什么不能只返回 ``value``？

    - ``pii_type`` 用于审计“类型有没有判断对”；
    - ``start/end`` 让替换代码能精确定位，不依赖模型重写全文；
    - ``confidence`` 用于候选重叠时决定优先保留哪一条。

    ``start`` 包含，``end`` 不包含，遵守 Python 切片习惯：

        text[start:end] == value
    """

    pii_type: str
    value: str
    start: int
    end: int
    confidence: float


# 校验器接收字符串，返回 True/False。例如银行卡会使用 Luhn 校验。
Validator = Callable[[str], bool]


@dataclass(frozen=True)
class RegexRule:
    """一条 Regex 规则的完整定义。

    Attributes:
        category: 规则命中后产生的类型。
        placeholder: 替换时使用的占位符。
        pattern: 已编译的正则表达式。
        groups: 真正需要脱敏的捕获组。0 表示整段匹配。
        validator: 可选的二次校验函数。
    """

    category: str
    placeholder: str
    pattern: re.Pattern[str]
    groups: tuple[int, ...]
    validator: Validator | None = None


# ============================================================================
# 模块 4：受控测试集
# ============================================================================

# 所有数据都是为实验构造的虚构值。
#
# 为什么既有正例又有负例？
#
# - 只有正例，只能测“能否找出来”；
# - 加入负例，才能测“会不会乱删”；
# - mixed_context 把真手机号和长得像手机号的订单号放在同一句中，专门测语义消歧。
CASES: tuple[Case, ...] = (
    Case(
        case_id="structured_cn",
        text="客户身份证号11010519491231002X，手机号13800138000。",
        gold=(
            GoldItem("cn_id_card", "11010519491231002X"),
            GoldItem("cn_phone", "13800138000"),
        ),
    ),
    Case(
        case_id="structured_us",
        text=(
            "SSN 123-45-6789; Visa 4111 1111 1111 1111; "
            "ticket 123-45-6780 is not an SSN."
        ),
        gold=(
            GoldItem("us_ssn", "123-45-6789"),
            GoldItem("credit_card", "4111 1111 1111 1111"),
        ),
    ),
    Case(
        case_id="credentials",
        text=(
            "postgres://alice:S3cr3t-Pass@db.internal:5432/prod failed; "
            "retry token=not-a-real-token-but-secret"
        ),
        gold=(
            GoldItem("password", "S3cr3t-Pass"),
            GoldItem("secret", "not-a-real-token-but-secret"),
        ),
    ),
    Case(
        case_id="natural_password",
        text="用户说：我网银的登录口令是‘Blue moon over river 77’，请帮我记住。",
        gold=(GoldItem("password", "Blue moon over river 77"),),
    ),
    Case(
        case_id="address",
        text=(
            "Please ship replacements to apartment 3B, 1847 Maple Street, "
            "Portland, Oregon 97205 after Tuesday."
        ),
        gold=(
            GoldItem(
                "address",
                "apartment 3B, 1847 Maple Street, Portland, Oregon 97205",
            ),
        ),
    ),
    Case(
        case_id="medical",
        text=(
            "Chart note: patient Maria Chen, MRN-789456, was diagnosed with "
            "stage II breast cancer and starts doxorubicin Friday."
        ),
        gold=(
            GoldItem("medical_record", "MRN-789456"),
            GoldItem("medical_diagnosis", "stage II breast cancer"),
            GoldItem("treatment", "doxorubicin"),
        ),
    ),
    Case(
        case_id="passport",
        text=(
            "Traveler passport P987654321 expires 2027-04-09; "
            "booking code P987654320 is unrelated."
        ),
        gold=(GoldItem("passport", "P987654321"),),
    ),
    Case(
        case_id="financial",
        text=(
            "Wire account 4429853327 routing 123006800. "
            "Product SKU 4429853328 should remain visible."
        ),
        gold=(
            GoldItem("bank_account", "4429853327"),
            GoldItem("routing_number", "123006800"),
        ),
    ),
    Case(
        case_id="email_bearer",
        text=(
            "Authorization: Bearer fakeBearerToken1234567890; "
            "notify alice.wang@example.com."
        ),
        gold=(
            GoldItem("bearer_token", "fakeBearerToken1234567890"),
            GoldItem("email", "alice.wang@example.com"),
        ),
    ),
    Case(
        case_id="negative_numbers",
        text=(
            "Metrics: latency 13800138000 ns, build 4111111111111112 vectors, "
            "model XR-7003. None identify a person."
        ),
        gold=(),
    ),
    Case(
        case_id="negative_language",
        text=(
            "The password field must contain at least 12 characters. "
            "Never log a user's real password."
        ),
        gold=(),
    ),
    Case(
        case_id="mixed_context",
        text=(
            "Support transcript: 'call me at 13912345678'. "
            "Agent replied that order 13912345679 ships tomorrow "
            "and wrote password: hunter2xyz."
        ),
        gold=(
            GoldItem("cn_phone", "13912345678"),
            GoldItem("password", "hunter2xyz"),
        ),
    ),
)


# ============================================================================
# 模块 5：LLM Prompt 与 JSON Schema
# ============================================================================

# System Prompt 只让模型“检测并定位”，不让它直接改写日志。
# 这样 Python 才能：
#
# 1. 检查 value 是否真的存在于原文；
# 2. 独立执行替换；
# 3. 用 Gold 对 findings 判分；
# 4. 避免模型顺手改写其他非敏感内容。
SYSTEM_PROMPT = """You detect sensitive information in logs. Return exact substrings only.
Types include cn_id_card, cn_phone, us_ssn, credit_card, password, secret,
address, medical_record, medical_diagnosis, treatment, passport, bank_account,
routing_number, bearer_token, email, private_key, and api_key. Distinguish a
real disclosed value from a field name, instruction, product code, metric, or
explicit decoy. start/end are zero-based Python slice offsets and confidence is
0..1. Return JSON matching the schema; never redact or paraphrase the value."""


# Ollama 支持通过 ``format`` 参数传入 JSON Schema。
#
# 注意：Schema 只能提高“输出形状正确”的概率，不能保证内容一定判断正确。
LLM_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "value": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "type",
                    "value",
                    "start",
                    "end",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


# ============================================================================
# 模块 6：Regex 使用的校验算法
# ============================================================================

def luhn_is_valid(number: str) -> bool:
    """用 Luhn 算法验证候选银行卡号。

    正则只能找出“13～19 位数字”，但订单号等业务编号也可能长这样。Luhn 是银行卡号
    常见的校验算法，可以过滤一部分“形状像卡号、实际不是卡号”的数字。

    它不能证明某张卡真实存在，只能说明数字满足校验规则。
    """

    # 去掉空格和连字符，只留下数字。
    digits = [int(character) for character in number if character.isdigit()]

    # 常见卡号长度在 13～19 位之间。
    if not 13 <= len(digits) <= 19:
        return False

    checksum = 0
    parity = len(digits) % 2

    # 按 Luhn 规则，从特定奇偶位置开始把数字乘 2；超过 9 就减 9。
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    # 最终和能被 10 整除，说明校验通过。
    return checksum % 10 == 0


def chinese_id_is_valid(value: str) -> bool:
    """验证中国大陆 18 位身份证校验码。

    前 17 位参与加权求和，第 18 位是校验位。与 Luhn 一样，它用于降低 Regex 误报，
    不负责验证身份证是否真的属于某个人。
    """

    normalized = value.upper()
    if len(normalized) != 18 or not normalized[:17].isdigit():
        return False

    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = "10X98765432"

    weighted_sum = sum(
        int(normalized[index]) * weights[index]
        for index in range(17)
    )

    expected_check_code = check_codes[weighted_sum % 11]
    return expected_check_code == normalized[17]


# ============================================================================
# 模块 7：Regex 规则表
# ============================================================================

# 规则按列表顺序拥有优先级：越靠前，优先级越高。
# 如果两个规则命中重叠区域，后面会优先保留列表中更靠前的规则。
REGEX_RULES: tuple[RegexRule, ...] = (
    RegexRule(
        category="private_key",
        placeholder="[REDACTED_PRIVATE_KEY]",
        pattern=re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
            r"[\s\S]*?(?:"
            r"-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
            r"|(?=\Z))"
        ),
        groups=(0,),
    ),
    RegexRule(
        category="jwt",
        placeholder="[REDACTED_JWT]",
        pattern=re.compile(
            r"eyJ[A-Za-z0-9_-]{10,}\."
            r"eyJ[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}"
        ),
        groups=(0,),
    ),
    RegexRule(
        # ``postgres://user:PASSWORD@host`` 中只脱敏 PASSWORD，保留连接结构。
        category="url_credential",
        placeholder="[REDACTED_URL_CRED]",
        pattern=re.compile(r"://[^\s:/@]*:([^\s@]+)@"),
        groups=(1,),
    ),
    RegexRule(
        category="aws_access_key",
        placeholder="[REDACTED_AWS_KEY]",
        pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        groups=(0,),
    ),
    RegexRule(
        category="github_token",
        placeholder="[REDACTED_GITHUB_TOKEN]",
        pattern=re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}"
            r"|github_pat_[A-Za-z0-9_]{20,})\b"
        ),
        groups=(0,),
    ),
    RegexRule(
        category="slack_token",
        placeholder="[REDACTED_SLACK_TOKEN]",
        pattern=re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        groups=(0,),
    ),
    RegexRule(
        category="google_api_key",
        placeholder="[REDACTED_GOOGLE_API_KEY]",
        pattern=re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        groups=(0,),
    ),
    RegexRule(
        category="api_key",
        placeholder="[REDACTED_API_KEY]",
        pattern=re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        groups=(0,),
    ),
    RegexRule(
        # 整段匹配 ``Bearer TOKEN``，但 groups=(1,) 表示只删除 TOKEN。
        category="bearer_token",
        placeholder="[REDACTED_BEARER_TOKEN]",
        pattern=re.compile(r"(?i)\bBearer\s+([A-Za-z0-9._~+/=-]{10,})"),
        groups=(1,),
    ),
    RegexRule(
        category="basic_auth",
        placeholder="[REDACTED_BASIC_AUTH]",
        pattern=re.compile(
            r"(?i)\bAuthorization\s*:\s*Basic\s+([A-Za-z0-9+/=]{4,})"
        ),
        groups=(1,),
    ),
    RegexRule(
        category="secret_assignment",
        placeholder="[REDACTED_SECRET]",
        pattern=re.compile(
            r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|"
            r"access[_-]?key|auth|credential)[\"']?\s*[=:]\s*"
            r"(?:\"([^\"]{4,})\"|'([^']{4,})'|([^\s\"',}]{4,}))"
        ),
        # 双引号、单引号、无引号三种写法只会命中其中一个捕获组。
        groups=(1, 2, 3),
    ),
    RegexRule(
        category="email",
        placeholder="[REDACTED_EMAIL]",
        pattern=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        groups=(0,),
    ),
    RegexRule(
        category="credit_card",
        placeholder="[REDACTED_CREDIT_CARD]",
        pattern=re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        groups=(0,),
        validator=luhn_is_valid,
    ),
    RegexRule(
        category="iban",
        placeholder="[REDACTED_IBAN]",
        pattern=re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
        groups=(0,),
    ),
    RegexRule(
        category="us_ssn",
        placeholder="[REDACTED_SSN]",
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        groups=(0,),
    ),
    RegexRule(
        category="cn_id_card",
        placeholder="[REDACTED_ID_CARD]",
        pattern=re.compile(r"\b\d{17}[\dXx]\b"),
        groups=(0,),
        validator=chinese_id_is_valid,
    ),
    RegexRule(
        category="cn_phone",
        placeholder="[REDACTED_PHONE]",
        pattern=re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
        groups=(0,),
    ),
    RegexRule(
        category="ip_address",
        placeholder="[REDACTED_IP]",
        pattern=re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
        ),
        groups=(0,),
    ),
)


# Regex 内部类型名与实验 Gold 类型名不完全一致，因此需要做别名映射。
REGEX_TYPE_ALIASES: dict[str, str] = {
    "url_credential": "password",
    "secret_assignment": "secret",
    "us_ssn": "us_ssn",
    "credit_card": "credit_card",
    "cn_id_card": "cn_id_card",
    "cn_phone": "cn_phone",
    "bearer_token": "bearer_token",
    "email": "email",
    "api_key": "api_key",
    "private_key": "private_key",
}


# ============================================================================
# 模块 8：通用的区间与候选处理函数
# ============================================================================

def ranges_overlap(first: Finding, second: Finding) -> bool:
    """判断两个左闭右开区间是否重叠。

    不重叠只有两种情况：

    1. first 完全位于 second 左边；
    2. first 完全位于 second 右边。

    对这两种情况取反，就是“发生重叠”。
    """

    first_before_second = first.end <= second.start
    first_after_second = first.start >= second.end
    return not (first_before_second or first_after_second)


def choose_non_overlapping(findings: list[Finding]) -> list[Finding]:
    """从可能重叠的候选中选择最终候选。

    排序规则：

    1. confidence 高的优先；
    2. confidence 相同，位置靠前的优先。

    这不是唯一正确的冲突策略，但它是清晰、确定、便于复现的策略。
    """

    accepted: list[Finding] = []

    for candidate in sorted(
        findings,
        key=lambda item: (-item.confidence, item.start),
    ):
        if any(ranges_overlap(candidate, existing) for existing in accepted):
            continue
        accepted.append(candidate)

    return sorted(accepted, key=lambda item: (item.start, item.end))


def normalize_findings(
    text: str,
    raw_findings: list[dict[str, Any]],
) -> list[Finding]:
    """把 LLM 或混合来源的动态字典清洗为可信的 Finding。

    模型常见问题：

    - value 外面多了一层引号；
    - start/end 算错；
    - confidence 超出 0～1；
    - 同一条发现重复返回；
    - value 根本不存在于原文。

    本函数负责做确定性校验。它不会判断“这个值在语义上是否真的敏感”，只保证返回
    的位置能在原文中定位。
    """

    normalized: list[Finding] = []
    seen: set[tuple[int, int, str, str]] = set()

    for raw in raw_findings or []:
        # 模型可能返回 null、数字等，所以先统一转成字符串。
        value = str(raw.get("value") or "")

        # 去掉模型偶尔附带的首尾空白与引号，但不改写字符串内部内容。
        value = value.strip(" \t\n\r'\"“”‘’")
        if not value:
            continue

        pii_type = str(raw.get("type") or "unknown").lower()

        # 解析位置失败时先用 -1 表示无效，稍后尝试按 value 搜索原文。
        try:
            start = int(raw.get("start", -1))
            end = int(raw.get("end", -1))
        except (TypeError, ValueError):
            start = -1
            end = -1

        # 只有“位置合法并且切片精确等于 value”才信任模型给的位置。
        position_is_valid = (
            0 <= start < end <= len(text)
            and text[start:end] == value
        )

        if not position_is_valid:
            # 位置错了，但 value 可能是对的，因此在原文中搜索精确 value。
            # 局限：同一个 value 出现多次时，find() 只返回第一次。
            start = text.find(value)
            end = start + len(value) if start >= 0 else -1

        # value 不存在于原文，说明无法安全执行替换，直接丢弃。
        if start < 0:
            continue

        try:
            confidence = float(raw.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5

        # 把置信度限制在 0～1，避免异常值影响重叠排序。
        confidence = max(0.0, min(1.0, confidence))

        deduplication_key = (start, end, pii_type, value)
        if deduplication_key in seen:
            continue
        seen.add(deduplication_key)

        normalized.append(
            Finding(
                pii_type=pii_type,
                value=value,
                start=start,
                end=end,
                confidence=confidence,
            )
        )

    return choose_non_overlapping(normalized)


def redact(text: str, findings: list[Finding]) -> str:
    """根据精确区间把敏感值替换成带类型的占位符。

    为什么从右向左替换？

    假设先替换左边的短字符串，字符串总长度会改变，右边候选的旧 start/end 就失效。
    从右向左替换时，右侧变化不会影响左侧下标。
    """

    accepted = choose_non_overlapping(findings)
    result = text

    for finding in sorted(accepted, key=lambda item: item.start, reverse=True):
        placeholder = f"[REDACTED_{finding.pii_type.upper()}]"
        result = (
            result[:finding.start]
            + placeholder
            + result[finding.end:]
        )

    return result


# ============================================================================
# 模块 9：Regex 检测器
# ============================================================================

def regex_findings(text: str) -> tuple[list[Finding], float]:
    """使用规则表检测敏感信息，并返回候选和毫秒延迟。"""

    started_at = time.perf_counter()

    # 候选先带 priority；Regex 没有真实置信度，所以后面统一填 1.0。
    candidates: list[tuple[int, Finding]] = []

    for priority, rule in enumerate(REGEX_RULES):
        for match in rule.pattern.finditer(text):
            selected_start = -1
            selected_end = -1

            # secret_assignment 有三个可选捕获组：双引号、单引号、无引号。
            # 一次匹配只会有一个组真正参与，另外两个组的 span 是 (-1, -1)。
            for group_number in rule.groups:
                group_start, group_end = match.span(group_number)
                if group_start >= 0:
                    selected_start = group_start
                    selected_end = group_end
                    break

            if selected_start < 0:
                continue

            value = text[selected_start:selected_end]

            # 有校验器的规则必须同时满足“形状匹配”和“校验算法通过”。
            if rule.validator is not None and not rule.validator(value):
                continue

            experiment_type = REGEX_TYPE_ALIASES.get(
                rule.category,
                rule.category,
            )

            candidates.append(
                (
                    priority,
                    Finding(
                        pii_type=experiment_type,
                        value=value,
                        start=selected_start,
                        end=selected_end,
                        confidence=1.0,
                    ),
                )
            )

    # Regex 的重叠策略和 LLM 略有不同：先按规则优先级，再按位置。
    accepted: list[Finding] = []
    for _, candidate in sorted(
        candidates,
        key=lambda pair: (pair[0], pair[1].start),
    ):
        if any(ranges_overlap(candidate, existing) for existing in accepted):
            continue
        accepted.append(candidate)

    accepted.sort(key=lambda item: (item.start, item.end))

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return accepted, elapsed_ms


# ============================================================================
# 模块 10：Ollama LLM 检测器
# ============================================================================

def to_plain_data(value: Any) -> Any:
    """把 Ollama SDK 对象递归转换成普通 JSON 数据。

    不同版本的 Ollama Python SDK 可能返回：

    - 普通 dict；
    - 带 ``model_dump()`` 的 Pydantic 风格对象；
    - 内部包含更多 SDK 对象的列表。

    保存实验回执前，需要把它们统一变成 dict/list/str/number。
    """

    if hasattr(value, "model_dump"):
        return to_plain_data(value.model_dump())
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_data(item) for item in value]
    if isinstance(value, (datetime, date)):
        # ISO 8601 是人类可读、跨语言也容易解析的时间表示。
        return value.isoformat()
    return value


class ModelOutputError(RuntimeError):
    """模型请求完成了，但返回内容无法成为合法 findings。

    这和“连不上 Ollama”不同：前者是被测模型的输出质量问题，实验应该记录并继续；
    后者是基础设施问题，整次实验通常应该停止。

    ``latency_ms`` 被保存在异常对象中，使失败调用也能计入延迟。
    """

    def __init__(self, message: str, latency_ms: float) -> None:
        super().__init__(message)
        self.latency_ms = latency_ms


class OllamaDetector:
    """一个很薄的本地模型调用封装。

    这里故意不使用 LangChain，因为任务只需要一次明确的模型请求。直接使用 SDK 能让
    输入、输出、Schema、耗时都清楚地暴露出来，更适合学习和受控评测。
    """

    def __init__(self, model: str, host: str) -> None:
        # 把 import 放在构造函数内部：
        # 只跑 ``--mode regex`` 时，即使没安装 ollama 包也能使用 Regex。
        try:
            import ollama
        except ImportError as error:
            raise RuntimeError(
                "需要 LLM/Hybrid 模式，但没有安装 ollama Python 包。"
                "请运行：python -m pip install ollama"
            ) from error

        self.model = model
        self.host = host
        # ``ollama.Client`` 内部使用 httpx。httpx 默认 ``trust_env=True``，会读取
        # HTTP_PROXY / HTTPS_PROXY 等环境或系统代理设置。在某些 Mac 配置中，即使
        # 目标地址是 127.0.0.1，本地请求也可能被错误送给代理并得到 502。
        #
        # 本实验明确只连接本机 Ollama，所以禁用环境代理既更安全，也更可复现。
        self.client = ollama.Client(host=host, trust_env=False)

        # receipts 保存每次真实模型调用的请求、响应、耗时和 token 统计。
        self.receipts: list[dict[str, Any]] = []

    def show_model(self) -> dict[str, Any]:
        """读取真实本地模型信息，用于确认实验到底调用了哪个模型。"""

        response = self.client.show(self.model)
        plain = to_plain_data(response)
        return plain if isinstance(plain, dict) else {"raw": plain}

    def detect(
        self,
        text: str,
        purpose: str,
    ) -> tuple[list[Finding], float]:
        """调用一次本地模型，返回标准化 findings 和毫秒延迟。"""

        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "format": LLM_OUTPUT_SCHEMA,
            # 对 Qwen3 显式关闭 thinking，防止短抽取任务把输出预算全部花在
            # ``message.thinking``，导致最终 ``message.content`` 为空。
            "think": ENABLE_THINKING,
            "options": {
                "temperature": TEMPERATURE,
                "seed": SEED,
                "num_predict": MAX_OUTPUT_TOKENS,
            },
            "stream": False,
        }

        started_at = time.perf_counter()
        response = self.client.chat(**request)
        latency_ms = (time.perf_counter() - started_at) * 1000

        response_data = to_plain_data(response)
        if not isinstance(response_data, dict):
            raise RuntimeError("Ollama 返回值不是字典结构。")

        # 无论后续 JSON 能否解析，都先保存真实回执。失败输出本身就是实验结果，
        # 不能只保存成功样本。
        receipt: dict[str, Any] = {
            "purpose": purpose,
            "provider": "ollama-local",
            "endpoint": self.host,
            "model": self.model,
            "request": request,
            "response": response_data,
            "latency_ms": round(latency_ms, 3),
            "usage": {
                "prompt_tokens": response_data.get("prompt_eval_count"),
                "completion_tokens": response_data.get("eval_count"),
            },
            "parse_status": "received",
        }
        self.receipts.append(receipt)

        message = response_data.get("message")
        if not isinstance(message, dict):
            receipt["parse_status"] = "missing_message"
            raise ModelOutputError(
                "Ollama 返回值缺少 message 对象。",
                latency_ms,
            )

        raw_content = message.get("content")
        if not isinstance(raw_content, str):
            receipt["parse_status"] = "missing_content"
            raise ModelOutputError(
                "Ollama 返回值缺少 message.content 字符串。",
                latency_ms,
            )

        # 模型返回的是“JSON 字符串”，所以还要用 json.loads 解析一次。
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as error:
            receipt["parse_status"] = "invalid_json"

            # 控制终端错误长度；完整原始响应已经保存在 receipt 中。
            preview = raw_content[:300]
            if len(raw_content) > len(preview):
                preview += "..."

            raise ModelOutputError(
                f"模型没有返回合法 JSON：{preview!r}",
                latency_ms,
            ) from error

        raw_findings = parsed.get("findings") if isinstance(parsed, dict) else None
        if not isinstance(raw_findings, list):
            receipt["parse_status"] = "findings_not_array"
            raise ModelOutputError(
                "模型 JSON 中的 findings 不是数组。",
                latency_ms,
            )

        findings = normalize_findings(text, raw_findings)
        receipt["parse_status"] = "ok"

        return findings, latency_ms


# ============================================================================
# 模块 11：Hybrid 检测器
# ============================================================================

def hybrid_findings(
    text: str,
    detector: OllamaDetector,
    case_id: str,
) -> tuple[list[Finding], float, str | None]:
    """运行当前官方思路：Regex 先替换，LLM 再检查剩余文本。

    这是“补漏型 Hybrid”：

    - Regex 已经发现的内容不再让 LLM 重复处理；
    - LLM 负责在剩余文本中寻找自然语言地址、诊断、密码等；
    - Regex 若发生误删，LLM 无法恢复，因为它看到的已经是占位符。
    """

    regex_hits, regex_latency_ms = regex_findings(text)

    # 先根据 Regex 结果真正替换原文。
    regex_redacted_text = redact(text, regex_hits)

    # LLM 读取的是 Regex 处理后的文本，而不是原文。
    try:
        remaining_hits, llm_latency_ms = detector.detect(
            regex_redacted_text,
            purpose=f"hybrid-after-regex:{case_id}",
        )
    except ModelOutputError as error:
        # Hybrid 至少还有 Regex 第一阶段的结果，因此不需要让整条链路完全失败。
        # 返回 Regex findings，同时用 error 告诉上层：这次是降级结果，不是完整 Hybrid。
        total_latency_ms = regex_latency_ms + error.latency_ms
        return regex_hits, total_latency_ms, str(error)

    # LLM 的 start/end 属于 regex_redacted_text。
    # 最终评估必须基于原文，所以要根据精确 value 映射回原文位置。
    mapped_hits: list[dict[str, Any]] = []
    for finding in remaining_hits:
        original_start = text.find(finding.value)
        if original_start < 0:
            # 在原文中找不到就不能安全替换，直接丢弃。
            continue

        mapped_hits.append(
            {
                "type": finding.pii_type,
                "value": finding.value,
                "start": original_start,
                "end": original_start + len(finding.value),
                "confidence": finding.confidence,
            }
        )

    # 把 Regex findings 也转成普通字典，统一交给 normalize_findings 去重和处理重叠。
    combined_raw = [
        {
            "type": finding.pii_type,
            "value": finding.value,
            "start": finding.start,
            "end": finding.end,
            "confidence": finding.confidence,
        }
        for finding in regex_hits
    ] + mapped_hits

    combined = normalize_findings(text, combined_raw)
    total_latency_ms = regex_latency_ms + llm_latency_ms
    return combined, total_latency_ms, None


# ============================================================================
# 模块 12：指标计算
# ============================================================================

def evaluate_case(
    case: Case,
    strategy: str,
    findings: list[Finding],
    latency_ms: float,
) -> dict[str, Any]:
    """把某条策略的预测与人工 Gold 比较。"""

    # typed 集合同时比较类型和值。
    gold_typed = {(item.pii_type, item.value) for item in case.gold}
    predicted_typed = {
        (finding.pii_type, finding.value)
        for finding in findings
    }

    # value 集合只比较“删没删对字符串”，不比较类型。
    gold_values = {item.value for item in case.gold}
    predicted_values = {finding.value for finding in findings}

    true_positive_values = gold_values & predicted_values

    # Precision：预测要删的内容里，有多少真的应该删。
    if predicted_values:
        precision = len(true_positive_values) / len(predicted_values)
    else:
        # 没有 Gold，也没有预测时，Precision 记为 1；
        # 有 Gold 却什么都没预测时，Precision 记为 0。
        precision = 1.0 if not gold_values else 0.0

    # Recall：Gold 中应该删的内容，有多少被找到了。
    if gold_values:
        recall = len(true_positive_values) / len(gold_values)
    else:
        # 纯负例没有任何敏感信息可漏，Recall 记为 1。
        recall = 1.0

    # Typed Exact：类型和值都必须匹配。
    if gold_typed:
        typed_exact = len(gold_typed & predicted_typed) / len(gold_typed)
    else:
        typed_exact = 1.0 if not predicted_typed else 0.0

    sanitized_text = redact(case.text, findings)

    # Gold 值在脱敏后仍然存在，就是真正的残余泄漏。
    residual_leaks = [
        value
        for value in gold_values
        if value in sanitized_text
    ]

    # 预测值不在 Gold 中，意味着这段非敏感文字被误删。
    false_redacted_characters = sum(
        len(finding.value)
        for finding in findings
        if finding.value not in gold_values
    )

    # 分母是原文中的非敏感字符数，至少设为 1，避免除以 0。
    non_sensitive_characters = max(
        1,
        len(case.text) - sum(len(value) for value in gold_values),
    )

    utility = max(
        0.0,
        1.0 - false_redacted_characters / non_sensitive_characters,
    )

    return {
        "case_id": case.case_id,
        "strategy": strategy,
        "findings": [asdict(finding) for finding in findings],
        "precision": precision,
        "recall": recall,
        "typed_exact": typed_exact,
        "residual_leaks": residual_leaks,
        "utility": utility,
        "latency_ms": round(latency_ms, 3),
        "sanitized_text": sanitized_text,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """把同一策略在多条案例上的结果聚合成摘要。"""

    if not rows:
        return {
            "cases": 0,
            "ok_cases": 0,
            "degraded_cases": 0,
            "failed_cases": 0,
            "mean_precision": 0.0,
            "mean_recall": 0.0,
            "mean_typed_exact": 0.0,
            "residual_leaks": 0,
            "mean_utility": 0.0,
            "mean_latency_ms": 0.0,
        }

    return {
        "cases": len(rows),
        "ok_cases": sum(row.get("status") == "ok" for row in rows),
        "degraded_cases": sum(row.get("status") == "degraded" for row in rows),
        "failed_cases": sum(row.get("status") == "failed" for row in rows),
        "mean_precision": mean(float(row["precision"]) for row in rows),
        "mean_recall": mean(float(row["recall"]) for row in rows),
        "mean_typed_exact": mean(float(row["typed_exact"]) for row in rows),
        "residual_leaks": sum(len(row["residual_leaks"]) for row in rows),
        "mean_utility": mean(float(row["utility"]) for row in rows),
        "mean_latency_ms": mean(float(row["latency_ms"]) for row in rows),
    }


# ============================================================================
# 模块 13：命令行、案例选择与控制流程
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """定义并解析命令行参数。"""

    parser = argparse.ArgumentParser(
        description=(
            "实验 3-3 完整注释版：比较 Regex、Local LLM、Hybrid 日志脱敏。"
        )
    )

    parser.add_argument(
        "--mode",
        choices=("regex", "llm", "hybrid", "all"),
        default="regex",
        help=(
            "运行策略。regex 不需要 Ollama；all 会为每条案例调用两次 LLM："
            "一次直接 LLM，一次 Hybrid 的第二阶段。"
        ),
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama 模型名，默认 {DEFAULT_MODEL}。",
    )

    parser.add_argument(
        "--ollama-host",
        default=DEFAULT_OLLAMA_HOST,
        help=f"Ollama 地址，默认 {DEFAULT_OLLAMA_HOST}。",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只运行前 N 条案例；不传则运行全部。",
    )

    parser.add_argument(
        "--case-id",
        default=None,
        help="只运行指定 case_id；它的优先级高于 --limit。",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="可选：把完整结果写入指定 JSON 文件。",
    )

    return parser.parse_args()


def select_cases(case_id: str | None, limit: int | None) -> list[Case]:
    """根据命令行参数选择要运行的案例。"""

    if case_id is not None:
        selected = [case for case in CASES if case.case_id == case_id]
        if not selected:
            known_ids = ", ".join(case.case_id for case in CASES)
            raise ValueError(
                f"不存在 case_id={case_id!r}。可选值：{known_ids}"
            )
        return selected

    if limit is None:
        return list(CASES)

    if limit <= 0:
        raise ValueError("--limit 必须大于 0。")

    return list(CASES[:limit])


def strategies_for_mode(mode: str) -> tuple[str, ...]:
    """把 all 展开成三种策略，避免主循环中到处判断字符串。"""

    if mode == "all":
        return ("regex", "llm", "hybrid")
    return (mode,)


def print_case_result(row: dict[str, Any]) -> None:
    """以适合人阅读的形式打印一条案例结果。"""

    print(
        f"  [{row['strategy']} / {row.get('status', 'ok')}] "
        f"P={row['precision']:.3f} "
        f"R={row['recall']:.3f} "
        f"Typed={row['typed_exact']:.3f} "
        f"Leaks={len(row['residual_leaks'])} "
        f"Utility={row['utility']:.3f} "
        f"Latency={row['latency_ms']:.3f}ms"
    )
    print(f"    脱敏结果：{row['sanitized_text']}")
    if row.get("error"):
        print(f"    模型输出错误：{row['error']}")


def main() -> int:
    """程序入口：准备依赖、遍历案例、运行策略、聚合并可选落盘。"""

    args = parse_arguments()

    try:
        selected_cases = select_cases(args.case_id, args.limit)
    except ValueError as error:
        print(f"参数错误：{error}")
        return 2

    selected_strategies = strategies_for_mode(args.mode)

    # 只有 LLM/Hybrid 才需要创建 Ollama 客户端。
    needs_llm = any(
        strategy in {"llm", "hybrid"}
        for strategy in selected_strategies
    )

    detector: OllamaDetector | None = None
    model_info: dict[str, Any] | None = None

    if needs_llm:
        try:
            detector = OllamaDetector(args.model, args.ollama_host)
            model_info = detector.show_model()
        except Exception as error:
            print(f"Ollama 初始化失败：{error}")
            print("请确认已经执行：ollama serve 与 ollama pull qwen3:0.6b")
            return 1

    # results[strategy] 是该策略的所有逐案例结果。
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for case_index, case in enumerate(selected_cases, start=1):
        print(f"\n[{case_index}/{len(selected_cases)}] 案例：{case.case_id}")
        print(f"  原文：{case.text}")

        for strategy in selected_strategies:
            strategy_status = "ok"
            strategy_error: str | None = None

            try:
                if strategy == "regex":
                    findings, latency_ms = regex_findings(case.text)

                elif strategy == "llm":
                    # 这里的 assert 主要帮助类型检查器理解 detector 不可能为 None。
                    assert detector is not None
                    try:
                        findings, latency_ms = detector.detect(
                            case.text,
                            purpose=f"llm:{case.case_id}",
                        )
                    except ModelOutputError as error:
                        # 直接 LLM 没有其他检测结果可以回退，因此按空 findings 评估。
                        # 这会如实表现为 Recall 下降、Gold 值全部残余泄漏。
                        findings = []
                        latency_ms = error.latency_ms
                        strategy_status = "failed"
                        strategy_error = str(error)

                elif strategy == "hybrid":
                    assert detector is not None
                    findings, latency_ms, strategy_error = hybrid_findings(
                        case.text,
                        detector,
                        case.case_id,
                    )
                    if strategy_error is not None:
                        strategy_status = "degraded"

                else:
                    # argparse 已限制 choices，理论上永远走不到这里。
                    raise RuntimeError(f"未知策略：{strategy}")

            except Exception as error:
                print(f"  [{strategy}] 执行失败：{error}")
                return 1

            row = evaluate_case(
                case=case,
                strategy=strategy,
                findings=findings,
                latency_ms=latency_ms,
            )
            row["status"] = strategy_status
            row["error"] = strategy_error
            results[strategy].append(row)
            print_case_result(row)

    summaries = {
        strategy: aggregate(rows)
        for strategy, rows in results.items()
    }

    print("\n=== 聚合摘要 ===")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))

    evidence: dict[str, Any] = {
        "configuration": {
            "mode": args.mode,
            "model": args.model if needs_llm else None,
            "ollama_host": args.ollama_host if needs_llm else None,
            "temperature": TEMPERATURE if needs_llm else None,
            "seed": SEED if needs_llm else None,
            "thinking": ENABLE_THINKING if needs_llm else None,
            "model_info": model_info,
        },
        "dataset": [
            {
                "case_id": case.case_id,
                "text": case.text,
                "gold": [asdict(item) for item in case.gold],
            }
            for case in selected_cases
        ],
        "summary": summaries,
        "results": dict(results),
        "receipts": detector.receipts if detector is not None else [],
    }

    if args.output is not None:
        # 创建父目录，让 ``--output tmp/results/result.json`` 也能直接使用。
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n完整结果已写入：{args.output.resolve()}")

    return 0


# Python 文件被直接执行时，__name__ 等于 "__main__"。
# 如果它以后被别的测试文件 import，这里不会自动运行整个实验。
if __name__ == "__main__":
    raise SystemExit(main())
