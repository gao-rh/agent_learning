# JavaScript 与 TypeScript 补课清单

状态：AI 草案 / 待确认。目标是读懂、调试并独立实现 Pi，不是先转成前端工程师。

> 2026-09-05：用户明确 JavaScript 零基础，只有 1–2 周非全职时间。本页为按需参考目录，当前按[一至两周核心学习安排](../记录/2026-09-05-一至两周核心学习安排.md)在短消息/工具示例中补语法；class、泛型、异步迭代等不作为当前必做前置。

JavaScript 是运行行为，TypeScript 为它增加静态类型约束，Node.js 提供文件、进程、网络等运行环境。TypeScript 的接口不会自动变成运行时的 JSON 参数校验。

## 语言与运行时参考范围（按课查阅）

| 顺序 | 要掌握什么 | Pi 中为什么需要 | 小练习 / 通过标准 |
| --- | --- | --- | --- |
| 1 | const/let、对象、数组、解构、展开、可选链、空值合并 | 消息、配置、上下文几乎全是对象和数组 | 对一组 message 做 filter/map；解释浅复制后修改嵌套对象的结果 |
| 2 | 函数、箭头函数、闭包、class、this | 回调、工具工厂、Agent 实例和队列 | 写出有私有状态的工具注册器，解释每个闭包捕获了什么 |
| 3 | ES modules、import/export、package.json、exports、工作区 | 跟踪跨包调用和依赖注入 | 能从 import 找到实现；区分源码运行、编译产物、npm 包 |
| 4 | Promise、async/await、try/catch/finally | 所有模型和工具调用都跨异步边界 | 自己预测串行 await 与 Promise.all 的日志和错误传播 |
| 5 | event loop、microtask、I/O 回调 | 流式显示、取消、排队请求和状态可交错发生 | 解释 await 让出的是当前异步函数，不是阻塞整个进程 |
| 6 | Iterator、Generator、AsyncIterable、for await | EventStream、流式 provider 响应 | 不看原实现写一个支持排队、等待和结束的异步事件流 |
| 7 | AbortController、清理、超时 | 中止网络、工具与子进程 | 取消后不再产出新进度；在 finally 清掉计时器和监听 |
| 8 | Node fs/path、Buffer、child_process、stdin/stdout | 读写文件、shell 工具、终端协议 | 在合成临时目录读文件、启动无害子进程、分别收集输出和退出码 |
| 9 | type/interface、联合类型、字面量、narrowing、unknown | AgentEvent 与消息类型 | 用 switch(event.type) 做穷尽处理；不用 any 绕过问题 |
| 10 | 泛型、函数类型、类型导入、结构类型 | EventStream<T,R>、AgentTool、回调契约 | 用两个类型参数解释“流中的事件”与“最终结果”为何不同 |
| 11 | runtime schema、JSON 解析、TypeBox | 模型与外部插件输入不受 TS 编译器保护 | 给非法 JSON/错类型/缺字段编失败用例，证明不会调用工具 |
| 12 | Vitest/node:test、mock、fake timer、调试器 | 证明顺序、错误和取消，而不是碰运气调用大模型 | 写可重复的无模型测试；能在循环里断点查看状态 |

这些条目按课程需要拆开使用；当前路线先学基础语法和简单 await，再做 Kimi 与工具循环，之后补 TypeScript、异步迭代与 EventStream。

当前 v0.85.0 的参数校验依赖写作 `typebox/compile`、`typebox/value`，不要照旧教程安装另一套校验组合再假设与当前源码一致。

## 有明确入口的学习资料

| 资料 | 指定阅读范围 | 用法 |
| --- | --- | --- |
| [MDN JavaScript 中文指南](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide) | 语法、函数、对象、集合、类、模块 | 初期主教材；不要求顺着学完浏览器生态 |
| [MDN：使用 Promise](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide/Using_promises) | 链、异常、组合、时序 | 用手写事件日志验证理解 |
| [MDN：迭代器和生成器](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide/Iterators_and_generators) | 可迭代协议、生成器 | 再对照 Pi 的 Symbol.asyncIterator |
| [Node.js：Event Loop](https://nodejs.org/learn/asynchronous-work/event-loop-timers-and-nexttick) | 事件循环、timers、nextTick | 理解运行基础；具体时序题固定 Node 版本 |
| [TypeScript：Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html) | 对象、联合、字面量、函数 | 从 Pi 的消息结构练起 |
| [TypeScript：Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) | type guards、discriminated unions、never | 阅读 AgentEvent 分支 |
| [TypeScript：Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html) | 泛型函数、约束 | 读 EventStream<T,R> 与工具类型 |

这些是在线资料，不属于已离线镜像的 Pi 文档。英语只按当课段落解释，中文释义与原文分开。

## 后续阶段自查题

1. 看到 `const next = [...messages]`，能否判断修改 `next[0].content` 会不会影响原数据？
2. 看到 `await tool.execute()`，能否说明等待期间终端输入能不能被处理？
3. 能否解释 Promise.all 的“完成顺序”和返回数组的“排列顺序”？
4. 能否解释为什么 event.type 可以帮助 TS 确定其他字段？
5. 能否说出为什么 TypeScript 参数类型正确仍需要运行时 schema？

这些问题在相应概念学完后使用。用户已明确零基础，不再用它们筛选第一课起点，也不预先把任何一项标成已理解。

## 暂不作为前置课

React/Vue、CSS、浏览器 DOM、复杂前端构建、高级类型体操、手写 JS 引擎、完整 Transformer 训练。它们不应阻塞 Agent Loop、Node I/O 和状态恢复的主线。

“暂不前置”不等于永远不学：如后续确需 WebUI 或深入模型推理，再单开相应分支。
