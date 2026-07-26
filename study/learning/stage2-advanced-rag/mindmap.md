# Stage 2: 高级 RAG

## 06 Query Transformation
### 核心思想
- 检索前改写查询, 提升召回质量
- 解决查询与文档表达方式不同的问题
### Multi-Query
- LLM生成多个改写版本
- 并行检索后RRF合并
- 适用: 覆盖面广, 召回率要求高
### HyDE
- 先生成假设性答案文档
- 用假设文档去检索相似真实文档
- 适用: 复杂抽象问题
### Sub-Query
- 复杂问题拆分为多个子问题
- 适用: 多跳推理, 复合问题

## 07 混合检索与 Rerank
### BM25 稀疏检索
- 基于词频的概率检索算法
- IDF × TF 评分
- k1词频饱和, b长度归一化
- 适用: 精确关键词匹配
### 向量检索 密集检索
- Embedding语义相似度
- 适用: 语义相近但用词不同
### RRF 融合
- 倒数排名融合
- 不依赖绝对分数, 对异构分数鲁棒
- k=60 平滑参数
### Rerank 精排
- RRF粗筛后用专用模型精排
- Cohere / 智谱 Rerank API
- 类比: 搜索引擎二次排序
### Pipeline
- 查询→BM25+向量→RRF融合→Rerank→LLM生成

## 08 RAG 评估体系
### 为什么评估
- 没有量化指标, 优化就是盲人摸象
- 告诉你哪里好、哪里差、该往哪优化
### 两个维度
- 检索质量: 检索到的东西对不对 (垃圾进→垃圾出)
- 生成质量: 生成的答案好不好 (好材料也可能做坏菜)
### 五大指标
- Context Precision: 排序质量
- Context Recall: 覆盖度
- Faithfulness: 不瞎编, 答案忠实于上下文
- Answer Relevance: 不跑题, 答案回应了问题
- Answer Correctness: 答案与标准答案匹配度
### 易混淆对比
- Faithfulness vs Relevance: 不瞎编 vs 不跑题
- Precision vs Recall: 排序质量 vs 覆盖度
### 框架
- Ragas / DeepEval

## 09 Milvus 向量数据库
### 核心优势
- 分布式架构, 支持10亿+向量
- 多种索引: FLAT/IVF/HNSW/DiskANN
- 混合检索: 向量+属性过滤
- 生产级持久化+增量写入
### vs FAISS
- FAISS: 内存向量索引, demo/小规模
- Milvus: 分布式向量数据库, 生产环境
### 部署方式
- Milvus Lite: 本地开发, 数十万级
- Milvus Standalone: 单机, 百万级
- Milvus Cluster: 分布式, 十亿级
### 核心操作
- create_collection: 创建集合
- insert: 插入带元数据的向量
- search: 向量相似度搜索
- query: 按属性过滤查询
- upsert/delete: 更新/删除

## 10 高级数据处理
### 为什么需要
- 复杂文档含表格/图片/布局
- 朴素TextLoader丢失结构信息
### 工具对比
- Unstructured.io: 通用文档, 简单易用
- MinerU: 复杂PDF, 国产开源高精度
- Docling: 学术论文, 布局感知
- PDF-Extract-Kit: 中文PDF
### 核心能力
- 按元素类型分类: Title/NarrativeText/Table
- mode="elements": 结构化解析
- 文本清洗: 空行/特殊字符/引用标记

## 11 周度总结
### AdvancedRAG 管线
- 查询变换→混合检索→RRF→Rerank→生成→评估
### 技术整合
- Multi-Query + BM25 + 向量检索 + RRF + Rerank + LLM
### 核心认知
- 查询改写决定天花板
- 混合检索互补盲区
- Rerank精排降噪
- 评估闭环持续优化
