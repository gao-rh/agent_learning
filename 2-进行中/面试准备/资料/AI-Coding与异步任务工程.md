# AI Coding 与异步任务工程

更新：2026-09-16。性质：教学参考与现场练习，Codex 整理；不代表本人已独立实现或公司生产代码。

**为何新增：** 现有《综合面试问题》维护个人 Coding 经历，Agent Q27 维护 Coding Agent 系统设计，均未承载 JavaScript 异步代码、并发池和代码审查。此处作为这些工程题的稳定主位置；岗位清单只引用本页。

先看 [01](#coding01) 和 [02](#coding02)，再按时间补重试、限并发、超时与审查。以小红书猎头提示为练习入口，题面均为 Codex 设计，不能称为该场原题。

<a id="coding01"></a>
## 01｜先理解 JavaScript 异步代码

- Promise 表示一个异步操作的最终状态。pending 会变为 fulfilled 或 rejected，已确定的状态不会重新运行。
- async 函数返回 Promise；函数内 throw 会让返回的 Promise 失败。
- await 让当前 async 函数的后续执行等待结果；其他事件可以继续处理。同步 CPU 密集代码仍会阻塞事件循环。
- Promise.allSettled 接受可迭代输入，等待每项结束，并按输入顺序返回状态。它不负责启动任务函数、不自动重试、不限制并发，也不自带超时。
- Promise.all 在某项失败后使聚合 Promise 失败，但不会自动取消其他任务。

```javascript
// 任务函数要调用；只把函数放进数组不会自动执行。
const jobs = [() => Promise.resolve('A'), () => Promise.resolve('B')];
const results = await Promise.allSettled(jobs.map(run => run()));
```

上例用于说明调用方式，但如果普通函数在返回 Promise 之前同步 throw，map 本身会中断。下一题的 Promise.resolve().then(...) 会统一处理这个问题。

常见陷阱：forEach 不等待 async 回调的 Promise。需要顺序时用 for...of 加 await；允许并发时收集 Promise 再聚合；规模大时再限制并发。

依据：[MDN allSettled](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/allSettled)、[MDN all](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all)。

<a id="coding02"></a>
## 02｜并发执行 A、B、C，收齐成功与失败

**题面：** 输入任务数组，每项有唯一 id 和 run 函数；返回每个任务的结果，某项失败不丢弃其他项，结果顺序与输入相同。这里假设输入结构合法，所有任务最终都会结束。

```javascript
async function settleJobs(jobs) {
  const results = await Promise.allSettled(
    jobs.map(job => Promise.resolve().then(() => job.run()))
  );
  return results.map((result, index) => ({
    id: jobs[index].id,
    ...result,
  }));
}
```

**怎么解释：** 每项 run 都在 Promise 回调里执行，同步抛错也会变成 rejected。allSettled 收齐后，按下标附上对应任务 ID。

输出形状示意：

```text
[
  { id: 'A', status: 'fulfilled', value: 'A 的结果' },
  { id: 'B', status: 'fulfilled', value: 'B 的结果' },
  { id: 'C', status: 'rejected', reason: Error('临时失败') }
]
```

**必须知道的边界：**

- 输出保序不等于执行保序；B 可以先于 A 完成。
- 空数组得到空结果。
- 某任务永不结束，聚合会一直等待，需要另设超时。
- fulfilled 只表示 Promise 成功返回。它可能返回了业务错误对象，业务语义仍需检查。
- Error 可用于进程内判断，跨网络返回时应显式序列化需要的字段；不要依赖 JSON.stringify(Error) 得到完整信息。

### 若要求手写简化版

**题目约定：** 合法数组输入，演示常用语义，不声称完全实现原生 Promise 构造器、子类和异常迭代器的全部规范行为。

```javascript
function allSettledArray(values) {
  return Promise.all(Array.from(values, value =>
    Promise.resolve(value).then(
      value => ({ status: 'fulfilled', value }),
      reason => ({ status: 'rejected', reason })
    )
  ));
}
```

原理：给每个输入同时接上成功与失败处理，把失败也转成正常返回的结果对象，最后汇总。Promise.resolve 同时接住普通值、Promise 与 thenable。

<a id="coding03"></a>
## 03｜只重试失败的 C，再合并结果

**题面：** 延续上题，任务可以安全重试；只重试临时失败，最多再执行一次，返回最新结果。幂等写操作需额外业务保证，这里以查询任务为例。

```javascript
async function retryFailedOnce(jobs, retryable) {
  const first = await settleJobs(jobs);
  const failedIds = new Set(first
    .filter(item => item.status === 'rejected' && retryable(item.reason))
    .map(item => item.id));

  const second = await settleJobs(
    jobs.filter(job => failedIds.has(job.id))
  );
  const latest = new Map(first.map(item => [item.id, item]));
  for (const item of second) latest.set(item.id, item);
  return jobs.map(job => latest.get(job.id));
}
```

调用时的分类逻辑示意：reason 上有受控错误码，retryable 仅对明确临时故障返回 true。不要把网络异常、鉴权失败、参数错误和写入结果未知都当成同一种问题。

**为什么保留任务函数？** Promise 是一次操作的结果；重试要调用函数产生新操作，不能把同一个 rejected Promise 再等待一次当作重做。

**为什么用 Map 覆盖？** 这里的状态表示每项任务最新一次结果。若直接追加，C 的失败和成功会同时存在，需要再解释哪个有效。历史日志可以另存 attempt、时间与原因，不与最新状态混为一份。

**如果第一次写入可能成功，响应却丢了？** 先按幂等键查询或对账，区分结果未知与确定失败。重试预算、退避和抖动应有整任务上限。

<a id="coding04"></a>
## 04｜最多同时执行 N 个任务

**题面：** 大量独立任务，需要限制并发并保留每项状态与输入顺序。输入为合法任务数组，limit 为正整数。不在任务之间引入依赖。

```javascript
async function settleLimited(jobs, limit) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new RangeError('limit 必须为正整数');
  }
  const results = new Array(jobs.length);
  let next = 0;

  async function worker() {
    while (next < jobs.length) {
      const index = next++;
      const job = jobs[index];
      try {
        const value = await job.run();
        results[index] = { id: job.id, status: 'fulfilled', value };
      } catch (reason) {
        results[index] = { id: job.id, status: 'rejected', reason };
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(limit, jobs.length) }, () => worker())
  );
  return results;
}
```

**直觉：** 开 N 个工人，每个工人完成手上任务再领取下一项。当前 JS 执行上下文里，领取下标发生在 await 之前，因而不会被这组 worker 重复领取；这不是跨线程共享变量的通用无锁方案。

**代码检查点：** 并发峰值不超过 N；某个任务失败后，工人还能领取后续任务；结果按 index 写回；空任务返回空数组。输入校验和任务取消可按真实接口契约扩展。

**生产者消费者追问：** 这题预先拿到了所有任务。如果生产者持续送入任务，还需要有界队列：满时背压、空时等待、退出时唤醒或发送结束信号。线程模型中还需要锁／条件变量等同步机制，不能照搬 JS 下标分配论证。

### HTTP 超时与状态检查

fetch 遇到 HTTP 404／500 通常仍成功返回 Response；需检查 response.ok。下例通过 AbortController 发出取消信号，并覆盖读取响应体所用时间。

```javascript
async function getJsonWithTimeout(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}
```

取消客户端等待不证明服务端没有执行请求。单纯用 Promise.race 包一个计时器，也不会自动中止底层任务。这里的定时器受事件循环调度影响，不是对阻塞 CPU 计算的硬实时中断。

依据：[MDN Fetch：状态与取消](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)。

<a id="coding05"></a>
## 05｜JavaScript 权限代码审查

**来源边界：** PE 原帖提到 JS 权限拦截审查，但没有给出完整原代码。下面是同类能力练习，不是还原真题。

错误示例：

```javascript
async function canEdit(user) {
  return user.role === 'editor';
}

function updateDocument(user) {
  if (typeof user === 'object' && canEdit(user)) {
    return '允许修改';
  }
  return '拒绝';
}
```

**问题与解释：**

1. typeof null 为 object，不能证明 user 有效。
2. canEdit 是 async，调用得到 Promise 对象。对象在条件中为真，不能代表权限检查已通过。
3. 异步失败如果没有 await 或错误处理，会脱离预期控制流。
4. 真正的权限还要考虑资源归属、租户和服务端身份，客户端按钮禁用不能代替服务端校验。

练习修正：

```javascript
async function updateDocumentSafe(user) {
  if (!user || typeof user !== 'object' || Array.isArray(user)) {
    return '拒绝';
  }
  try {
    const allowed = await canEdit(user);
    if (allowed !== true) return '拒绝';
    return '允许修改';
  } catch {
    return '拒绝';
  }
}
```

这是权限判断练习，没有真实写库动作。生产接口需按鉴权系统取得可信身份、校验具体资源，并明确失败响应；上例不能当作完整鉴权实现。

**现场解释顺序：** 先复述原功能，再沿正常和异常控制流指出缺陷，给出最小修正，最后用未登录、无权限、有权限和鉴权服务失败验证。

<a id="coding06"></a>
## 06｜和 LangGraph 的关系：收集失败结果与框架重试

本会话用户已表示了解相关机制；这里用于复习，不自动确认独立编码能力。

| 位置 | 负责什么 | 不会自动做什么 |
| --- | --- | --- |
| 节点函数 | 执行业务调用；捕获预期异常并形成结果，或继续抛出异常 | 不保证能捕获进程退出、外部存储与框架其他位置的错误 |
| Reducer | 合并多个节点对同一状态字段的更新 | 不自动捕获节点错误，不自动派发重试任务 |
| RetryPolicy | 对符合规则的抛出异常重试节点 | 捕获后返回的 failed 对象不会作为异常触发它 |
| 主控／条件路由 | 判断结果、依赖和预算，只派发需要重做的任务 | 不应把过期 attempt 的结果当作当前成功 |
| Checkpointer | 保存执行状态和恢复所需信息 | 不保证数据库外部写入、通知等副作用只发生一次 |

默认并行分支的未处理异常可能使当前 superstep 失败，下游汇总不会天然拿到 allSettled 风格的结果。如果应用希望收齐失败信息，需要在节点内把预期错误转换成结构化状态，或使用适合的框架异常策略。

A、B 成功、C 失败之后，主控可以只派发 C。最新状态按 task_id 合并，历史按 attempt 另存，路由等待本轮实际派发的任务。不要在只重跑 C 的循环中，仍要求 A、B、C 全部再次到达固定屏障。

有 checkpointer 时，成功分支的待提交结果可以在恢复中被利用，不代表整套应用任意副作用都不会重复。框架细节与版本条件见[LangGraph 图 API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)与[持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence)。

<a id="coding07"></a>
## 07｜一次 AI Coding 现场任务怎样推进

**先确认：** 输入输出、允许部分成功与否、任务规模、失败策略、语言与 AI 工具使用规则。这里是在面试里确认题目要求，不预设可以使用 AI。

**允许用 AI 时的任务说明示例：**

> 请实现一个 JavaScript 异步任务执行器。输入是唯一 id 与 run 函数组成的数组；最多同时执行 3 项；返回顺序与输入一致，保留每项成功或失败；任务会同步抛错或异步失败。先给简短实现思路，再给代码，并运行空输入、乱序完成和部分失败的样例。

然后本人检查实现，尤其是 task 函数是否真正被调用、是否提前启动了所有任务、异常后工人是否退出、输出是否仍保序。给 AI 明确失败输入，比连续说“再检查一下”更容易获得可验证的修复。

**工程完成的证据：** 需求满足、必要样例通过、代码能解释、边界说明准确。生成了很多代码、测试数量多或耗费很多 Token 都不能单独证明完成。

个人经历不在这里编写；对应原话见[综合面试问题](../常见问题回答准备/综合面试问题.md)。Coding Agent 的循环和执行环境见[Agent Q27](2026-09-13-大厂Agent面试重整/README.md#q27)。

<a id="coding08"></a>
## 08｜算法与基础保底：答案从哪里开始

### 最长无重复子串

使用滑动窗口与字符最近位置表，左边界只向右移动。以下 Python 实现返回长度，空字符串为 0；时间 O(n)，空间取决于不同字符数量。

```python
def longest_unique_length(text):
    last = {}
    left = best = 0
    for right, char in enumerate(text):
        if char in last:
            left = max(left, last[char] + 1)
        last[char] = right
        best = max(best, right - left + 1)
    return best
```

关键反例是 abba：遇到第二个 a 时，不能让 left 从 2 退回 1。

### 删除链表倒数第 N 个节点

使用哑节点和快慢指针，让快指针先走 N 步，再同时走到快指针位于末节点，慢指针就是待删节点的前驱。题目如保证 1 ≤ N ≤ 长度，可以利用该前提；否则需明确非法输入行为。用单节点、删头、删尾和 N 越界检查。时间 O(n)，额外空间 O(1)。

```python
def remove_nth_from_end(head, n):
    if n <= 0:
        raise ValueError('n must be positive')
    class Dummy:
        pass
    dummy = Dummy()
    dummy.next = head
    fast = slow = dummy
    for _ in range(n):
        fast = fast.next
        if fast is None:
            raise ValueError('n exceeds list length')
    while fast.next is not None:
        fast = fast.next
        slow = slow.next
    slow.next = slow.next.next
    return dummy.next
```

### 表达式求值

先确认题面是前缀、后缀还是中缀；原面经只写“波兰式”，不能强行改成某道确定题。若明确为逆波兰／后缀表达式，从左向右扫描，操作数入栈；运算符先弹右操作数再弹左操作数。减除法顺序不能反，整数除法需确认负数截断规则。

### 生产者消费者

参考设计：有界队列保存任务，生产者在队满时等待或按约定拒绝，消费者在队空时等待；处理后领取下一项。退出协议必须能唤醒等待者。线程环境使用合适的线程安全队列或互斥与条件变量，等待条件通常用循环重新检查。考点是背压、同步和退出，不是只画两个线程。

### 哈希、并发与 HTTP

- 哈希表平均查询可接近 O(1)，仍需处理冲突与扩容，不承诺每次固定常数时间。
- 并发是多任务交错推进，并行是同时执行；异步 I/O 并发不等于 JS CPU 工作并行。
- HTTPS 在 HTTP 之上使用 TLS 提供传输机密性、完整性和端点认证；不能替代业务身份、授权与应用输入校验。
- 用户进程中的超时不是对所有外部执行的回滚；连接断开之后仍要考虑结果未知。

<a id="coding09"></a>
## 09｜核验记录与复习边界

2026-09-16：本页例子是教学代码，未接公司接口、真实模型、鉴权系统或数据库。JS 异步基础依据 MDN，LangGraph 错误与恢复依据官方文档及本会话先前的本地机制实验。

本轮已从正文提取实现并实跑：Node.js v24.14.0 下验证同步异常、异步失败、输入顺序、空输入、简化 allSettled、仅重试临时失败项、并发上限和失败后继续执行；用本机临时 HTTP 服务验证成功响应、HTTP 500 和超时取消；验证权限 Promise 陷阱与修正后行为。Python 3.14.6 下验证滑动窗口及链表的空值、首尾删除和非法 N。上述检查均通过。

本地阅读页已检查关键词搜索、结果跳转和具体章节展开；4 份登记资料的在线视图 SHA-256 与对应 Markdown 一致。未将额外私人材料或归档加入搜索。

类型与异步语义依据：[MDN typeof](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/typeof)、[MDN async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)。

这些检查证明示例在指定本地环境中的行为，不证明完整生产能力，也不替代本人现场解释和修改代码。
