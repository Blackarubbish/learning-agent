from langchain_community.llms import Minimax
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os


deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set")

llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    openai_api_key=deepseek_api_key,
    base_url="https://api.deepseek.com/v1",
)


def llm_invoke():
    response = llm.invoke("你好")
    print(response)


def prompt_template(langguage: str, task: str):
    prompt = ChatPromptTemplate.from_messages(
        [("system", "你是 {language} 专家"), ("user", "用 {language} 写一个 {task}")]
    )
    chain = prompt | llm
    response = chain.invoke({"language": "Python", "task": "快速排序"})
    print(response)


def run():
    prompt_template(langguage="rust", task="快速排序")


run()
