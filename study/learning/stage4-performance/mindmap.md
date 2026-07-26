# Stage 4: 系统性能优化

## 19 性能瓶颈分析 ✅
### 核心工具
- cProfile: Python内置确定性profiler, 函数级采样
- pstats: 统计数据解析和排序
- py-spy: 采样profiler, 可attach运行中进程
- 火焰图: 可视化调用栈耗时分布
### 核心指标
- cumtime累计耗时: 含子调用, 定位时间黑洞 (网络I/O)
- tottime自身耗时: 不含子调用, 定位CPU热点
- ncalls: 函数被调用次数
- print_callers: 追踪慢函数的调用链
### 实验方法
- 对ResearchAssistant.run()做cProfile
- 按cumtime排序→找时间黑洞, LLM API占90%+
- 按tottime排序→找代码热点
- print_callers→追踪慢函数是谁调用的
### 关键发现
- LLM API调用是最大瓶颈, 网络I/O
- Embedding计算其次
- FAISS向量检索通常不是瓶颈

## 20 缓存优化 Redis ✅
### 核心概念
- Cache-Aside模式: 先查缓存→未命中→调LLM→写缓存
- TTL: 过期时间, 避免缓存无限增长
- 缓存命中率: 衡量缓存效果的核心指标
### 精确缓存 ExactMatchCache
- SHA256(prompt) 做 key, 字符级完全匹配才命中
- 第二轮 benchmark 从 28s 降到 0s
- 适用: 高频重复查询（FAQ、固定 prompt 模板）
### 语义缓存 SemanticCache
- embedding 余弦相似度 > threshold 即命中
- 同义改写（"什么是 ML" vs "机器学习是什么"）共享缓存
- threshold 控制命中范围: 太高退化为精确匹配, 太低误匹配
### 关键发现
- fakeredis 零依赖替代 Redis, 开发测试无需额外服务
- AIMessage 不能直接存 Redis, 需转 str
- 精确缓存消除 LLM API 瓶颈, 语义缓存进一步覆盖同义改写

## 21 异步处理 Async ✅
### 核心概念
- asyncio: Python原生异步, 单线程事件循环
- await: 挂起协程让出CPU, 非阻塞等待
- I/O密集用async, CPU密集用线程池
### 关键 API
- llm.ainvoke: 异步LLM调用
- httpx.AsyncClient: 异步HTTP客户端
- vectorstore.asimilarity_search: 异步检索
- asyncio.gather: 并发执行多个协程
### 实验结论
- 5并发查询: 同步40.64s → 异步14.61s, 加速比2.8x
- await 是"挂起让路"而非"阻塞等待"
- 异步不加速单任务, 只让多任务I/O等待时间重叠

## 22 批处理优化 ✅
### 核心概念
- Embedding 批处理: API 级合并, N条文本 → 1次HTTP (真批处理)
- LLM 并发批处理: 框架级并发, N个prompt → N次HTTP (线程池)
- batch_size: 越大吞吐越高, 但收益递减, 有API rate limit上限
### 关键 API
- embeddings.embed_documents(texts): 批量向量化, 1次API处理N条
- llm.batch(prompts): 线程池并发LLM调用, 耗时≈max(单次)
- llm.batch(prompts, config={"max_concurrency": 5}): 限制并发度
- llm.abatch(prompts): 异步版batch, 用asyncio.gather
### 实验结论
- 30条Embedding: bs=1 耗时7.7s → bs=30 耗时0.69s, 加速11x
- LLM batch: 串行42.7s → batch 9.6s, 加速4.5x
- 收益递减: bs=1→5 省24次RTT(巨大), 5→10省3次(变小), 10→30省2次(边际)
- 性能差距来自网络往返(RTT), 不是服务端计算速度

## 23 高性能推理 vLLM 📌
### 核心概念
- vLLM: 高性能LLM推理引擎
- PagedAttention: 类似OS分页管理KV cache, 减少显存碎片
- Continuous Batching: 动态合并请求, 提升GPU利用率
### 关键特性
- OpenAI兼容API, 可直接替换
- 支持多种开源模型
- CPU模式可验证流程, 性能有限
### 实验设计
- 部署开源模型 Qwen2.5-1.5B
- 对比vLLM vs HuggingFace推理 tokens/s
- 测试不同并发数下的吞吐量变化
### 替代方案
- Ollama: 无GPU时的替代方案
- SGLang: vLLM的竞品方案

## 24 周度总结与压测 📌
### 核心工具
- locust: Python负载测试工具
- 自定义测试场景, 模拟N个用户并发
### 关键指标
- QPS: 每秒查询数
- P50/P99延迟: 中位数/尾部延迟
- 错误率: 失败请求占比
- 吞吐量: 单位时间处理的数据量
### 实验设计
- locust写测试脚本, 模拟N用户并发
- 分别压测优化前和优化后版本
- 产出完整对比报告: QPS/P50/P99/命中率/Token消耗
### 优化报告结构
- 基准数据→优化措施→效果量化→成本分析
### 总结维度
- Profiling: 瓶颈在哪, 和预期一致吗
- 缓存: 命中率达标了吗, 什么场景收益最大
- 异步: 并发加速比, 有无串行瓶颈
- 批处理: batch_size对吞吐影响曲线, 最优值
- vLLM: 自部署vs API服务, 成本和性能权衡
