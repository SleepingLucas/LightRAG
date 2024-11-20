import asyncio
import os
from dataclasses import dataclass
from typing import Any, Union, Tuple, List, Dict
import inspect
from lightrag.utils import logger
from ..base import BaseGraphStorage
from neo4j import (
    AsyncGraphDatabase,
    exceptions as neo4jExceptions,
    AsyncDriver,
    AsyncManagedTransaction,
)


from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


@dataclass
class Neo4JStorage(BaseGraphStorage):
    """
    Neo4j 图数据库存储实现
    """
    
    @staticmethod
    def load_nx_graph(file_name):
        print("no preloading of graph with neo4j in production")

    def __init__(self, namespace, global_config):
        super().__init__(namespace=namespace, global_config=global_config)
        self._driver = None
        self._driver_lock = asyncio.Lock()
        URI = os.environ["NEO4J_URI"]
        USERNAME = os.environ["NEO4J_USERNAME"]
        PASSWORD = os.environ["NEO4J_PASSWORD"]
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            URI, auth=(USERNAME, PASSWORD)
        )
        return None

    def __post_init__(self):
        self._node_embed_algorithms = {
            "node2vec": self._node2vec_embed,
        }

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def __aexit__(self, exc_type, exc, tb):
        if self._driver:
            await self._driver.close()

    async def index_done_callback(self):
        print("KG successfully indexed.")

    async def has_node(self, node_id: str) -> bool:
        displayName = node_id.strip('"')

        async with self._driver.session() as session:
            query = (
                f"MATCH (n {{displayName: $displayName}}) RETURN count(n) > 0 AS node_exists"
            )
            result = await session.run(query, displayName=displayName)
            single_result = await result.single()
            logger.debug(
                f'{inspect.currentframe().f_code.co_name}:query:{query}:result:{single_result["node_exists"]}'
            )
            return single_result["node_exists"]

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        entity_name_source = source_node_id.strip('"')
        entity_name_target = target_node_id.strip('"')

        async with self._driver.session() as session:
            query = (
                f"MATCH (a {{displayName: $entity_name_source}})-[r]-(b {{displayName: $entity_name_target}}) "
                "RETURN COUNT(r) > 0 AS edgeExists"
            )
            result = await session.run(query, entity_name_source=entity_name_source, entity_name_target=entity_name_target)
            single_result = await result.single()
            logger.debug(
                f'{inspect.currentframe().f_code.co_name}:query:{query}:result:{single_result["edgeExists"]}'
            )
            return single_result["edgeExists"]

        def close(self):
            self._driver.close()

    async def get_node(self, node_id: str) -> Union[dict, None]:
        async with self._driver.session() as session:
            entity_name = node_id.strip('"')
            query = f"MATCH (n {{displayName: $entity_name}}) RETURN n"
            result = await session.run(query, entity_name=entity_name)
            record = await result.single()
            if record:
                node = record["n"]
                node_dict = dict(node)
                logger.debug(
                    f"{inspect.currentframe().f_code.co_name}: query: {query}, result: {node_dict}"
                )
                return node_dict
            return None

    async def node_degree(self, node_id: str) -> int:
        entity_name = node_id.strip('"')

        async with self._driver.session() as session:
            query = f"""
                MATCH (n {{displayName: $entity_name}})
                RETURN COUNT{{ (n)--() }} AS totalEdgeCount
            """
            result = await session.run(query, entity_name=entity_name)
            record = await result.single()
            if record:
                edge_count = record["totalEdgeCount"]
                logger.debug(
                    f"{inspect.currentframe().f_code.co_name}:query:{query}:result:{edge_count}"
                )
                return edge_count
            else:
                return None

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        entity_name_source = src_id.strip('"')
        entity_name_target = tgt_id.strip('"')
        src_degree = await self.node_degree(entity_name_source)
        trg_degree = await self.node_degree(entity_name_target)

        # Convert None to 0 for addition
        src_degree = 0 if src_degree is None else src_degree
        trg_degree = 0 if trg_degree is None else trg_degree

        degrees = int(src_degree) + int(trg_degree)
        logger.debug(
            f"{inspect.currentframe().f_code.co_name}:query:src_Degree+trg_degree:result:{degrees}"
        )
        return degrees

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> Union[dict, None]:
        entity_name_source = source_node_id.strip('"')
        entity_name_target = target_node_id.strip('"')
        """
        Find all edges between nodes of two given labels

        Args:
            source_node_label (str): Label of the source nodes
            target_node_label (str): Label of the target nodes

        Returns:
            list: List of all relationships/edges found
        """
        async with self._driver.session() as session:
            query = f"""
            MATCH (start {{displayName: $entity_name_source}})-[r]->(end {{displayName: $entity_name_target}})
            RETURN properties(r) as edge_properties
            LIMIT 1
            """#.format(
            #     entity_name_source=entity_name_source,
            #     entity_name_target=entity_name_target,
            # )

            result = await session.run(query, entity_name_source=entity_name_source, entity_name_target=entity_name_target)
            record = await result.single()
            if record:
                result = dict(record["edge_properties"])
                logger.debug(
                    f"{inspect.currentframe().f_code.co_name}:query:{query}:result:{result}"
                )
                return result
            else:
                return None

    async def get_node_edges(self, source_node_id: str) -> List[Tuple[str, str]]:
        node_name = source_node_id.strip('"')

        """
        Retrieves all edges (relationships) for a particular node identified by its label.
        :return: List of dictionaries containing edge information
        """
        query = f"""MATCH (n {{displayName: $node_name}})
                OPTIONAL MATCH (n)-[r]-(connected)
                RETURN n, r, connected"""
        async with self._driver.session() as session:
            results = await session.run(query, node_name=node_name)
            edges = []
            async for record in results:
                source_node = record["n"]
                connected_node = record["connected"]

                source_label = (
                    list(source_node.labels)[0] if source_node.labels else None
                )
                target_label = (
                    list(connected_node.labels)[0]
                    if connected_node and connected_node.labels
                    else None
                )

                if source_label and target_label:
                    edges.append((source_label, target_label))

            return edges

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (
                neo4jExceptions.ServiceUnavailable,
                neo4jExceptions.TransientError,
                neo4jExceptions.WriteServiceUnavailable,
                neo4jExceptions.ClientError,
            )
        ),
    )
    async def upsert_node(self, node_id: str, node_data: Dict[str, Any]):
        """
        在 Neo4j 数据库中插入或更新一个节点。

        Args:
            node_id: 节点的唯一标识符（作为 id 属性）
            node_data: 节点属性的字典
        """
        label = node_data.get('entity_type', 'UNKNOWN').strip('"')
        properties = node_data.copy()
        properties['displayName'] = node_id.strip('"')

        async def _do_upsert(tx: AsyncManagedTransaction):
            query = f"""
            MERGE (n {{displayName: $properties.displayName}})
            SET n += $properties
            REMOVE n:UNKNOWN
            SET n:{label}
            RETURN n
            """
            await tx.run(query, properties=properties, label=label)
            logger.debug(
                f"Upserted node with id '{properties['displayName']}', label '{label}' and properties: {properties}"
            )

        try:
            async with self._driver.session() as session:
                await session.execute_write(_do_upsert)
        except Exception as e:
            logger.error(f"Error during upsert: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (
                neo4jExceptions.ServiceUnavailable,
                neo4jExceptions.TransientError,
                neo4jExceptions.WriteServiceUnavailable,
            )
        ),
    )
    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: Dict[str, Any]
    ):
        """
        在两个节点之间插入或更新关系及其属性，节点通过其 id 标识。

        Args:
            source_node_id (str): 源节点的 id
            target_node_id (str): 目标节点的 id
            edge_data (dict): 要设置在关系上的属性字典
        """
        source_id = source_node_id.strip('"')
        target_id = target_node_id.strip('"')
        edge_properties = edge_data.copy()
        # 从 keywords 中提取第一个关键词作为关系类型
        keywords = edge_properties.get('keywords', '').split(',')
        rel_type = keywords[0].strip().strip('"') if keywords else 'RELATED_TO'

        async def _do_upsert_edge(tx: AsyncManagedTransaction):
            query = f"""
            MATCH (source {{displayName: $source_id}})
            MATCH (target {{displayName: $target_id}})
            MERGE (source)-[r:`{rel_type}`]->(target)
            SET r += $properties
            RETURN r
            """
            await tx.run(query, source_id=source_id, target_id=target_id, properties=edge_properties)
            logger.debug(
                f"Upserted edge from '{source_id}' to '{target_id}' with type '{rel_type}' and properties: {edge_properties}"
            )

        try:
            async with self._driver.session() as session:
                await session.execute_write(_do_upsert_edge)
        except Exception as e:
            logger.error(f"Error during edge upsert: {str(e)}")
            raise

    async def _node2vec_embed(self):
        print("Implemented but never called.")
