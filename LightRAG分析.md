## 数据存储

### 图数据库

使用 neo4j 作为图数据库。

- 实体：
  - <id>：插入图数据库时自动生成
  - description：实体描述
  - displayName：实体名称
  - entity_type：实体类型，与其标签相同，PERSON、PAPER等
  - source_id：来源id，表示信息是从哪些文本块记录而来。chunk-xxx
- 关系：
  - <id>：插入图数据库时自动生成
  - description：关系描述
  - keywords：关系的关键词，其类型(type)记录为第一个关键词
  - source_id：来源id，表示信息是从哪些文本块记录而来。chunk-xxx
  - weight：关系强度，表示源实体和目标实体之间关系的强度

以上信息均由插入文本时，LLM通过提示词 NOW_PROMPTS["entity_extraction"]得出。

信息更新流程：

`lightrag:ainsert()` -> `operate:extract_entities()` -> 通过 NOW_PROMPTS["entity_extraction"] 提示词调用 LLM 获取实体与关系信息 -> 通过 `operate:_merge_nodes_then_upsert()` 与 `operate:_merge_edges_then_upsert()` 插入图数据库



### 向量数据库

使用 postgresql + PGVector 作为向量数据库。有三个向量数据表，分别为： `lightrag_chunks`、`lightrag_entities`、`lightrag_relationships`。

- `lightrag_chunks`：存储文档分割后的文本块的信息
  - full_doc_id：文档 id，doc-xxx
  - tokens：文本块的 token 数
  - chunk_order_index：文本块在文档中的顺序
  - id：文本块 id，chunk-xxx
  - workspace：工作区名称
  - content：文本块内容
  - embedding：文本块的向量表示
- `lightrag_entities`：存储实体的信息
  - entity_name：实体名称
  - id：实体 id，ent-xxx
  - workspace：工作区名称
  - content：实体名称 + 实体描述
  - embedding：实体的向量表示
- `lightrag_relationships`：存储关系的信息
  - src_id：源实体名称
  - tgt_id：目标实体名称
  - id：关系 id，rel-xxx
  - workspace：工作区名称
  - content：关系关键词 + 源、目的实体名 + 关系描述
  - embedding：关系的向量表示

信息更新流程：

`lightrag_chunks` 表：
`lightrag:ainsert()` -> 在函数内切片文档 -> `self.chunks_vdb.upsert()` 将文本块信息插入向量数据库

`lightrag_entities` 表：
`lightrag:ainsert()` -> `operate:extract_entities()` -> 通过 NOW_PROMPTS["entity_extraction"] 提示词调用 LLM 获取实体信息 -> 处理后通过 `entity_vdb.upsert()` 插入向量数据库 -> `entity_vdb.upsert()` 中，以表中的 `contents` 字段作为向量的内容

`lightrag_relationships` 表：
`lightrag:ainsert()` -> `operate:extract_entities()` -> 通过 NOW_PROMPTS["entity_extraction"] 提示词调用 LLM 获取关系信息 -> 处理后通过 `relationships_vdb.upsert()` 插入向量数据库 -> `relationships_vdb.upsert()` 中，以表中的 `contents` 字段作为向量的内容



## query

LightRAG 有多种查询模式，分别是 local，global，hybrid，naive。naive 模式为普通RAG查询，在此不进行分析。除了 naive 模式，其他三种查询均按照一定流程进行：

1. 通过提示词 NOW_PROMPTS["keywords_extraction"] 调用LLM，对用户的问题进行关键词提取。
2. 根据关键词，通过函数 `_build_local_query_context()` 或 `_build_global_query_context()` 构建知识上下文。 hybrid 模式下，会同时调用两个函数，然后将两个上下文合并。
3. 通过提示词 NOW_PROMPTS["rag_response"]，整合上下文，调用LLM，生成回答。

其中最关键的部分为知识上下文的构建。下面分别分析 local 和 global 模式下的上下文构建流程。



### local_query

local_query 模式下，上下文构建调用函数 `_build_local_query_context()`。

1. 根据第一步得到的问题关键词，查询**实体向量数据库**，得到与关键词相关的实体列表。

    ```py
    results = await entities_vdb.query(query, top_k=query_param.top_k)
    ```

2. 根据实体列表，获取图数据库中的实体信息。

    ```py
    node_datas = await asyncio.gather(
        *[knowledge_graph_inst.get_node(r["entity_name"]) for r in results]
    )
    ```


3. 获取每个实体的度，后续会根据度的大小对实体进行排序。

    ```py
    node_degrees = await asyncio.gather(
        *[knowledge_graph_inst.node_degree(r["entity_name"]) for r in results]
    )
    ```

4. 根据以上获取到的信息，构建实体信息字典，keys: ['entity_type', 'displayName', 'description', 'source_id', 'entity_name', 'rank']

5. 调用函数 `_find_most_related_text_unit_from_entities()`，获取与实体最相关的文本单元

    ```py
    use_text_units = await _find_most_related_text_unit_from_entities(
        node_datas, query_param, text_chunks_db, knowledge_graph_inst
    ) 
    ```

    函数内部流程：

    - 获取每个实体的 source_id 列表（来源 id，chunk-xxx）
    - 根据传入的实体，获取实体的一跳邻居，并创建一个字典存储每个邻居与其对应的 source_id
    - 遍历每个实体的文本单元和边，计算每个文本单元的关系计数（对于每个实体的每个文本单元，对于该实体连接的每条边的目的节点，如果该目标节点的来源列表(chunk)包括该文本单元，则关系计数+1）
    - 根据上文向量数据库匹配到的节点顺序与关系计数，对文本单元进行排序
    - 根据 token 限制，截取最相关的文本单元列表，返回

6. 调用函数 `_find_most_related_edges_from_entities()`，获取与实体最相关的边

    ```py
    use_relations = await _find_most_related_edges_from_entities(
        node_datas, query_param, knowledge_graph_inst
    )
    ```

    函数内部流程：

    - 获取每个实体的与其邻居所连边的数据及该边的度数
    - 根据度数以及关系强度排序，返回

7. 截断实体列表，使其不超过最大 token 限制

8. 根据上文获得的实体信息，文本单元信息，边信息，构建表格形式的 csv 上下文

local 模式下构建的知识上下文，其核心是通过实体向量数据库查询到与问题关键词相关的实体，然后根据实体信息，获取与实体相关的文本单元及其所连的边。最终将实体信息，文本单元信息，边信息整合为一个表格形式的上下文。



### global_query

global_query 模式下，上下文构建调用函数 `_build_global_query_context()`。

1. 根据第一步得到的问题关键词，查询**关系向量数据库**，得到与关键词相关的关系列表。

    ```py
    results = await relationships_vdb.query(keywords, top_k=query_param.top_k)
    ```

2. 根据关系列表，获取图数据库中的关系信息。

    ```py
    edge_datas = await asyncio.gather(
        *[knowledge_graph_inst.get_edge(r["src_id"], r["tgt_id"]) for r in results]
    )
    ```

3. 获取每个关系的度，后续会根据度的大小对关系进行排序。

    ```py
    edge_degree = await asyncio.gather(
        *[knowledge_graph_inst.edge_degree(r["src_id"], r["tgt_id"]) for r in results]
    )
    ```

4. 根据以上获取到的信息，构建关系信息字典， keys: ['src_id', 'tgt_id', 'rank', 'keywords', 'weight', 'description', 'source_id']
   
5. 调用函数 `_find_most_related_entities_from_relationships()`，获取与关系最相关的实体

    ```py
    use_entities = await _find_most_related_entities_from_relationships(
        edge_datas, query_param, knowledge_graph_inst
    )
    ```

    函数内部流程：

    - 获取每个关系的源节点和目标节点的数据与度数
    - 根据最大 token 限制，获取与关系最相关的实体
    - 返回
  
6. 调用函数 `_find_related_text_unit_from_relationships()`，获取与关系最相关的文本单元

    ```py
    use_text_units = await _find_related_text_unit_from_relationships(
        edge_datas, query_param, text_chunks_db, knowledge_graph_inst
    )
    ```

    函数内部流程：

    - 获取每个关系的 source_id 列表（来源 id，chunk-xxx）
    - 根据来源列表，获取对应的文本单元
    - 排序并根据最大 token 长度截取后返回

7. 截断关系列表，使其不超过最大 token 限制

8. 根据上文获得的关系信息，实体信息，文本单元信息，构建表格形式的 csv 上下文

global 模式下构建的知识上下文，其核心是通过关系向量数据库查询到与问题关键词相关的关系，然后根据关系信息，获取与关系相关的实体及其所连的文本单元。最终将关系信息，实体信息，文本单元信息整合为一个表格形式的上下文。



### hybrid_query

hybrid_query 模式下，会同时调用 local 和 global 模式下的上下文构建函数，然后将两个上下文合并。