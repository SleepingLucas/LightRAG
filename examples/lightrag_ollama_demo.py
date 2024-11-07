import os
import logging
from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_model_complete, ollama_embedding
from lightrag.utils import EmbeddingFunc
import textract

WORKING_DIR = "./dickens"

logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s", level=logging.INFO)

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

rag = LightRAG(
    working_dir=WORKING_DIR,
    llm_model_func=ollama_model_complete,
    llm_model_name="qwen2.5:3b",
    llm_model_max_async=4,
    # llm_model_max_token_size=32768,
    llm_model_max_token_size=16384,
    llm_model_kwargs={"host": "http://localhost:11343", "options": {"num_ctx": 32768}},
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=512,
        func=lambda texts: ollama_embedding(
            texts, embed_model="viosay/conan-embedding-v1:latest", host="http://192.168.69.234:11343"
        ),
    ),
)

file_path = "人生海海.pdf"
text_content = textract.process(file_path)
rag.insert(text_content.decode('utf-8'))

# with open("./book.txt", "r", encoding="utf-8") as f:
#     rag.insert(f.read())

# Perform naive search
print(
    rag.query("What are the top themes in this story?", param=QueryParam(mode="naive"))
)

# Perform local search
print(
    rag.query("What are the top themes in this story?", param=QueryParam(mode="local"))
)

# Perform global search
print(
    rag.query("What are the top themes in this story?", param=QueryParam(mode="global"))
)

# Perform hybrid search
print(
    rag.query("What are the top themes in this story?", param=QueryParam(mode="hybrid"))
)
