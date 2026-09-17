# 拼多多｜机器学习与 PyTorch 面试速补

整理日期：2026-09-11。**AI 整理的备考问答，未验证为拼多多实际面试题，也不表示你已经掌握。** 依据官网 JD、框架官方文档和算法作者资料整理，先理解概念与工程含义。

一句话摘要：SparseLR / FFM / DNN / RNN 的区别，PyTorch 从数据到梯度更新的完整链路。

**2026-09-11 准备入口调整：** 本页作为 ML/PyTorch 专项补充。整体准备先看[岗位画像与问题清单](2026-09-11-拼多多岗位画像与问题清单.md)，优先覆盖平台设计、编程基础与项目交付；公开面经及其匹配边界见[来源核验](2026-09-11-拼多多面经来源与核验.md)。

## 当前按哪个 JD 准备

**按用户 2026-09-11 的判断，以 9 月 10 日版 T024234 为当前准备依据。** 本次重新读取官网，页面显示机器学习平台工程师、上海、2026-09-10。旧版 T018734 只保留为历史比较，不再与新版并列为待选择项；邀请邮件与编号的绑定没有新增 HR 证据，不妨碍先按用户选定版本准备。[当前官网 JD](https://careers.pddglobalhr.com/jobs/detail?code=T024234)

| JD 层次 | 已披露内容的概括 | 对这份资料的影响 |
| --- | --- | --- |
| 工作职责 | 面向算法使用者做 ML 平台产品，包含资源调度、数据处理、深度学习及在线/离线架构；协作推进算法应用 | 不只问算法定义，也要知道训练任务如何运行和排障 |
| 基础要求 | 静态语言与动态语言能力、编程习惯、产品意识、独立解决问题与协作 | 不应把它理解成只做 Agent 编排的岗位 |
| 加分项 | 深度学习框架及其内部机制、RAG/Agent 产品经历；点名 SparseLR、FFM、DNN、RNN | 以下 20 题以这些关键词为主，树模型仅作常见补充 |

**先读哪几题（AI 建议）：** 第 1–5 题、9、12–14 题。其余按需要补。以下“追问”是练习方向，不代表已知面试题频率。

快速跳转：[SparseLR](拼多多-机器学习与PyTorch面试速补.md#section-2) · [FFM](拼多多-机器学习与PyTorch面试速补.md#section-3) · [PyTorch 架构](拼多多-机器学习与PyTorch面试速补.md#section-9) · [训练循环](拼多多-机器学习与PyTorch面试速补.md#section-13) · [常见排障](拼多多-机器学习与PyTorch面试速补.md#section-20)

## 1. LR 为什么可以做分类？损失函数是什么？

**参考回答：** 逻辑回归先计算线性分数 z = wᵀx + b，再用 sigmoid 把它变成正类概率 p = 1 / (1 + exp(-z))。二分类通常最小化交叉熵 −[y log p + (1−y) log(1−p)]，可加正则。固定阈值后得到类别；点击率预测也可以直接使用概率。

**追问与易错点：** 为什么叫线性模型？它的 log-odds 对输入是线性的；sigmoid 并没有让原始特征之间自动产生交互。标准未加权单样本损失对 z 的导数是 p−y。[依据：scikit-learn 逻辑回归](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression)

## 2. SparseLR 的“稀疏”指什么？L1 与 L2 有何区别？

**参考回答：** 要分清输入稀疏和参数稀疏。用户、商品等离散特征经 one-hot 或哈希编码后，单条样本只激活少数维度；这是输入稀疏。L1 惩罚绝对值之和，常使一部分权重变为零；L2 惩罚平方和，通常压小权重但不主动制造大量精确零。高维稀疏 LR 的工程重点还包括稀疏存储、索引与更新成本。

**追问与易错点：** SparseLR 不是唯一、标准化的算法名称，JD 未说明这里特指哪种实现；不能把它直接等同于“只用 L1”。可以解释两种稀疏性后再对齐上下文。[依据：L1 与 LR 稀疏性示例](https://scikit-learn.org/stable/auto_examples/linear_model/plot_logistic_l1_l2_sparsity.html)

## 3. LR、FM、FFM 的区别是什么？什么叫 field？

**参考回答：** LR 显式建模一阶贡献，交叉项通常要事先构造。FM 用低维向量内积学习两两特征交互；一个特征共用一条向量。FFM 进一步让向量依赖“对方特征属于哪个域”：用户、商品、设备可以是不同 field。例如同一个用户特征和商品交互、和设备交互时使用不同向量。

**记住式子：** FM 的交互项是 Σ(i<j)〈vᵢ,vⱼ〉xᵢxⱼ；FFM 改成 Σ(i<j)〈vᵢ,field(j), vⱼ,field(i)〉xᵢxⱼ。这里每个 vᵢ,field(j) 都是一条向量。

**追问与易错点：** field 是特征所属的类别组，不是样本字段值。FFM 表达更细，但若特征数 n、域数 f、向量维度 k，参数量大致从 FM 的 O(nk) 增至 O(nfk)；一条样本 m 个非零特征时，直接两两交互约 O(m²k)。不能说 FFM 一定比 FM 效果好。[依据：FFM 作者论文](https://www.csie.ntu.edu.tw/~cjlin/papers/ffm.pdf)、[作者实现 LIBFFM](https://www.csie.ntu.edu.tw/~cjlin/libffm/)

## 4. DNN 如何处理离散特征？Embedding 到底是什么？

**参考回答：** DNN 是多层神经网络的泛称。常见推荐模型把离散 ID 查表映射为可训练的 Embedding，与数值特征拼接，再经过多层线性变换和非线性激活输出预测。Embedding 可以理解为“按 ID 选择参数矩阵中的一行”，不是现成的语义知识库；这些向量在任务损失下学习。

**追问与易错点：** 没有非线性激活，多层线性变换仍可合并为一层。词表 N、维度 d 的 Embedding 约有 N×d 个参数，大词表可能比后面的网络更占内存；未知 ID、特征版本和线上线下一致性也要考虑。[依据：PyTorch 网络教程](https://docs.pytorch.org/tutorials/beginner/basics/buildmodel_tutorial.html)、[Embedding](https://docs.pytorch.org/docs/main/generated/torch.nn.Embedding.html)

## 5. RNN 为什么适合序列？LSTM 和 GRU 改进在哪里？

**参考回答：** RNN 按顺序读取输入，用前一时刻隐藏状态和当前输入生成新状态，同一组参数在时间步之间共享。它适合表达行为序列，但反向传播跨很多步时容易梯度消失或爆炸。LSTM 用 cell state 及输入、遗忘、输出门控制信息流；GRU 用更简化的门控结构。门控缓解长期依赖问题，不能保证完全消除。

**追问与易错点：** 训练时沿时间展开做反向传播；padding 要与有效长度配合。Transformer 的注意力不依靠同样的逐步递归结构，但没有必要为了这份 JD 先背完 Transformer 全部细节。[依据：LSTM](https://docs.pytorch.org/docs/main/generated/torch.nn.LSTM.html)、[GRU](https://docs.pytorch.org/docs/main/generated/torch.nn.GRU.html)

## 6. 决策树、随机森林、GBDT 有什么区别？

**参考回答：** 决策树通过特征切分预测；单棵深树容易过拟合。随机森林对样本做抽样、对候选特征引入随机性，训练多棵树再聚合，主要降低方差。GBDT 逐轮加入弱学习器，拟合当前损失的负梯度，逐步改善预测。只有平方损失等特定情形，才可直接说“拟合残差”。

**追问与易错点：** 结构化表格任务可先用树模型作基线；稀疏 ID 交互或序列任务常需要其他建模方式。这里是补充知识，JD 没有点名树模型。[依据：scikit-learn 集成学习](https://scikit-learn.org/stable/modules/ensemble.html)

## 7. 准确率很高就代表模型好吗？如何发现过拟合或数据泄漏？

**参考回答：** 点击率极低时，全部预测不点击也可能有很高准确率。ROC-AUC 关注排序，log loss 评价概率预测；按业务再看 precision、recall 或 PR 曲线。训练集明显好于验证集可能是过拟合，也可能有分布差异；不能只看单一指标下结论。

**追问与易错点：** 先分训练/验证/测试，再仅在训练集拟合预处理；避免把未来行为、事后标签或跨集合重复样本带入特征。离线 AUC 提升不保证线上收益提升。[依据：评估指标](https://scikit-learn.org/stable/modules/model_evaluation.html)、[数据泄漏](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage)

## 8. SGD、Adam、学习率、batch size 分别管什么？

**参考回答：** SGD 根据当前小批量梯度更新参数；Momentum 叠加历史方向。Adam 维护梯度的一阶、二阶矩估计，带偏差校正，自适应调整各参数的更新尺度。学习率控制步长；batch size 影响梯度估计噪声、吞吐和显存。Adam 通常更易上手，但不保证所有任务最终效果更好。

**追问与易错点：** Adam 通常需要额外保存两组与参数同量级的状态，因此恢复训练不只要模型权重。增大 batch 后如何调学习率需要实验，不能机械照搬线性放大。[依据：PyTorch Adam](https://docs.pytorch.org/docs/stable/generated/torch.optim.Adam.html)

## 9. 如何用一分钟讲清 PyTorch 的架构？

**参考回答：** 上层用 Python API、nn.Module、数据加载器和优化器描述训练；Tensor 保存数据及形状、步长、类型、设备等信息。算子经 Dispatcher 按设备、Autograd 等分发键选择实现，底层由 ATen 等算子库与 CPU/GPU 内核执行。Autograd 记录可微计算并反向求导。torch.compile 是可选的编译优化路径，不是训练必须经过的一步。

| 层次 | 主要组件 | 回答“负责什么” |
| --- | --- | --- |
| 使用层 | Dataset/DataLoader、nn.Module、optim | 组织数据、模型和训练更新 |
| 执行与求导 | Tensor、Dispatcher、Autograd | 管数据、选择算子实现、算梯度 |
| 计算后端 | ATen 算子、CPU/CUDA 等 kernel 与后端库 | 实际完成张量运算 |
| 可选编译 | Dynamo、AOTAutograd、Inductor | 捕获和优化计算，减少运行开销 |

**易错点：** 这是一张职责图，不是严格的单向调用栈；Autograd 和 Dispatcher 会协作、再分发。不要照搬早年的 TH/THC 架构文章作为今天的全貌。[依据：Dispatcher 官方教程](https://docs.pytorch.org/tutorials/advanced/dispatcher)、[当前 compiler 文档](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler.html)

## 10. Tensor 与数组有什么区别？view 和 reshape 呢？

**参考回答：** Tensor 除了多维数据，还携带 dtype、device、shape、stride 等信息，可参与自动求导和设备上的运算。view 需要形状与现有步长兼容；reshape 在可能时返回视图，否则可能复制。转置常只改步长，不立即搬动数据。

**追问与易错点：** 非连续 Tensor 不代表所有算子都不能处理；contiguous() 必要时会分配并复制，滥用会增加内存与带宽开销。[依据：Tensor Views](https://docs.pytorch.org/docs/main/tensor_view.html)

## 11. nn.Module、Parameter、buffer 有什么区别？

**参考回答：** Module 管理模型结构与注册的子模块、参数和 buffer；Parameter 赋给 Module 属性后会被注册，通常交给优化器学习。buffer 用于保存不作为优化参数更新的状态，例如 BatchNorm 的运行统计量。普通 Tensor 属性不会自动拥有全部这些管理行为。

**追问与易错点：** 一般调用 model(x)，不要直接调 model.forward(x) 绕过模块调用机制。state_dict 通常包含参数和持久 buffer；Parameter 也可以被冻结，并非永远都训练。[依据：PyTorch Modules](https://docs.pytorch.org/docs/main/notes/modules.html)

## 12. Autograd 如何工作？backward 会更新参数吗？

**参考回答：** 在需要求导的计算中，前向运算建立记录依赖关系的计算图。backward 依据链式法则反向传播，将梯度累积到相应叶子参数的 .grad；**更新权重由 optimizer.step() 完成**。常规 eager 执行会随本次前向动态构图，因此可以处理 Python 控制流。

**追问与易错点：** 不需要每批都 retain_graph=True；正常反向后会释放不再需要的中间保存值。detach 会切断该结果的求导关联，并不等于复制数据。[依据：Autograd mechanics](https://docs.pytorch.org/docs/main/notes/autograd.html)

## 13. 最小训练循环是什么？为什么要清梯度？

**参考回答：** 取 batch → 前向得到预测 → 计算损失 → 反向算梯度 → 优化器更新。PyTorch 的梯度默认累积，因此常规每次更新前要清零；有意做梯度累积时则在多个 micro-batch 后更新，并正确处理 loss 的缩放。

```python
import torch
from torch import nn

# 演示：32 条样本、8 个浮点特征；二分类，标签形状与 logits 相同。
x = torch.randn(32, 8)
y = torch.randint(0, 2, (32, 1)).float()
model = nn.Linear(8, 1)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.BCEWithLogitsLoss()

model.train()
optimizer.zero_grad(set_to_none=True)
logits = model(x)
loss = loss_fn(logits, y)
loss.backward()       # 算梯度
optimizer.step()      # 更新参数
```

**易错点：** BCEWithLogitsLoss 内部处理 sigmoid，不要先额外 sigmoid。上面是概念示例，不代表你的生产经历，也没有完成 GPU/训练效果验收。[依据：官方训练循环教程](https://docs.pytorch.org/tutorials/beginner/basics/optimization_tutorial.html)

## 14. model.eval()、no_grad()、inference_mode() 是一回事吗？

**参考回答：** eval() 改变 Dropout、BatchNorm 等模块的训练/推理行为，不自动关闭求导。no_grad() 控制该上下文中不记录反向图；inference_mode() 进一步去掉一些记录开销，但对其中创建的 Tensor 后续参与求导有更多限制。常见推理使用 eval() 配合 inference_mode()，有求导需求时另行安排。

**易错点：** 只加 no_grad 但忘记 eval，Dropout 仍可能随机丢弃；只调 eval 也不意味着不建图。[依据：Autograd 的 grad modes 与 evaluation mode](https://docs.pytorch.org/docs/main/notes/autograd.html#locally-disabling-gradient-computation)

## 15. Dataset、DataLoader、collate_fn 分别做什么？

**参考回答：** Dataset 定义如何访问样本，DataLoader 负责迭代、分批、采样及可选多进程读取，collate_fn 把若干样本组合成 batch，变长序列常在这里 padding。要区分逐索引读取的 map-style 与流式 iterable-style 数据集。

**追问与易错点：** worker 数量不是越多越好，要看解码、磁盘、CPU 和内存。GPU 等数据时应检查读取与拷贝耗时；不要一看到 GPU 利用率低就换模型。[依据：Dataset 与 DataLoader 教程](https://docs.pytorch.org/tutorials/beginner/basics/data_tutorial.html)

## 16. 保存模型和恢复训练有什么区别？

**参考回答：** 只做推理通常需要模型配置、state_dict 和一致的预处理。恢复训练还应保存优化器、学习率调度器、训练步数、使用时的 AMP scaler，以及复现所需的随机状态、数据位置和代码/数据版本。保存权重不等于保存完整实验。

**追问与易错点：** Adam 丢失历史状态后继续训练，会改变后续更新轨迹。平台侧要考虑 checkpoint 完整写入、版本对应和失败恢复；后两点是由平台职责推导出的练习方向。[依据：官方保存与加载指南](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html?highlight=load_state_dict)

## 17. 混合精度 AMP 为什么能加速？有什么风险？

**参考回答：** autocast 为适合的算子选择 FP16/BF16 等精度，其余保留较高精度；在支持的硬件上可能降低带宽和计算开销。FP16 训练常配 GradScaler，缩放 loss 后反传，再还原梯度尺度，减轻小梯度下溢。BF16 指数范围较大，通常无需同样的缩放。

**易错点：** 不是简单把整个模型 .half()；也不保证所有任务都更快。仍要检查溢出、NaN、模型质量和实际硬件收益。[依据：官方 AMP 文档](https://docs.pytorch.org/docs/stable/amp.html)

## 18. torch.compile 做了什么？为什么可能没变快？

**参考回答：** 常见路径中，Dynamo 捕获可编译图，AOTAutograd 参与训练前后向图处理，默认后端 Inductor 进行优化与代码生成。无法纳入同一图的部分可能产生 graph break；形状或控制条件变化可能触发重新编译。

**追问与易错点：** 需要区分第一次编译成本和预热后的稳态耗时；小任务、图经常中断、频繁重编译都可能抵消收益。默认优化路径不是每个模型都相同，不能说“打开必加速”。[依据：torch.compiler](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler.html)

## 19. DDP 多卡训练如何保持模型一致？

**参考回答：** 常见做法是一张卡对应一个进程，每个进程保存完整模型并读取不同数据分片；反向期间同步梯度，各进程在相同初始参数与优化器状态下执行相同更新。DDP 不自动帮你切好输入数据，需配合正确的采样与分片。

**追问与易错点：** DDP 同步核心是梯度，不是每步简单“把各卡参数平均”。增加卡数不会自动解决单个模型装不下的问题；模型状态分片是 FSDP 等策略关注的事。[依据：DDP 官方设计说明](https://docs.pytorch.org/docs/main/notes/ddp.html)

## 20. GPU 利用率低或显存 OOM，你怎么排查？

**参考回答：** 先用 profiler 或分段计时定位数据读取、CPU→GPU 拷贝、计算、同步通信哪个阶段耗时。利用率低时检查数据供给、小算子/Python 开销、同步和通信。OOM 则区分参数、梯度、优化器状态、激活及缓存预留，检查 batch/序列长度、是否把带图 Tensor 存进列表、是否错误保留计算图。

**可练习的处理顺序：** 先复现并测量，再考虑减小 micro-batch、梯度累积、AMP、激活重计算或状态分片，最后比较正确性、吞吐与峰值内存。CUDA 计时要考虑异步执行，不能只测 Python 函数返回时间。

**易错点：** empty_cache 只释放未占用的缓存块，不会释放仍被活跃 Tensor 使用的显存；它不是通用 OOM 解法。[依据：性能调优指南](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html)、[CUDA 内存管理](https://docs.pytorch.org/docs/main/notes/cuda.html#memory-management)

## 把知识接到这份平台岗位

**AI 建议的练习题：** “算法同事交给你一个训练脚本，你如何让它在平台上可靠地运行？”可以沿着数据/特征版本 → 镜像与依赖 → 资源申请 → 任务运行和日志指标 → checkpoint 与重试 → 模型产物及评估来回答，再指出哪些是自己做过、哪些只是方案。这比把名词都背出来更能连接这份 JD，但不表示该团队已经采用这些具体实现。

维护说明：技术依据核对到 2026-09-11；框架文档可能随版本变化。这里讲公开通用机制，不声称知道拼多多内部框架、考核频率或面试通过标准。
