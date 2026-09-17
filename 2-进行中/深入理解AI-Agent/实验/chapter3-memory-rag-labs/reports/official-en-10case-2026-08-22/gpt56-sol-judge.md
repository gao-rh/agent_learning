# 官方英文 10 用例 × 4 模式独立判分报告

判分者：GPT-5.6 SOL（独立 Judge）；writer 与 answerer：Kimi K2.6。日期：2026-08-22。

本报告是从官方 60 用例中选择的 **10 个目的抽样案例**，共 40 个 arm；它不是完整 60 用例的总体结论，也不宜据此估计总体显著性。

## 判分口径

我逐 arm 阅读了官方英文 YAML 的完整 sessions、最终问题、expected behavior/evaluation criteria，以及结果 JSON 的每轮 `memory_states` 和最终 `answer`。源对话是事实最高权威；criteria 仅表达测试意图，不会把其中与源冲突或源中没有的事实自动当真。

四维 `precision / recall / reasoning / proactivity` 均为 1–4 分。官方通过条件为：无 material hallucination，且前三维均不低于 3；proactivity 只诊断、不决定通过。表中 `P` 为通过，`F-H` 为 hallucination veto，`F-S` 为无幻觉但核心维度低于 3，`GF` 为生成失败；括号内依次为四维分数。

## 10 × 4 判分矩阵

| 测试用例 | Notes | Enhanced Notes | JSON Cards | Advanced JSON Cards |
|---|---:|---:|---:|---:|
| layer1_01_bank_account | P (4/4/4/4) | F-H (2/4/3/3) | P (4/4/4/4) | P (4/4/4/4) |
| layer1_04_airline_booking | P (4/4/4/4) | P (4/4/4/4) | P (4/4/4/4) | GF |
| layer2_01_multiple_vehicles | P (4/4/4/3) | P (4/4/4/3) | F-H (2/4/3/4) | P (4/4/4/4) |
| layer2_07_multiple_medications | F-H (2/4/3/4) | F-H (2/4/3/4) | F-H (2/3/3/4) | F-H (1/3/2/4) |
| layer2_10_travel_rebooking_chain | P (4/3/4/3) | F-H (2/3/4/4) | F-H (2/3/4/4) | F-H (2/3/4/4) |
| layer2_12_contradictory_financial_instructions | F-H (2/4/2/4) | P (4/4/4/4) | P (4/4/4/4) | P (4/4/4/4) |
| layer3_01_travel_coordination | P (3/4/4/4) | P (3/4/4/4) | F-H (1/4/2/3) | P (4/4/4/4) |
| layer3_02_medical_insurance_coordination | F-H (2/4/2/4) | P (4/4/4/4) | F-H (1/2/1/3) | F-S (4/2/2/4) |
| layer3_04_warranty_coordination | F-H (1/1/1/3) | F-H (2/4/3/4) | F-H (2/4/3/4) | F-H (2/4/3/4) |
| layer3_05_tax_preparation_synthesis | F-H (2/3/3/4) | F-H (2/3/3/4) | F-H (2/3/2/4) | F-H (2/4/2/4) |

总计通过 **17/40（42.5%）**。其中 21 个成功生成的 arm 因 material hallucination 被否决，1 个无幻觉 arm 因 recall/reasoning 低于 3 未通过，另有 1 个真实生成失败。

## 按模式与层级通过率

| 模式 | 通过/总数 | 通过率 |
|---|---:|---:|
| Notes | 5/10 | 50.0% |
| Enhanced Notes | 5/10 | 50.0% |
| JSON Cards | 3/10 | 30.0% |
| Advanced JSON Cards | 4/10 | 40.0% |

| 层级 | 通过/总数 | 通过率 |
|---|---:|---:|
| Layer 1 | 6/8 | 75.0% |
| Layer 2 | 7/16 | 43.75% |
| Layer 3 | 4/16 | 25.0% |

仅统计成功生成 arm 的 writer 各轮加 answerer 总调用数据，平均每 arm 的观测开销如下；它反映本地结果 receipt，不等同于供应商账单：

| 模式 | 平均总 token | 平均累计延迟 |
|---|---:|---:|
| Notes | 10,181 | 75.7 秒 |
| Enhanced Notes | 10,294 | 82.5 秒 |
| JSON Cards | 13,012 | 111.3 秒 |
| Advanced JSON Cards | 21,007 | 186.1 秒 |

Advanced 仅含 9 个成功生成 arm；airline 的第 10 个 arm 因输出上限失败，未纳入平均值。

## 主要失败模式

失败 arm 可同时有多个阶段标签，因此以下计数不能相加为 23：

| 阶段 | 失败 arm 数 | 典型表现 |
|---|---:|---|
| benchmark_ambiguity | 20 | fixture 与源对话冲突，或把计划当完成、把不明确范围当强制范围 |
| answerer_usage | 14 | 正确事实已在最终记忆中，但答案遗漏、误用或添加无依据细节 |
| writer_memory | 13 | 写入错误年份/付款账户/状态，或后续轮次把关键旧事实遗失 |
| schema_format | 2 | 固定 JSON 结构在更新时丢失当前状态或把旧对象误当当前对象 |
| output_limit | 1 | Advanced JSON 在 airline arm 真实触发输出上限 |

最重要的现象不是“回答是否漂亮”，而是三个更硬的失效链条：

1. **写入污染后被答案放大**：错误年份、付款来源、完成状态一旦进入长期记忆，answerer 往往用确定语气复述。
2. **记忆正确但 answerer 没用对**：例如 surgery prior authorization 已在 Advanced cards 中，却被最终答案完全遗漏。
3. **结构并不自动保证生命周期正确**：JSON Cards 在医疗用例中把当前手术授权丢掉，却保留了早已过期的 MRI 授权；结构化只是让错误更规整。

## 代表性逐证据解释

### 1. Bank / Enhanced Notes：writer 自造“账户冲突”

源会话明确：checking 是 `4429853327`，savings 是 `4429853328`，routing 是 `123006800`。Enhanced memory state 1 前段写对，后段却说 direct deposit 使用 `4429853328`。答案虽然最终给出正确 checking 号，却宣称记录存在 discrepancy 并要求用户核验。这不是谨慎加分，而是 writer 污染导致的源外事实，触发 hallucination veto。

### 2. Airline / Advanced：真实 output-limit 失败

`layer1_04_airline_booking--advanced_json_cards--en.failure.json` 是实际生成失败，没有可评分答案。按要求原样标记 `generation_failure`、`pass=false`、`failure_stage=[output_limit]`，没有补跑或从其他模式补答案。

### 3. Multiple Vehicles / JSON：fixture 日历矛盾不能偷偷“纠正”

源会话把预约说成 “Friday, November 24” 和 “Black Friday”，但 2024-11-24 实际是星期日。JSON answer 改成 Sunday，虽然符合现实日历，却违反本实验“源对话优先”。其 Honda/Tesla 绑定是正确的，但日期改写仍是 material contradicted claim。Notes/Enhanced/Advanced 列出两车状态，已足以解决复数问题，不因未机械追问“哪辆车”而判失败。

### 4. Multiple Medications：四种模式都把时间歧义处理坏了

session 1 时间戳为 2024-09-20，却说最近 refill 是 October 5/20，且没有年份。Notes、Enhanced、Advanced writer 都擅自补成 2023；JSON writer 没补年份，answerer 却补成 2024。前者让答案推导出“已超过 11 个月”，后者制造未来 refill。Advanced 又声称有四种 BP 药但只列三种。四个 arm 均被否决。

### 5. Travel Rebooking / Notes：没有给 companion 总额不等于核心失败

源会话支持 Michael 最终 NPRS45 行程和自己的 $6,200；Jennifer 的 $2,300 在另一个关联 booking。最终问题说 “my itinerary and total cost”，自然可以只回答 Michael。Notes 正确给出全部改签链与 $6,200，因此 recall 记 3 并通过；fixture 要求 $8,500 combined total 被标为 benchmark ambiguity。其余三种模式反而把原始个人 Amex 与后续 corporate Visa 合并成“全由公司卡支付”，属于实质错误。

### 6. Contradictory Financial / Notes：答案否认记忆中已有的最终指令

源对话和最终 Notes 都明确：Patricia 最后确认 `WT-89089`、$95,000、October 1、Chase funding，并替代旧指令。答案却说没有显式确认冲突如何解决。这里 writer 没错，是 answerer 没有使用记忆中的明确 supersession，reasoning 记 2 且 hallucination veto。

### 7. Travel Coordination：官方 criteria 与源对话正面冲突

源会话明确说 Japan 只要求护照在停留期间有效，expedited renewal 为 2–3 周；criteria 却写“六个月规则”“很可能拒绝登机”“expedited 5–7 周”。Notes、Enhanced、Advanced 按源回答并通过。JSON 不仅受 fixture 影响，还把 7.5 周窗口错误写成 standard 已来不及、无条件要求 14 天内 urgent appointment，并把“Amex 支付的机票不受 Chase trip insurance 覆盖”扩大成“整个行程不受覆盖”，因此独立失败。

### 8. Medical / JSON 与 Advanced：一个是 schema 丢事实，一个是 answerer 漏事实

源会话的首要 blocker 是 December 5 surgery 的 prior authorization 截至 November 20 尚未收到。JSON memory 从 state 2 到 state 3 丢掉这项当前状态，并把明确 in-network 的 Riverside Surgery Center 改成“assumed”；答案于是追逐已经过去的 February MRI 授权并警告手术中心网络未知。Advanced 最终卡片则完整保留 `surgery_auth_status=not yet received`，但答案仍完全不提。这分别定位为 `writer_memory + schema_format` 和 `answerer_usage`。

### 9. Warranty：benchmark 的主方案本身不受源支持

源只说 Chase purchase protection 在购买后 120 天覆盖 damage/theft；extended warranty 是延长 manufacturer warranty。criteria 却要求把延保作为意外碎屏的 primary solution，同时给出源中没有的 $600–800 repair price，并从“住独栋房”推导 homeowner policy。Enhanced/JSON/Advanced 正确判断延保通常不覆盖意外裂屏，但都又给出源外的精确维修价、AppleCare 购买窗口或 parts-pairing 风险，故仍触发严格 hallucination veto。Notes 更早在 state 3 就遗失了整台 MacBook，答案错误声称从未购买。

### 10. Tax：计划、启动与完成不能混写

源中用户说会“今天发起”72 股 MSFT 转账，但没有确认到账；厨房和 deck 也只是约 $50,000 的计划。JSON schema 直接把 donation 记为完成并把持仓减到 78。Advanced cards 做得更好，保留 `initiated` 和 `planned`，但答案仍把房屋 basis 从 $632,250 直接升到 $682,250。四种答案还存在 QuickBooks 未购买却扣除、错误更改 homestead 年份，或把全额 mortgage/property tax 同时放入 Schedule A 和 Schedule C 的双重计算风险。因此不能因覆盖面广而放水。

## 与书中结论的一致性

对“**Simple Notes 基础层成本低**”，本样本基本一致：Layer 1 的 Notes 为 2/2，通过表现稳定；其成功 arm 平均 10,181 token、75.7 秒，也是四种模式最低。

对“**Advanced JSON 高层最好但更贵更慢**”，本样本只支持后半句，不支持“最好”：

- 更贵更慢得到明显支持：Advanced 成功 arm 平均 21,007 token、186.1 秒，约为 Notes 的 2.06 倍 token、2.46 倍延迟，且额外出现 1 次 output-limit 失败。
- 高层最好没有在这 4 个 Layer 3 目的样本中出现：Advanced 仅 1/4，通过率与 Notes 相同，低于 Enhanced Notes 的 2/4；全体 10 用例也只有 4/10，低于 Notes 和 Enhanced 的 5/10。
- Advanced 的优势主要体现在显式状态/生命周期可定位，例如 tax 的 `planned/initiated`、financial 的 `superseded/active`；但它仍可能被 answerer 忽略，也可能把源外推断结构化为貌似确定的字段。

因此，这 10 个目的抽样案例给出的更准确结论是：**简单格式在基础事实题上成本/可靠性很好；Advanced JSON 确实最重、最慢，并在部分冲突生命周期题上有优势，但“高层最好”尚未被该样本复现。** 完整书中结论仍需用全部 60 用例、相同 judge 口径和成本统计重新验证。
