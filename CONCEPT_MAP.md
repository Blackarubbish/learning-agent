# 概念地图

> 每次完成一个章节后，在这里连接新概念与已有知识。连线含义由你口述，AI Agent 帮你生成 Mermaid 代码。

```mermaid
graph TD
    %% ====== 基础层 ======
    subgraph 基础架构
        FastAPI[FastAPI Web框架] -->|提供 API 接口| RAG[RAG 检索增强生成]
        LangChain[LangChain 应用框架] -->|编排组件| RAG
    end

    %% ====== 文档处理层 ======
    subgraph 文档处理
        DocLoader[文档加载器<br/>TextLoader/PDF] --> TextSplitter[文本分割<br/>RecursiveCharacterTextSplitter]
        TextSplitter --> Chunks[文档块]
    end

    %% ====== Embedding 层 ======
    subgraph 向量化
        Chunks --> EmbeddingModel[Embedding 模型<br/>Zhipu embedding-3]
        EmbeddingModel --> Vectors[向量表示]
    end

    %% ====== 检索层 ======
    subgraph 检索策略
        Vectors --> VectorSearch[向量检索<br/>语义相似度]
        Chunks --> BM25[BM25 关键词检索<br/>词频统计]
        VectorSearch --> RRF[RRF 融合<br/>倒数排名融合]
        BM25 --> RRF
        RRF --> Rerank[Rerank 精排<br/>Zhipu rerank]
        QueryTransform[查询变换<br/>MultiQuery/HyDE] --> VectorSearch
        QueryTransform --> BM25
    end

    %% ====== 向量数据库层 ======
    subgraph 向量存储
        Vectors --> FAISS[FAISS<br/>内存向量库]
        Vectors --> Milvus[Milvus<br/>分布式向量库]
    end

    %% ====== 生成层 ======
    subgraph 生成
        Rerank --> LLM[LLM 生成<br/>DeepSeek/Zhipu]
        LLM --> Answer[答案]
    end

    %% ====== 评估层 ======
    subgraph 评估体系
        Answer --> Faithfulness[Faithfulness<br/>忠实度评估]
        Rerank --> ContextPrecision[Context Precision<br/>上下文精确度]
        RRF --> ContextRecall[Context Recall<br/>上下文召回率]
        Answer --> AnswerRelevancy[Answer Relevancy<br/>答案相关性]
        Faithfulness --> Ragas[Ragas 评估框架]
        ContextPrecision --> Ragas
        ContextRecall --> Ragas
        AnswerRelevancy --> Ragas
        Ragas --> DeepEval[DeepEval 替代方案]
    end

    %% ====== Agent 层 ======
    subgraph Agent
        ReAct[ReAct 框架<br/>推理+行动循环]
        Tools[自定义工具<br/>Calculator/String/API]
        InfoAbstraction[信息抽象<br/>截断/摘要/引导]
        StatusFeedback[状态反馈<br/>进度/部分失败]
        ErrorRecovery[错误恢复接口<br/>原因+方案+示例]
        AgentMemory[Agent Memory<br/>对话历史/上下文管理]
        ErrorClass[错误三分类<br/>RETRYABLE/PARAMETER_ERROR/PERMANENT]
        StructFeedback[结构化错误反馈<br/>分类+摘要+修复建议]
        Reflection[Reflection 反射循环<br/>失败→反馈→修正→重试]
        Degradation[降级策略<br/>连续失败→转交人类]
        ReAct --> Tools
        Tools --> LLM
        Tools -->|质量属性| InfoAbstraction
        Tools -->|质量属性| StatusFeedback
        Tools -->|质量属性| ErrorRecovery
        Tools -->|失败时触发| ErrorClass
        ErrorClass -->|生成| StructFeedback
        StructFeedback -->|压缩上下文| InfoAbstraction
        StructFeedback -->|驱动| Reflection
        Reflection -->|增强 Observation| ReAct
        ErrorClass -->|系统化升级| ErrorRecovery
        Degradation -->|安全阀| Reflection
        Degradation -->|进阶: Reflexion| AgentMemory
        SQLAgent[SQL Agent<br/>db_schema + db_query]
        SchemaExplore[Schema 探索<br/>先查目录再翻书]
        SQLSafety[SQL 安全校验<br/>只读围栏]
        Tools -->|数据库工具| SQLAgent
        SQLAgent -->|依赖| InfoAbstraction
        SQLAgent -->|依赖| ErrorRecovery
        SQLAgent -->|包含| SchemaExplore
        SQLAgent -->|包含| SQLSafety
        AgentMemory --> ReAct
        FC[Function Calling<br/>JSON Schema + bind_tools]
        ReAct -->|工程化升级| FC
        FC -->|工具定义| Tools
        ResearchAssistant[研究助手 Agent<br/>FC 循环 + 工具工程 + 双层记忆 + 错误反射]
        FC -->|决策引擎| ResearchAssistant
        Tools -->|工具质量| ResearchAssistant
        AgentMemory -->|上下文注入| ResearchAssistant
        Reflection -->|错误修正闭环| ResearchAssistant
        Degradation -->|安全阀| ResearchAssistant
    end

    %% ====== 性能分析层 ======
    subgraph 性能优化
        cProfile[cProfile<br/>函数级性能采样]
        pstats[pstats<br/>统计数据解析]
        Cumtime[cumtime 累计耗时<br/>含子调用,找时间黑洞]
        Tottime[tottime 自身耗时<br/>不含子调用,找代码热点]
        Callers[print_callers<br/>调用链追踪]
        cProfile --> pstats
        pstats --> Cumtime
        pstats --> Tottime
        pstats --> Callers
        cProfile -->|测量| ResearchAssistant
    end

    %% ====== 缓存层 ======
    subgraph 缓存优化
        ExactCache[精确缓存<br/>SHA256 hash key]
        SemanticCache[语义缓存<br/>Embedding 相似度]
        TTL[TTL 过期时间<br/>平衡命中率与新鲜度]
        CacheAside[Cache-Aside 模式<br/>查缓存→调LLM→写缓存]
        ExactCache -->|完全相同才命中| CacheAside
        SemanticCache -->|意思相近即可命中| CacheAside
        TTL -->|设置过期时间| ExactCache
        TTL -->|设置过期时间| SemanticCache
        CacheAside -->|包裹| LLM
        %% 异步连接
        cProfile -->|I/O 瓶颈驱动| AsyncIO
        ExactCache -->|消除重复 I/O| AsyncIO
        SemanticCache -->|消除重复 I/O| AsyncIO
        FC -->|ainvoke 替代 invoke| Ainvoke
    end

    %% ====== 异步处理层 ======
    subgraph 异步处理
        AsyncIO[asyncio 事件循环<br/>单线程协作式调度]
        Ainvoke[llm.ainvoke<br/>异步 LLM 调用]
        AsyncSearch[asimilarity_search<br/>异步向量检索]
        Gather[asyncio.gather<br/>并发执行协程]
        AsyncIO -->|调度| Ainvoke
        AsyncIO -->|调度| AsyncSearch
        AsyncIO -->|批量并发| Gather
    end

    %% ====== 样式 ======
    style RAG fill:#f9f,stroke:#333,stroke-width:4px
    style RRF fill:#bbf,stroke:#333,stroke-width:2px
    style Rerank fill:#bfb,stroke:#333,stroke-width:2px
    style Ragas fill:#fbb,stroke:#333,stroke-width:2px
    style ReAct fill:#fcf,stroke:#333,stroke-width:3px
    style Tools fill:#ff9,stroke:#333,stroke-width:3px
    style FC fill:#ddf,stroke:#333,stroke-width:3px
    style ResearchAssistant fill:#ff9,stroke:#f00,stroke-width:4px
    style cProfile fill:#ddf,stroke:#333,stroke-width:3px
    style Cumtime fill:#bbf,stroke:#333,stroke-width:2px
    style Tottime fill:#bfb,stroke:#333,stroke-width:2px
    style ExactCache fill:#bbf,stroke:#333,stroke-width:2px
    style SemanticCache fill:#bfb,stroke:#333,stroke-width:2px
    style AsyncIO fill:#ff9,stroke:#333,stroke-width:3px
    style Ainvoke fill:#bbf,stroke:#333,stroke-width:2px
    style Gather fill:#bfb,stroke:#333,stroke-width:2px
```

---

## 概念关联记录

每完成一个章节后在此处手动记录：

| 章节 | 新概念 | 关联到已有概念 | 关联含义 |
|------|--------|--------------|---------|
| 07 | RRF 融合 | BM25 + 向量检索 | RRF 把两种检索结果按排名取倒数求和，不依赖绝对分数 |
| 07 | Rerank 精排 | RRF 融合 | Rerank 在 RRF 粗筛后用专用模型精排，类比搜索引擎二次排序 |
| 09 | Milvus 向量数据库 | FAISS | Milvus 是 FAISS 的生产级替代：多了增删改查、属性过滤、持久化、分布式 |
| 10 | 文档解析 (Unstructured) | TextLoader + 文本分割 | 解析能按结构分类（标题/正文/表格），避免分块截断和结构信息丢失 |
| 11 | AdvancedRAG 集成管线 | Query Transform + 混合检索 + Rerank | 管线串联：Multi-Query 改写决定天花板，混合检索互补盲区，Rerank 精排降噪，Faithfulness 防幻觉 |
| 12 | Agent / ReAct | LLM + Tools | RAG 是单向检索→生成，Agent 是循环思考→行动→观察→再思考，能调用外部工具完成任务 |
| 13 | 信息抽象 | Tools → LLM | 工具返回截断+摘要+引导，防止上下文过载；LLM 按引导逐层深入，用多轮循环弥补窗口限制 |
| 13 | 状态反馈 | Tools → ReAct | 工具报告进度+成功/失败详情+后续建议；Agent 据此在下一轮针对性地处理失败项 |
| 13 | 错误恢复接口 | Tools → LLM | 错误信息包含"原因+可用选项+正确示例"，让 LLM 自主修正而非盲猜 |
| 14 | Schema 探索 | Tools + 信息抽象 | Agent 先查目录再翻书——了解表结构后识别相关字段生成精确 SQL，避免 SELECT * 上下文爆炸 |
| 14 | SQL 安全校验 | Tools + 错误恢复 | \b 独立单词匹配拦截写操作，防止 Agent 幻觉导致数据篡改/删除等不可逆灾难 |
| 15 | Function Calling JSON Schema | ReAct + Tools | FC 把 ReAct 的工具定义从文本描述升级为 JSON Schema，解析可靠性从 ~80% 提升到 ~99%，还支持并行调用 |
| 16 | 短期记忆 (ShortTermMemory) | ReAct + AgentMemory | 内存全文缓冲区保存当前会话的完整交互历史，超出窗口则截断最早的消息 |
| 16 | 长期记忆 (LongTermMemory) | AgentMemory + FAISS | 向量存储保存用户偏好和关键决策，跨会话持久化，语义检索而非全文匹配 |
| 17 | 错误三分类 | 13章 错误恢复接口 | 把工具返回的错误信息升级为系统化三分类，让 LLM 的行为从"再试一次"变成"检查参数再试"或"立即放弃" |
| 17 | Reflection 反射循环 | 12章 ReAct | 反射是 ReAct Observation 环节的增强——失败时不只是返回错误，还附加分类+修复建议，让 LLM 自主修正 |
| 17 | 结构化错误反馈 (Compact Errors) | 13章 信息抽象 | 和工具输出截断同理：错误信息只给分类+摘要+修复建议，不堆栈追踪，按 12-Factor Agent 原则 9 压缩到上下文窗口 |
| 17 | 降级策略 | 16章 AgentMemory + Reflection | 连续失败触发降级防止死循环；Reflexion 是进阶版——把失败经验写入长期记忆跨会话避免重复犯错 |
| 18 | ResearchAssistant 集成 | FC + Tools + AgentMemory + Reflection + Degradation | 四大模块形成完整能力闭环：FC循环=决策框架，工具工程=可靠性，记忆=体验，反射=安全网 |
| 18 | Agent 模块职责边界 | 13章工具工程 + 16章记忆 + 17章错误处理 | 各模块有清晰的职责边界：工具保证单次调用成功率，记忆消除重复声明摩擦，反射阻断错误累积衰减 |
| 18 | 错误分类权威来源 | 17章错误三分类 + 13章错误恢复接口 | 工具的 category 是唯一权威来源；classify_error 只用于意外异常的分类兜底，避免两个分类系统冲突 |
| 19 | cProfile + pstats | ResearchAssistant + LLM + httpx | cProfile 对 Agent.run() 做函数级采样；cumtime 定位网络 I/O 时间黑洞（LLM API 调用占 90%+），tottime 定位 CPU 热点；print_callers 追踪慢函数调用链 |
| 20 | 精确缓存 (ExactMatchCache) | 19章性能瓶颈 + LLM + fakeredis | SHA256(prompt) 做 key，字符级完全相同才命中；第二轮 benchmark 0.0s 证明缓存消除了 LLM API 瓶颈 |
| 20 | 语义缓存 (SemanticCache) | 精确缓存 + Embedding + FAISS | 用 embedding 余弦相似度匹配"意思相近"的查询；threshold 控制命中范围和准确度，解决同义改写穿透精确缓存的问题 |
| 21 | asyncio 事件循环 | cProfile + ExactCache + FC | cProfile 发现的 I/O 瓶颈驱动 async 改造；缓存消除重复 I/O，async 让非重复 I/O 等待时间重叠；`llm.ainvoke()` 是 FC 循环的异步升级 |

<!-- 继续往下写... -->

---

## 核心流程一句话总结

```
RAG 管线:
用户问题 → [查询变换优化] → [多路检索(BM25+向量)] → [RRF融合] → [Rerank精排] → [LLM生成] → [评估验证]
                ↑__________________检索增强__________________↑

Agent 工具调用闭环:
用户任务 → [ReAct 思考] → [工具调用] → [成功→Observation | 失败→错误分类→结构化反馈→Reflection 修正→重试]
                              ↑__连续失败→降级(转交人类)__↑

ResearchAssistant 集成闭环:
用户输入 → [长期记忆检索(偏好)] → [短期记忆注入(历史)] → [FC 循环(bind_tools)] 
    → [工具执行(信息抽象+状态反馈)] → [失败→工具分类(权威)→反馈→重试/降级]
    → 最终答案 → [更新短期记忆]

异步并发加速:
同步: query1 → 等API → query2 → 等API → ... (串行, Σ耗时)
异步: query1..N → [同时发请求] → [I/O等待重叠] → [同时收结果] (并发, ≈max耗时)
    llm.invoke() → await llm.ainvoke()
    vectorstore.similarity_search() → await vectorstore.asimilarity_search()
    for q in queries → await asyncio.gather(*tasks)
```