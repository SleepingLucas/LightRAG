import asyncio
from dataclasses import dataclass
import numpy as np
import asyncpg
from typing import Union

from sympy import N
from ..utils import logger
from ..base import BaseVectorStorage


class PostgresDB:
    """PostgreSQL数据库连接管理类"""

    def __init__(self, config):
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6024)
        self.database = config.get("database", "postgres")
        self.user = config.get("user", "postgres")
        self.password = config.get("password", "123456")
        self.workspace = config.get("workspace", "default")
        self.pool = None

    async def init_pool(self):
        """初始化连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=1,
                max_size=10,
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def execute(self, query: str, *args):
        """执行SQL"""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            try:
                return await conn.execute(query, *args)
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}\nQuery: {query}")
                raise

    async def fetch(self, query: str, *args):
        """查询数据"""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, *args)
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}\nQuery: {query}")
                raise

    async def create_extension(self):
        """安装pgvector扩展"""
        await self.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    async def create_vector_table(
        self, table_name: str, dim: int, meta_fields: set = None
    ):
        """创建向量表"""
        # 基础列
        columns = [
            "id VARCHAR PRIMARY KEY",
            f"embedding vector({dim})",
            "workspace VARCHAR",
        ]

        # 添加元数据列
        if meta_fields:
            for field in meta_fields:
                columns.append(f"{field} TEXT")

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {','.join(columns)}
        );
        """
        # print(create_table_sql)
        await self.execute(create_table_sql)

        # 创建向量索引
        create_index_sql = f"""
        CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
        ON {table_name} 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
        await self.execute(create_index_sql)


@dataclass
class PostgresVectorDBStorage(BaseVectorStorage):
    """
    基于PostgreSQL的向量存储实现
    """
    
    cosine_better_than_threshold: float = 0.2
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: PostgresDB = None
        self.table_name = f"light_vectors_{self.namespace}"
        self.cosine_better_than_threshold = self.global_config.get(
            "cosine_better_than_threshold", self.cosine_better_than_threshold
        )
    
    # def __post_init__(self):
    #     """初始化"""
        
    #     # self.db: PostgresDB = None # 需要手动设置
    #     # 创建数据库连接

    async def init_table(self):
        """初始化表结构"""
        await self.db.create_extension()
        await self.db.create_vector_table(
            self.table_name, self.embedding_func.embedding_dim, self.meta_fields
        )

    async def upsert(self, data: dict[str, dict]):
        """插入或更新向量数据"""
        if not data:
            logger.warning("Empty data to insert")
            return []

        # 准备数据
        list_data = [
            {"id": k, **{k1: v1 for k1, v1 in v.items() if k1 in self.meta_fields}}
            for k, v in data.items()
        ]

        # 生成embedding
        contents = [v["content"] for v in data.values()]
        batches = [
            contents[i : i + self.global_config["embedding_batch_num"]]
            for i in range(0, len(contents), self.global_config["embedding_batch_num"])
        ]
        embeddings_list = await asyncio.gather(
            *[self.embedding_func(batch) for batch in batches]
        )
        embeddings = np.concatenate(embeddings_list)

        # 构造INSERT语句
        fields = ["id", "embedding", "workspace"] + list(self.meta_fields)
        placeholders = [f"${i+1}" for i in range(len(fields))]

        upsert_sql = f"""
        INSERT INTO {self.table_name} ({','.join(fields)})
        VALUES ({','.join(placeholders)})
        ON CONFLICT (id) DO UPDATE SET
        {','.join([f"{f}=excluded.{f}" for f in fields if f != 'id'])};
        """

        # 批量插入数据
        for i, item in enumerate(list_data):
            values = [item["id"], embeddings[i].tolist(), self.db.workspace]
            values.extend(item.get(f, "") for f in self.meta_fields)
            
            # 使用 asyncpg 插入数据时，确保 embedding 转换为适当的 vector 格式
            values[1] = f'[{",".join(map(str, values[1]))}]'  # 将 embedding 转换为 pgvector 的格式
            
            await self.db.execute(upsert_sql, *values)

        return list_data

    async def query(self, query: str, top_k=5) -> list[dict]:
        """向量近邻搜索"""
        # 生成query的embedding
        embedding = await self.embedding_func([query])
        embedding = embedding[0]
        
        pgvector_embedding = f'[{",".join(map(str, embedding))}]'  # 将 embedding 转换为 pgvector 的格式

        # 构造查询SQL
        fields = ["id"] + list(self.meta_fields)
        query_sql = f"""
        SELECT {','.join(fields)}, 
               1 - (embedding <=> $1::vector) as similarity
        FROM {self.table_name}
        WHERE workspace = $2
        AND 1 - (embedding <=> $1::vector) > $3
        ORDER BY embedding <=> $1::vector
        LIMIT $4;
        """

        # 执行查询
        results = await self.db.fetch(
            query_sql,
            pgvector_embedding,
            self.db.workspace,
            self.cosine_better_than_threshold,
            top_k,
        )

        # 格式化结果
        return [
            {**{k: row[k] for k in fields}, "distance": row["similarity"]}
            for row in results
        ]

    async def index_done_callback(self):
        """索引完成回调"""
        pass
