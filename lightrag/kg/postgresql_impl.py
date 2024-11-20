import contextlib
from dataclasses import dataclass
from datetime import datetime
import asyncio
import os
from typing import AsyncGenerator, TypeVar, Union
from typing import (
    cast as typing_cast,
)
import numpy as np
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Integer, DateTime
from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy import func, select, desc, delete
from sqlalchemy.orm import (
    scoped_session,
)

from ..utils import logger
from ..base import BaseVectorStorage

T = TypeVar("T")


# Storage Factory
class PostgresStorageFactory:
    """PostgreSQL存储工厂类"""

    @staticmethod
    def get_storage_class(namespace: str) -> type[BaseVectorStorage]:
        """根据namespace返回对应的存储类"""
        storage_map = {
            "chunks": ChunkStorage,
            "entities": EntityStorage,
            "relationships": RelationshipStorage,
        }

        if namespace not in storage_map:
            raise ValueError(f"Unknown namespace: {namespace}")

        return storage_map[namespace]


# Base Models and Database Connection
class Base(DeclarativeBase):
    """SQLAlchemy 模型基类"""

    pass


class VectorModel(Base):
    """向量存储基础模型类"""

    __abstract__ = True

    # 删除类变量vector_dim,改为在实例化时动态设置
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workspace: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    createtime: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatetime: Mapped[datetime] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )


class ChunkModel(VectorModel):
    """文本块向量模型"""

    __tablename__ = "light_chunks"

    full_doc_id: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer)
    chunk_order_index: Mapped[int] = mapped_column(Integer)


class EntityModel(VectorModel):
    """实体向量模型"""

    __tablename__ = "light_entities"

    entity_name: Mapped[str] = mapped_column(Text)


class RelationshipModel(VectorModel):
    """关系向量模型"""

    __tablename__ = "light_relationships"

    src_id: Mapped[str] = mapped_column(Text)
    tgt_id: Mapped[str] = mapped_column(Text)


# Storage Implementation
class PostgresVectorStorage:
    """PostgreSQL向量存储实现类"""

    def __init__(self, model_cls: type[VectorModel], config: dict, embedding_func=None):
        """初始化存储"""
        self.model = model_cls
        self.workspace = config.get("workspace", "default")

        # 动态设置embedding字段
        if embedding_func:
            self.vector_dim = embedding_func.embedding_dim
            # 动态添加embedding列
            if not hasattr(self.model, "embedding"):
                self.model.embedding = mapped_column(
                    Vector(self.vector_dim), nullable=False
                )

        # 构建数据库连接URL
        url = "postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}".format(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", 5432),
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
            database=os.environ.get("POSTGRES_DB", "postgres"),
        )

        # 创建异步引擎
        self.engine = create_async_engine(url)
        self.session_maker: Union[scoped_session, async_sessionmaker] = (
            async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        )
        # self.async_session = async_sessionmaker(
        #     self.engine, class_=AsyncSession, expire_on_commit=False
        # )

    @contextlib.asynccontextmanager
    async def _make_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Make an async session."""
        async with self.session_maker() as session:
            yield typing_cast(AsyncSession, session)

    async def init_tables(self):
        """创建数据库表"""
        # 创建pgvector扩展
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # 创建表
            await conn.run_sync(Base.metadata.create_all)

        logger.info(f"Tables created successfully")

    async def upsert(self, data: dict[str, dict], embeddings: np.ndarray):
        """插入或更新数据"""
        async with self._make_async_session() as session:
            for (id_, item), embedding in zip(data.items(), embeddings):
                # 构造模型实例
                db_item = self.model(
                    id=id_,
                    embedding=embedding.tolist(),
                    workspace=self.workspace,
                    content=item["content"],
                    **self._get_extra_fields(item),
                )

                # 更新或插入
                await session.merge(db_item)

            await session.commit()

    async def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        """向量相似度搜索"""
        async with self._make_async_session() as session:
            # 构建查询
            stmt = (
                select(
                    self.model,
                    # self.model.content,
                    (
                        1 - self.model.embedding.cosine_distance(query_vector.tolist())
                    ).label("similarity"),
                )
                .where(self.model.workspace == self.workspace)
                .order_by(desc("similarity"))
                .limit(top_k)
            )

            result = await session.execute(stmt)
            result = result.fetchall()

            # 格式化结果
            return [dict(model.__dict__) for model, similarity in result]

    async def delete(self, ids: Union[str, list[str]]):
        """删除指定id的记录

        Args:
            ids: 单个id或id列表
        """
        if isinstance(ids, str):
            ids = [ids]

        async with self._make_async_session() as session:
            # 构建删除语句
            stmt = delete(self.model).where(self.model.id.in_(ids))
            await session.execute(stmt)
            await session.commit()

    async def delete_by_field(self, field_name: str, value: str):
        """根据字段值删除记录

        Args:
            field_name: 字段名
            value: 字段值
        """

        if not hasattr(self.model, field_name):
            raise ValueError(
                f"Field {field_name} not found in model {self.model.__name__}"
            )

        field = getattr(self.model, field_name)

        async with self._make_async_session() as session:
            # 构建删除语句
            stmt = delete(self.model).where(field == value)
            await session.execute(stmt)
            await session.commit()

    def _get_extra_fields(self, item: dict) -> dict:
        """获取模型特定的额外字段"""
        if self.model == ChunkModel:
            return {
                "full_doc_id": item.get("full_doc_id"),
                "tokens": item.get("tokens"),
                "chunk_order_index": item.get("chunk_order_index"),
            }
        elif self.model == EntityModel:
            return {"entity_name": item.get("entity_name")}
        elif self.model == RelationshipModel:
            return {"src_id": item.get("src_id"), "tgt_id": item.get("tgt_id")}
        return {}
    
    def ensure_event_loop(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop


# Wrapper Classes
@dataclass
class ChunkStorage(BaseVectorStorage):
    """文本块向量存储封装类"""

    def __post_init__(self):
        config = self.global_config
        self.storage = PostgresVectorStorage(
            ChunkModel, config, embedding_func=self.embedding_func
        )
        loop = self.storage.ensure_event_loop()
        loop.create_task(self.storage.init_tables())
        self.workspace = config.get("workspace", "default")

    async def upsert(self, data: dict[str, dict]):
        contents = [v["content"] for v in data.values()]
        embeddings = await self.embedding_func(contents)
        return await self.storage.upsert(data, embeddings)

    async def query(self, query: str, top_k=5) -> list[dict]:
        embedding = (await self.embedding_func([query]))[0]
        return await self.storage.search(embedding, top_k)


@dataclass
class EntityStorage(BaseVectorStorage):
    """实体向量存储封装类"""

    def __post_init__(self):
        config = self.global_config
        self.storage = PostgresVectorStorage(
            EntityModel, config, embedding_func=self.embedding_func
        )
        loop = self.storage.ensure_event_loop()
        loop.create_task(self.storage.init_tables())
        self.workspace = config.get("workspace", "default")

    async def upsert(self, data: dict[str, dict]):
        contents = [v["content"] for v in data.values()]
        embeddings = await self.embedding_func(contents)
        return await self.storage.upsert(data, embeddings)

    async def query(self, query: str, top_k=5) -> list[dict]:
        embedding = (await self.embedding_func([query]))[0]
        return await self.storage.search(embedding, top_k)

    async def delete_entity(self, entity_name: str):
        try:
            # 根据entity_name删除实体
            await self.storage.delete_by_field("entity_name", entity_name)
            logger.info(f"Entity {entity_name} deleted.")
        except Exception as e:
            logger.error(f"Error while deleting entity {entity_name}: {e}")


@dataclass
class RelationshipStorage(BaseVectorStorage):
    """关系向量存储封装类"""

    def __post_init__(self):
        config = self.global_config
        self.storage = PostgresVectorStorage(
            RelationshipModel, config, embedding_func=self.embedding_func
        )
        loop = self.storage.ensure_event_loop()
        loop.create_task(self.storage.init_tables())
        self.workspace = config.get("workspace", "default")

    async def upsert(self, data: dict[str, dict]):
        contents = [v["content"] for v in data.values()]
        embeddings = await self.embedding_func(contents)
        return await self.storage.upsert(data, embeddings)

    async def query(self, query: str, top_k=5) -> list[dict]:
        embedding = (await self.embedding_func([query]))[0]
        return await self.storage.search(embedding, top_k)

    async def delete_relation(self, entity_name: str):
        try:
            async with self.storage._make_async_session() as session:
                # 构建删除语句
                stmt = delete(RelationshipModel).where(
                    (RelationshipModel.src_id == entity_name)
                    | (RelationshipModel.tgt_id == entity_name)
                )
                await session.execute(stmt)
                await session.commit()
            logger.info(f"Relations for entity {entity_name} deleted.")
        except Exception as e:
            logger.error(
                f"Error while deleting relations for entity {entity_name}: {e}"
            )
