import os
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding
from lightrag.llm import ollama_model_complete, ollama_embedding
from lightrag.utils import EmbeddingFunc
import numpy as np
import textract
from dotenv import load_dotenv
import nest_asyncio 
nest_asyncio.apply() 

load_dotenv()

print(os.getenv("DASHSCOPE_API_KEY"))

WORKING_DIR = "./test_temp"

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


# async def llm_model_func(
#     prompt, system_prompt=None, history_messages=[], **kwargs
# ) -> str:
#     return await openai_complete_if_cache(
#         "solar-mini",
#         prompt,
#         system_prompt=system_prompt,
#         history_messages=history_messages,
#         api_key=os.getenv("UPSTAGE_API_KEY"),
#         base_url="https://api.upstage.ai/v1/solar",
#         **kwargs,
#     )
async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    return await openai_complete_if_cache(
        "qwen-turbo",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        **kwargs,
    )


# async def embedding_func(texts: list[str]) -> np.ndarray:
#     return await openai_embedding(
#         texts,
#         model="solar-embedding-1-large-query",
#         api_key=os.getenv("DASHSCOPE_API_KEY"),
#         base_url="https://api.upstage.ai/v1/solar",
#     )


# async def get_embedding_dim():
#     test_text = ["This is a test sentence."]
#     embedding = await embedding_func(test_text)
#     embedding_dim = embedding.shape[1]
#     return embedding_dim


# # function test
# async def test_funcs():
#     result = await llm_model_func("How are you?")
#     print("llm_model_func: ", result)

#     result = await embedding_func(["How are you?"])
#     print("embedding_func: ", result)


# asyncio.run(test_funcs())


async def main():
    try:
        # embedding_dimension = await get_embedding_dim()
        # print(f"Detected embedding dimension: {embedding_dimension}")

        rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=llm_model_func,
            # embedding_func=EmbeddingFunc(
            #     embedding_dim=embedding_dimension,
            #     max_token_size=8192,
            #     func=embedding_func,
            # ),
            embedding_func=EmbeddingFunc(
                embedding_dim=1024,
                max_token_size=512,
                func=lambda texts: ollama_embedding(
                    texts, embed_model="viosay/conan-embedding-v1:latest", host="http://192.168.69.234:11343"
                ),
            ),
        )

        # file_path = "人生海海.pdf"
        # text_content = textract.process(file_path)
        # rag.insert(text_content.decode('utf-8'))
        # with open("./temp.txt", "r", encoding="utf-8") as f:
        #     await rag.ainsert(f.read())

        # # Perform naive search
        # print(
        #     await rag.aquery(
        #         "What are the top themes in this story?", param=QueryParam(mode="naive")
        #     )
        # )
        # Perform naive search
        print(
            await rag.aquery(
                "汤庸是一个怎样的人？", param=QueryParam(mode="naive")
            )
        )

        # Perform local search
        print(
            await rag.aquery(
                "汤庸是一个怎样的人？", param=QueryParam(mode="local")
            )
        )

        # Perform global search
        print(
            await rag.aquery(
                "汤庸是一个怎样的人？",
                param=QueryParam(mode="global"),
            )
        )

        # Perform hybrid search
        print(
            await rag.aquery(
                "汤庸是一个怎样的人？",
                param=QueryParam(mode="hybrid"),
            )
        )
        
        
        
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
