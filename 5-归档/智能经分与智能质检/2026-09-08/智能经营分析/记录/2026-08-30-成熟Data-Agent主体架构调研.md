# 2026-08-30 成熟 Data Agent 主体架构调研

> 调研口径：优先使用已经公开产品化的官方文档与明确披露生产使用的官方工程文章。只归纳主体拓扑，不将官方未披露的内部实现推测为事实。

## 原始问题

- 现在成熟 Data Agent 的主体架构是什么样的？
- 不需要深入每个组件，主要看它们是“一个主 Agent + 多个专业 Agent”，还是其他形态。

## 用户理解

> 当前假设：我们可能是一个主 Agent，加一个分析 Agent，加一个取数 Agent，大概是这样一种组成结构。

## Codex 反馈

### 最重要的归纳

成熟 Data Agent 并没有统一的“三个 Agent”结构。目前公开架构更稳定的共性是：

```text
单一对话入口 / 主 Agent
        ↓
计划与受控编排
        ↓
按需调用专业能力
  ├─业务知识 / 语义层
  ├─取数 / Text-to-SQL
  ├─计算与分析
  └─图表与报告
        ↓
校验、权限、成本与可观测性门禁
```

专业能力可能被实现为子 Agent，也可能只是工具、查询引擎或确定性 Workflow。因此，判断架构时应看“谁负责规划、谁执行、谁强制边界”，不应只数 Agent 个数。

### 公开案例的主体拓扑

| 案例 | 官方公开的主体形态 | 归类 |
| --- | --- | --- |
| Snowflake Cortex Agents | 一个负责拆分子任务和选择工具的编排 Agent，下挂 Cortex Analyst、Cortex Search、代码执行、图表和自定义工具 | 主 Agent + 专业工具 |
| Microsoft Fabric data agent | 问题经 Orchestrator 选择数据源，再调用 NL2SQL / NL2DAX / NL2KQL 工具生成、校验、执行查询，最后格式化结果 | 受控编排 + 查询工具，默认不是三 Agent |
| Databricks Genie Agents | 复合 AI 系统；普通模式生成只读 SQL，Agent mode 对复杂问题拆解子任务、执行多次 SQL 并输出结构化报告和可视化 | 单数据 Agent 的多步分析循环 |
| Google Conversational Analytics | 一个可组装的数据 Agent，下挂 Text-to-SQL、语义查询、上下文检索、Code Interpreter、图表和解释工具；需要时才外包成多 Agent | 主 Agent + 可组装工具 |
| OpenAI 内部 Data Agent | 一个通用分析 Agent 端到端做数据发现、SQL、迭代自修正、Notebook/报告；外围由多层数据上下文、知识、记忆、可复用 Workflow、评测和权限支撑 | 强通用 Agent + 工具/上下文 |
| Uber QueryGPT | 流水线串联 Intent Agent、Table Agent、Column Prune Agent，再进入 SQL 生成；关键表选择引入人工确认 | 专业 Agent 流水线 |
| Amazon RRDA | 先用意图/领域分类路由，中央 Bedrock Agent 编排指标知识检索、Schema 获取和 SQL 生成/校验 Action Groups，可视化另走 QuickSight 分支 | 受控路由 + 中央 Agent + 专业动作 |

### 三种常见架构家族

1. **主 Agent + 工具：最常见的产品化形态**
   - 主 Agent 负责对话、澄清、高层规划和结果组装。
   - 取数、检索、计算、绘图通常是受权限约束的工具或服务，不一定是自治 Agent。
   - Snowflake、Fabric 和 Google 公开架构都接近这一形态。

2. **专业 Agent 流水线：适合把稳定失败点单独优化**
   - 将意图识别、数据域/表选择、Schema 裁剪、SQL 生成和校验拆成可独立评测的阶段。
   - Uber QueryGPT 是典型例子。这里的“Agent”常常只是责任单一的 LLM 节点，不是对等协作的完整智能体。

3. **单强 Agent / 分析运行时：适合开放式、多步分析**
   - 一个 Agent 在受限循环内自行拆解、多次取数、执行代码、检查中间结果和产出报告。
   - OpenAI 内部 Data Agent 和 Databricks Genie Agent mode 更接近这种形态。

### 对当前智能经营分析架构的映射（AI 草案 / 待确认）

“主 Agent + 分析 Agent + 取数 Agent”是合理的主体分工，但更接近成熟系统的严格表达是：

```text
主 Agent：对话、通用澄清、高层计划、最终组装
    ↓
受控编排器：状态、准入、权限、循环上限、失败停止
    ├─ 取数能力：简单查询是工具/引擎；需多步 Schema 发现和 SQL 修复时才升级为 Agent
    ├─ 分析 Agent：仅承接需要多步取数、解释、下钻和报告的完整分析任务
    └─ 口径/知识、绘图、发布等受控工具
```

其中，取数能力是否一定要叫“取数 Agent”，不是架构成熟度的关键。它是否有独立目标、内部多步决策、错误修复循环和独立评测，才决定它是 Agent 还是工具。

### 后续追问：LangGraph 中主 Agent 怎样调用受控编排器？

#### 用户原始问题

> 如果用 LangGraph 实现，主 Agent 规划之后，它怎么去调用受控编排器？技术实现是怎么做的？

#### Codex 反馈

这里存在一个控制方向的关键纠正：**通常不是主 Agent 规划完再调用编排器，而是已经运行的 LangGraph 编排器调用主 Agent 节点。**

```text
应用入口 graph.invoke(initial_state)
        ↓
LangGraph Runtime 调用 main_agent 节点
        ↓
main_agent 只返回结构化 Plan / 状态更新
        ↓
代码校验 Plan 的完整性、权限和可执行性
        ↓
conditional edge / Command 选择已注册节点
        ↓
LangGraph Runtime 调用取数子图或分析子图
```

推荐的受控实现是“模型提议，代码准入，图执行”：

```python
class RootState(TypedDict, total=False):
    messages: list
    plan: dict
    plan_errors: list[str]
    evidence: dict
    analysis_result: dict
    status: str


def main_agent_node(state: RootState) -> dict:
    plan = planner_model.with_structured_output(Plan).invoke(state["messages"])
    return {"plan": plan.model_dump(), "status": "planned"}


def validate_plan_node(state: RootState) -> dict:
    errors = validate_plan(state["plan"])
    return {
        "plan_errors": errors,
        "status": "plan_rejected" if errors else "plan_accepted",
    }


def route_after_plan(state: RootState) -> str:
    if state["status"] == "plan_rejected":
        return "clarify_or_safe_fail"
    return {
        "query_data": "data_agent",
        "data_analysis": "analysis_agent",
        "data_knowledge": "knowledge_tools",
    }[state["plan"]["intent"]]


builder = StateGraph(RootState)
builder.add_node("main_agent", main_agent_node)
builder.add_node("validate_plan", validate_plan_node)
builder.add_node("data_agent", data_subgraph)
builder.add_node("analysis_agent", analysis_subgraph)
builder.add_node("knowledge_tools", knowledge_node)
builder.add_node("clarify_or_safe_fail", clarify_or_safe_fail_node)

builder.add_edge(START, "main_agent")
builder.add_edge("main_agent", "validate_plan")
builder.add_conditional_edges(
    "validate_plan",
    route_after_plan,
    {
        "data_agent": "data_agent",
        "analysis_agent": "analysis_agent",
        "knowledge_tools": "knowledge_tools",
        "clarify_or_safe_fail": "clarify_or_safe_fail",
    },
)
```

其中：

- `main_agent_node` 可以自主理解和规划，但它不直接获得任意跳转权限。
- `validate_plan_node` 将必须保证的规则保留在 Python/runtime，例如指标 ID、时间范围、用户权限、成本预算和必需字段。
- `route_after_plan` 只能返回白名单中已注册的节点，这就是外层受控路由。
- `data_subgraph` 和 `analysis_subgraph` 可以是编译好的子图；如果子图与父图 State 不同，再用 wrapper node 做输入/输出转换。
- 开放分析中，分析子图可返回 `next_need=query_data` 和标准 `QuerySpec`，再由父图路由到取数子图；这比让分析 Agent 绕过父图直接访问数据底座更受控。

LangGraph 也允许节点返回 `Command(update=..., goto=...)`，在一次返回中同时更新 State 和路由。但对当前项目，默认优先使用“结构化 Plan + 独立校验节点 + conditional edges”，因为这样最容易单独评测规划、准入和路由。如果使用 `Command`，也应由代码先校验模型输出，再将它映射到有限的 `goto` 目标，不应将模型生成的任意字符串直接作为节点名。

当前 E2 复现已经实现了这一模式的缩小版：

1. `clarification_agent` 通过 `submit_clarification` 提交结构化决策；
2. `_validate_ready_request` 与 `apply_clarification_decision` 由代码校验并写入标准 State；
3. `route_after_decision` 只能在 `query_data / data_knowledge / data_analysis / ask_human / safe_fail` 中选择；
4. `StateGraph.add_conditional_edges` 让 runtime 执行真正的下一节点。

因此，后续并不需要新造一个“编排器 API”给主 Agent 调用；需要做的是把当前的单层意图路由扩展为“主 Agent 产生 `AnalysisTask` → 代码校验 → 父图路由到分析子图/取数子图”。

### 后续追问：计划是一步一步执行，还是一次并行派发？

#### 用户原始问题

> 主 Agent 是先派取数 Agent 做一部分，拿到结果再派下一个任务，还是一开始就把三种数分配给三个取数 Agent 并行处理，拿到数后再调分析 Agent？子 Agent 是否以工具形式暴露？分析场景中应由主 Agent 还是分析 Agent 调取数？

#### Codex 反馈

通用做法是**分层计划 + 依赖驱动执行**，不是固定只选串行或并行：

- 已经能确定、互不依赖的取数任务，组成一个 `QuerySpec` 批次并行执行。
- 必须先观察中间结果才知道下钻方向的任务，等证据返回后再生成下一批 `QuerySpec`。
- 因此完整执行形态通常是“批次内并行，批次之间顺序、可自适应”。

当前项目已确认的两级规划边界应保持：

1. **主 Agent 生成高层 `AnalysisTask`**：明确用户目标、业务范围、指标/对象、时间和对比口径、分析模式、交付物、预算与停止边界；不展开全部 SQL 和每一次下钻顺序。
2. **分析 Agent 生成详细 `AnalysisPlan`**：提出假设、初始证据需求、可并行查询批次、依赖关系、结果解释、后续下钻与报告草稿。

一个高层 `AnalysisTask` 可以是：

```json
{
  "goal": "解释近一周准时保保费下降的原因",
  "scope": {
    "metric_ids": ["premium_income"],
    "current_period": ["2026-08-24", "2026-08-30"],
    "comparison": "previous_period",
    "business_event": "准时保"
  },
  "analysis_mode": "open_analysis",
  "deliverable": "有证据的原因排序与下钻过程",
  "constraints": {
    "read_only": true,
    "max_query_batches": 4,
    "max_total_queries": 12
  },
  "completion_criteria": [
    "解释总量与环比变化",
    "定位主要贡献维度",
    "结论可回溯到 DataEvidence"
  ]
}
```

分析 Agent 再将它转为运行中计划：

```json
{
  "hypotheses": [
    "整体流量下降",
    "某渠道贡献下降",
    "某商户组发生异常"
  ],
  "query_batches": [
    {
      "batch_id": "baseline",
      "parallel": true,
      "queries": [
        "当期与对比期总保费",
        "按渠道的保费变化",
        "按商户的保费变化"
      ]
    }
  ],
  "conditional_steps": [
    "如某渠道贡献超过阈值，下钻该渠道的商户与日趋势",
    "如证据不足，生成新 QuerySpec；否则进入报告"
  ]
}
```

执行链路应为：

```text
主 Agent：澄清 + 组装 AnalysisTask
        ↓
父图准入校验
        ↓
分析 Agent：生成假设 + 第一批 QuerySpec
        ↓
查询准入节点
        ↓
同一取数 Worker / 子图的 N 次并行调用
        ↓
DataEvidence 聚合与校验
        ↓
分析 Agent：解释证据，决定下钻或完成
        ├─ 需要下钻 → 新的 QuerySpec 批次 → 再回到取数
        └─ 证据足够 → 报告草稿
        ↓
报告校验 → 主 Agent 组装最终答复
```

因此，“三个取数 Agent 一起干”在 LangGraph 里通常不是三个常驻 Agent，而是同一个 `data_worker` 根据三个 `QuerySpec` 产生三次隔离的并行调用。动态数量可以用 LangGraph `Send` 实现，并通过 reducer 聚合各个 Worker 返回的 `DataEvidence`。

子 Agent 对上层的暴露方式有两种都很常见：

| 暴露方式 | 机制 | 适用情况 |
| --- | --- | --- |
| Agent-as-Tool | 用一个工具 wrapper 在内部 `subagent.invoke(...)`，主 Agent 通过 tool calling 选择子 Agent | 路由较自由、子 Agent 像一次性专家服务、不强调父图对内部 State 的可见性 |
| Subgraph-as-Node | 把编译好的子图注册为父 `StateGraph` 节点，由父图路由 | 需要受控准入、checkpoint、中间状态可观测和跨 Agent 门禁 |

对当前智能经营分析，优先选择 `Subgraph-as-Node`。但从分析 Agent 的逻辑视角看，取数能力仍应呈现为一个明确的工具式契约：

```text
execute_query(QuerySpec) -> DataEvidence
```

它内部是普通工具、Agent 还是子图，由上层编排隔离。分析 Agent 只提交 `QuerySpec`，真正执行仍经过父图的权限、指标、范围、预算和证据校验。

按请求类型的最终选择是：

| 请求类型 | 谁计划取数 | 主体链路 |
| --- | --- | --- |
| 直接查数 | 主 Agent 组装 `QuerySpec` | 主 Agent → 取数能力 → 结果校验 → 主 Agent |
| 固定分析模式 | Workflow / 分析 Skill 预定义查询批次 | 固定计划 → 并行取数 → 分析/报告 |
| 开放式分析 | 主 Agent 定义边界，分析 Agent 决定详细 QuerySpec | 主 Agent → 分析 Agent ⇄ 受控取数能力 → 报告 → 主 Agent |

### 后续追问：受控编排是不是“子 Agent 只能回到主 Agent”？

#### 用户原始理解

> 主 Agent 的下一个节点一定是取数 Agent 或分析 Agent；取数 Agent 无法再有下一个节点，只能返回主 Agent；分析 Agent 可以调取数 Agent，而分析 Agent 的下一个节点也只能是取数 Agent 或主 Agent。

#### Codex 反馈

这个理解抓到了“跳转范围受限”，但把受控编排误解成了“所有子 Agent 都必须回主 Agent 的星形结构”。

严格定义是：

> 受控编排器事先定义了当前状态允许的下一步集合、每条边的准入条件、权限、循环上限和停止条件；Agent 在这个边界内选择目标、产生参数、解释结果和决定可允许的下一步。

一个更正确的父图可以是：

```text
主 Agent
  ├─ 信息不足 → 澄清 / interrupt → 主 Agent
  ├─ 直接查数 → QueryGate → 取数子图 → EvidenceGate → 主 Agent / 结果输出
  ├─ 开放分析 → 分析子图
  ├─ 口径咨询 → 只读知识工具 → 主 Agent
  └─ 不支持 / 超预算 → SafeFail

分析子图
  ├─ 需要证据 → QueryGate → 取数子图 → EvidenceGate → 继续分析
  ├─ 需要计算 / 绘图 → 受控计算工具 → 继续分析
  ├─ 信息不足 → 澄清
  ├─ 证据足够 → ReportGate → 主 Agent 组装输出
  └─ 超过上限 / 无法安全继续 → SafeFail
```

所以：

- 主 Agent 的下一步不只有取数 Agent 或分析 Agent，还可以是澄清、知识查询、直接答复、人工审核或安全停止；可用出边由当前 State 和图定义决定。
- 取数 Agent 不是只能回主 Agent。它对父图返回 `DataEvidence`，父图根据这份数据是为直接查数还是为分析子任务服务，可将结果送回主 Agent、分析 Agent、重试节点或 `SafeFail`。
- 取数 Agent 内部也可有自己的子图，例如 `Schema 检索 → SQL 生成 → 执行 → 校验 → 错误修复`；父图只看它的输入/输出契约。
- 分析 Agent 逻辑上可以“调用取数”，但受控实现中它先输出 `next_action=query_data + QuerySpec`，再由父图的 `QueryGate` 校验后调用取数子图。
- 分析 Agent 的下一步也不只是取数或回主 Agent；它还可以继续解释当前证据、执行受控计算/绘图、请求澄清、生成报告或安全停止。

Agent 的自由和编排器的受控分别体现在：

| Agent 可自主决定 | 编排器/runtime 必须硬控 |
| --- | --- |
| 当前最有价值的分析假设 | 能不能访问某指标/表/用户数据 |
| 要申请哪些 `QuerySpec` | `QuerySpec` 是否完整、合法、在预算内 |
| 如何解释空结果或异常值 | 是否允许重试，最多重试几次 |
| 证据是否足以支持下钻假设 | 最多几轮下钻、超限如何停止 |
| 报告重点和解释顺序 | 报告数值、指标身份和证据引用必须通过校验 |

技术上，分析 Agent 可返回：

```json
{
  "next_action": "query_data",
  "query_specs": [
    {"metric_id": "premium_income", "dimension": "channel"}
  ],
  "reason": "需要验证下降是否集中在某渠道"
}
```

但不让模型直接拥有无约束的节点跳转权。父图路由代码会检查：

```python
def route_after_analysis(state):
    if state["analysis_rounds"] >= state["max_analysis_rounds"]:
        return "safe_fail"
    if state["next_action"] == "query_data" and query_specs_are_valid(state):
        return "query_gate"
    if state["next_action"] == "finish" and evidence_is_sufficient(state):
        return "report_gate"
    return "clarify_or_safe_fail"
```

这就是“Agent 自由提出下一步，编排器只允许合法边通过”，而不是“编排器把每一步都写死”。

### 后续追问：是否需要单独的澄清 Agent？

#### 用户原始问题

> 需要单独的澄清 Agent 吗？成熟 Data Agent 有设置澄清 Agent 吗？

#### Codex 反馈

通常不需要。成熟 Data Agent 普遍具有澄清能力，但官方公开架构通常没有把“通用澄清”披露为一个长期独立的 Agent：

- Databricks 由同一个 Genie Agent 在意图不清时提出后续问题，并建议在该 Agent 的 instructions 中规定何时、如何澄清。
- Snowflake 由当前 Cortex Agent 在“继续调用工具、向用户澄清、生成回答”之间选择。
- OpenAI 内部 Data Agent 会在任务信息不足时主动澄清；用户不回答时也可以采用合理默认值继续。
- Microsoft Fabric 的公开形态仍是一个 Data Agent / Orchestrator 选择 NL2SQL、NL2DAX、NL2KQL 等工具，没有单独披露通用澄清 Agent。
- Uber QueryGPT 虽然拆出了 Intent、Table、Column Prune 等专业 Agent，Table Agent 还会让用户确认候选表，但这属于某一步骤内的人机确认，不是一个通用澄清 Agent。

这里应把三个责任分开：

| 责任 | 推荐承担者 |
| --- | --- |
| 发现缺失信息 | 当前最了解任务上下文的主 Agent 或分析 Agent |
| 判断是否允许继续、暂停并保存状态 | 受控编排器中的 `ClarificationGate` / 状态节点 |
| 以统一口吻向用户提问 | 主 Agent 的对话入口 |

对当前智能经营分析，推荐的流转是：

```text
主 Agent / 分析 Agent 发现信息不足
        ↓
返回结构化 ClarificationRequest
        ↓
ClarificationGate 校验并写入 need_clarification
        ↓
统一对话入口一次询问当前已知的全部缺失项
        ↓
interrupt + checkpoint 等待用户回答
        ↓
根据 resume_to 回到原来的主 Agent 或分析 Agent
```

结构化请求可以是：

```json
{
  "status": "need_clarification",
  "requested_by": "analysis_agent",
  "resume_to": "analysis_agent",
  "missing_fields": ["comparison_period", "channel_scope"],
  "question": "请一次补充对比周期和渠道范围。",
  "round": 1
}
```

分析 Agent 可以发现“缺少对比期、分析范围或归因目标”，但默认不应自己另开一套对话；取数 Agent 如果遇到口径歧义、权限不足或无法生成合法查询，也优先返回结构化缺失项/错误，由主 Agent 或分析链路决定如何向用户表达。这样可以避免多个 Agent 重复理解意图、争抢对话权和丢失回答后的恢复位置。

当前 E2 学习复现中的节点可以继续叫 `clarification_agent`，因为它目前组合承担了意图识别、槽位提取和澄清决策。但在完整架构中，更准确的概念是 `request_understanding` 或 `main_understanding`：**澄清是它可能产生的一种状态，而不是因此必须存在一个独立 Agent。**

只有当澄清本身已经成为跨领域复用的复杂业务能力——拥有独立知识、工具、多轮问卷/合规规则、内部循环和独立评测——才值得拆成专门的澄清 Agent。普通 Data Agent 的指标、时间、维度、范围补全通常达不到这个门槛。

### 证据边界

- Snowflake、Fabric、Databricks 和 Google 的结构来自官方产品文档；这能证明产品的公开使用模型，不能证明官方未披露的全部内部实现。
- OpenAI、Uber 和 Amazon RRDA 是官方公开的内部/生产案例；它们展示真实落地架构，但不代表全行业都必须复制。
- Google Code Interpreter、Fabric advanced DAX 等功能在官方资料中仍标注为 Preview，因此不将它们当作“成熟基线”的单独证据。

## 发散联想

- 当前已确认的“受控编排 + 受限 Agent 自主决策”方向与多个产品化 Data Agent 的主体方向一致。
- 需要进一步验证的不是“是否够多 Agent”，而是取数 Agent 和分析 Agent 是否各自拥有不重复的目标、上下文、工具权限、内部循环和评测边界。
- 成熟架构的重心通常不在 Agent 数量，而在语义层/指标口径、只读权限、查询校验、可停止循环、证据透明和分阶段评测。

## 结论状态

- 成熟 Data Agent 的公开主体架构：待继续
- “主 Agent + 分析 Agent + 取数 Agent”与当前项目的对应关系：待确认
- 受控编排与 Agent 自主决策的边界：待继续
- 是否需要独立澄清 Agent：待确认

## 后续动作

- 由用户确认是否认同“主 Agent + 受控编排 + 专业能力”是比“三 Agent”更稳定的一级抽象。
- 如果认同，再对照当前智能经营分析架构，只检查取数 Agent 与分析 Agent 的独立责任是否充分，不扩展其他模块。

## 官方资料

- [Snowflake Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- [Snowflake：Create and manage agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-manage)
- [Microsoft Fabric：Semantic model best practices for data agent](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices)
- [Microsoft Fabric：Create a Fabric data agent](https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent)
- [Databricks：Genie Agents concepts](https://docs.databricks.com/aws/en/genie-agents/concepts)
- [Databricks：Use a Genie Agent to explore business data](https://docs.databricks.com/aws/en/genie-agents/talk-to-genie)
- [Databricks：Curate an effective Genie Agent](https://docs.databricks.com/aws/en/genie-agents/best-practices)
- [Snowflake：Analytical search with Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-analytical-search)
- [Google Cloud：Understanding Looker’s Conversational Analytics API](https://cloud.google.com/blog/products/data-analytics/understanding-lookers-conversational-analytics-api)
- [Google Cloud：Conversational Analytics API overview](https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/overview)
- [OpenAI：Inside OpenAI’s in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)
- [Uber：QueryGPT – Natural Language to SQL Using Generative AI](https://www.uber.com/us/en/blog/query-gpt/)
- [AWS：Build a conversational data assistant, Part 1](https://aws.amazon.com/blogs/machine-learning/build-a-conversational-data-assistant-part-1-text-to-sql-with-amazon-bedrock-agents/)
- [LangGraph：Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph：Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph：Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
