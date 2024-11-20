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
    workspace="test_postgres_storage",
    llm_model_func=llm_model_func,
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=512,
        func=lambda texts: ollama_embedding(
            texts, embed_model="viosay/conan-embedding-v1:latest", host="http://192.168.69.234:11343"
        ),
    ),
    chunk_token_size=500,
    log_level="DEBUG",
    vector_storage="PostgresVectorDBStorage",
    graph_storage="Neo4JStorage"
)
# ...其他初始化代码...

# 加载需要插入的数据
doc_path = "data/paper/scholat_paper_ed/scholat_paper_ed_001.csv"
loader = CSVLoader(doc_path)
data = loader.load()
data = [d.page_content for d in data]
need_to_insert_data = data[16:17]

profiler = Profiler()
profiler.start()

asyncio.run(rag.ainsert(need_to_insert_data))

profiler.stop()

profiler.print()

with open("./test/profile_report.html", "w") as f:
    f.write(profiler.output_html())
print("Profiling report saved to profile_report.html")

# async def main():
# yappi.set_clock_type("wall")

# with yappi.run():
#     # await rag.ainsert(need_to_insert_data)
#     asyncio.run(rag.ainsert(need_to_insert_data))

# yappi.get_func_stats().print_all()
# yappi.get_func_stats().save("./test/profile_results.prof", type="pstat")
# yappi.get_thread_stats().print_all()


# if __name__ == "__main__":
#     asyncio.run(main())
    
# kernprof -l -o ./test/profile_results.lprof test/analyze_insert.py
