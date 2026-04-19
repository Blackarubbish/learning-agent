# RAG Part 1 实践项目：文档加载与分割可视化

## 项目目标

加载一篇长文稿，通过可视化分析不同分割策略的效果。

## 项目结构

```
practice/
├── sample.txt           # 示例文档
├── main.py              # 主程序
└── analysis.py          # 分析工具
```

## 第一步：准备示例文档

```bash
# 创建一个测试文档
cat > sample.txt << 'EOF'
人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。这包括视觉感知、语音识别、决策制定和语言翻译等。

机器学习是人工智能的一个子集，它使用统计技术使计算机系统能够从数据中"学习"，而无需进行明确的编程。学习过程从观察或数据开始，如示例、直接经验或指令。

深度学习是机器学习的一个子集，它使用多层神经网络来分析各种因素的数据。与浅层学习相比，深度学习能够处理更复杂的模式识别任务。

自然语言处理（NLP）是人工智能和语言学的一个交叉领域，关注计算机与人类语言之间的交互。NLP 的应用包括机器翻译、情感分析和问答系统。

计算机视觉是另一个重要的人工智能领域，使计算机能够从图像或视频中获取有意义的信息。应用包括人脸识别、自动驾驶和医学影像分析。

强化学习是另一种机器学习范式，其中智能体通过与环境交互来学习决策策略。智能体根据当前状态采取行动，并从环境获得的奖励信号中学习。

人工智能的未来发展方向包括通用人工智能（AGI）、可解释人工智能（XAI）和人工智能安全研究。这些领域旨在创建更强大、更安全、更可预测的 AI 系统。
EOF
```

## 第二步：主程序 main.py

```python
"""
RAG Part 1 实践：文档加载与分割
运行：python main.py
"""

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def load_document(file_path: str):
    """加载文档"""
    loader = TextLoader(file_path)
    docs = loader.load()
    print(f"✅ 加载完成：{len(docs)} 个文档")
    return docs


def split_documents(docs, chunk_size: int, chunk_overlap: int):
    """分割文档"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "？", "！", ""]
    )
    chunks = splitter.split_documents(docs)
    return chunks


def analyze_chunks(chunks):
    """分析分割结果"""
    print(f"\n📊 分割结果分析：共 {len(chunks)} 个 chunks\n")

    for i, chunk in enumerate(chunks):
        content = chunk.page_content
        metadata = chunk.metadata
        print(f"--- Chunk {i + 1} ---")
        print(f"长度: {len(content)} 字符")
        print(f"内容: {content[:100]}{'...' if len(content) > 100 else ''}")
        print(f"元数据: {metadata}")
        print()


def main():
    # 1. 加载文档
    print("=" * 50)
    print("第一步：加载文档")
    print("=" * 50)
    docs = load_document("sample.txt")

    # 2. 使用不同参数分割
    configs = [
        {"chunk_size": 200, "chunk_overlap": 20},
        {"chunk_size": 500, "chunk_overlap": 50},
        {"chunk_size": 1000, "chunk_overlap": 100},
    ]

    for config in configs:
        print("\n" + "=" * 50)
        print(f"第二步：分割文档 (chunk_size={config['chunk_size']}, "
              f"chunk_overlap={config['chunk_overlap']})")
        print("=" * 50)
        chunks = split_documents(docs, **config)
        analyze_chunks(chunks)


if __name__ == "__main__":
    main()
```

## 第三步：运行并观察

```bash
source .venv/bin/activate
cd practice
python main.py
```

## 实践任务

### 任务 1：观察 chunk_size 影响
- 把 `chunk_size` 分别设为 100、500、1000
- 观察每个配置产生多少 chunks
- 理解大小 chunks 的 trade-off

### 任务 2：观察 chunk_overlap 影响
- 固定 `chunk_size=500`
- 把 `chunk_overlap` 分别设为 0、50、200
- 观察重叠是如何保持上下文连续的

### 任务 3：分析分割质量
- 在 `sample.txt` 中添加你自己的内容（代码、表格、列表）
- 观察不同格式内容的分割效果
- 思考什么情况需要自定义 separator

### 任务 4（挑战）：处理 PDF

pypdf 已安装，可直接使用：

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("your_file.pdf")
docs = loader.load()

# 分割 PDF
chunks = split_documents(docs, chunk_size=500, chunk_overlap=50)
```

## 预期输出示例

```
==================================================
第一步：加载文档
==================================================
✅ 加载完成：1 个文档

==================================================
第二步：分割文档 (chunk_size=200, chunk_overlap=20)
==================================================

📊 分割结果分析：共 8 个 chunks

--- Chunk 1 ---
长度: 180 字符
内容: 人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。这包括...
元数据: {'source': 'sample.txt'}
...
```

## 思考题

1. **chunk_size 是不是越小越好？**
   - 不是。太小的 chunk 丢失语义，太大稀释相似度。

2. **chunk_overlap 是不是越大越好？**
   - 不是。太大浪费 token，增加检索噪声。

3. **如何选择合适的 chunk_size？**
   - 根据：文档平均长度、Embedding 模型上下文窗口、检索粒度需求。

4. **中文和英文的分割策略有什么不同？**
   - 英文按空格分词，中文需要按标点和换行分割。
