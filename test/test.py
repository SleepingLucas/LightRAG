import os
import sys
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache
from lightrag.llm import ollama_embedding
from lightrag.utils import EmbeddingFunc
from dotenv import load_dotenv
import asyncio
import nest_asyncio
import yappi
from langchain_community.document_loaders.csv_loader import CSVLoader
from lightrag.operate import extract_entities
nest_asyncio.apply()
from pyinstrument import Profiler

# ...其他导入...

load_dotenv()
# ...其他导入...

async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    return await openai_complete_if_cache(
        "qwen-plus",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        **kwargs,
    )


WORKING_DIR = "data/test_neo4j"
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

rag = LightRAG(
    working_dir=WORKING_DIR,
    workspace="test_lightrag",
    llm_model_func=llm_model_func,
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=512,
        func=lambda texts: ollama_embedding(
            texts, embed_model="viosay/conan-embedding-v1:latest", host="http://192.168.69.234:11343"
        ),
    ),
    chunk_token_size=500,
    log_level="INFO",
    vector_storage="PostgresVectorDBStorage",
    graph_storage="Neo4JStorage"
)
# ...其他初始化代码...

async def amain():
    res = await rag.aquery(
        "汤庸有哪些论文？",
        param=QueryParam(mode="global", only_need_context=True),
    )
    # res = await rag.aquery(
    #     "汤庸有哪些成就？",
    #     param=QueryParam(mode="local"),
    # )
    
    print(res)
    
if __name__ == "__main__":
    asyncio.run(amain())
