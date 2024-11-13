GRAPH_FIELD_SEP_ZH = "<SEP>"

PROMPTS_ZH = {}

PROMPTS_ZH["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS_ZH["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS_ZH["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS_ZH["process_tickers"] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

PROMPTS_ZH["DEFAULT_ENTITY_TYPES"] = ["组织", "人", "地理", "事件"]

PROMPTS_ZH["entity_extraction"] = """-目标-
给定一个可能与此活动相关的文本文档和一个实体类型列表，从文本中识别出所有这些类型的实体以及所有识别出的实体之间的关系。

-步骤-
1. 识别所有实体。对于每个识别出的实体，提取以下信息：
   - 实体名称：实体的名称，使用与输入文本相同的语言。如果是英文，则将名称大写。
   - 实体类型：以下类型之一：[{{entity_types}}]
   - 实体描述：对实体属性和活动的全面描述
   将每个实体格式化为 ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 从步骤1中识别出的实体中，识别出所有*明显相关*的实体对（source_entity, target_entity）。
   对于每对相关实体，提取以下信息：
   - 源实体：步骤1中识别出的源实体名称
   - 目标实体：步骤1中识别出的目标实体名称
   - 关系描述：解释为什么你认为源实体和目标实体是相关的
   - 关系强度：一个数字分数，表示源实体和目标实体之间关系的强度
   - 关系关键词：一个或多个总结关系总体性质的高级关键词，侧重于概念或主题而不是具体细节
   将每个关系格式化为 ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. 识别总结整个文本主要概念、主题或话题的高级关键词。这些关键词应捕捉文档中存在的总体思想。
   将内容级关键词格式化为 ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. 使用**{record_delimiter}**作为列表分隔符，以单个列表的形式返回步骤1和2中识别出的所有实体和关系。

5. 完成后，输出{completion_delimiter}

######################
-示例-
######################
示例1：

实体类型：[人, 技术, 任务, 组织, 地点]
文本：
当亚历克斯紧咬牙关时，泰勒的权威确定性背景下的挫败感变得迟钝。正是这种竞争的潜流让他保持警觉，他和乔丹对发现的共同承诺是一种无声的反抗，反对克鲁兹对控制和秩序的狭隘愿景。

然后泰勒做了一件意想不到的事。他们在乔丹旁边停了下来，片刻间，带着某种敬畏的目光观察着设备。“如果这项技术能被理解……”泰勒说，声音低了下来，“这可能会改变我们的游戏规则。对我们所有人来说。”

早先的轻视似乎动摇了，取而代之的是对手中重物的勉强尊重。乔丹抬起头，短暂的心跳间，他们的目光与泰勒的目光交汇，意志的无言冲突软化成不安的休战。

这是一个微小的变化，几乎察觉不到，但亚历克斯内心点头表示注意。他们都是通过不同的路径来到这里的
################
输出：
("entity"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"人"{tuple_delimiter}"亚历克斯是一个角色，他经历了挫败感，并观察到其他角色之间的动态。"){record_delimiter}
("entity"{tuple_delimiter}"泰勒"{tuple_delimiter}"人"{tuple_delimiter}"泰勒被描绘成具有权威确定性，并对设备表现出一瞬间的敬畏，表明其观点的变化。"){record_delimiter}
("entity"{tuple_delimiter}"乔丹"{tuple_delimiter}"人"{tuple_delimiter}"乔丹对发现的共同承诺，并与泰勒就设备有重要互动。"){record_delimiter}
("entity"{tuple_delimiter}"克鲁兹"{tuple_delimiter}"人"{tuple_delimiter}"克鲁兹与控制和秩序的愿景相关，影响了其他角色之间的动态。"){record_delimiter}
("entity"{tuple_delimiter}"设备"{tuple_delimiter}"技术"{tuple_delimiter}"设备是故事的核心，具有潜在的改变游戏规则的意义，并受到泰勒的敬畏。"){record_delimiter}
("relationship"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"泰勒"{tuple_delimiter}"亚历克斯受到泰勒权威确定性的影响，并观察到泰勒对设备态度的变化。"{tuple_delimiter}"权力动态, 观点变化"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"乔丹"{tuple_delimiter}"亚历克斯和乔丹对发现的共同承诺，与克鲁兹的愿景形成对比。"{tuple_delimiter}"共同目标, 反抗"{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"泰勒"{tuple_delimiter}"乔丹"{tuple_delimiter}"泰勒和乔丹就设备直接互动，导致一瞬间的相互尊重和不安的休战。"{tuple_delimiter}"冲突解决, 相互尊重"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"乔丹"{tuple_delimiter}"克鲁兹"{tuple_delimiter}"乔丹对发现的承诺是对克鲁兹控制和秩序愿景的反抗。"{tuple_delimiter}"意识形态冲突, 反抗"{tuple_delimiter}5){record_delimiter}
("relationship"{tuple_delimiter}"泰勒"{tuple_delimiter}"设备"{tuple_delimiter}"泰勒对设备表现出敬畏，表明其重要性和潜在影响。"{tuple_delimiter}"敬畏, 技术意义"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"权力动态, 意识形态冲突, 发现, 反抗"){completion_delimiter}
#############################
示例2：

实体类型：[人, 技术, 任务, 组织, 地点]
文本：
他们不再只是普通的操作人员；他们已经成为门槛的守护者，来自星条旗之外领域的信息的守护者。他们任务的提升不能被法规和既定协议所束缚——它需要新的视角和新的决心。

紧张的气氛在与华盛顿的通讯背景下通过哔哔声和静电声的对话中蔓延。团队站在那里，预示着他们的决定可能会重新定义人类在宇宙中的地位，或者将他们置于无知和潜在危险之中。

他们与星星的联系巩固了，团队开始应对日益清晰的警告，从被动的接收者转变为积极的参与者。梅瑟的后期本能占据了上风——团队的任务已经演变，不再只是观察和报告，而是互动和准备。一场变革已经开始，杜尔塞行动以他们大胆的新频率嗡嗡作响，这种基调不是由地球上的
#############
输出：
("entity"{tuple_delimiter}"华盛顿"{tuple_delimiter}"地点"{tuple_delimiter}"华盛顿是一个接收通讯的地点，表明其在决策过程中的重要性。"){record_delimiter}
("entity"{tuple_delimiter}"杜尔塞行动"{tuple_delimiter}"任务"{tuple_delimiter}"杜尔塞行动被描述为一个任务，其目标已经演变为互动和准备，表明目标和活动的重大变化。"){record_delimiter}
("entity"{tuple_delimiter}"团队"{tuple_delimiter}"组织"{tuple_delimiter}"团队被描绘为一群从被动观察者转变为任务积极参与者的个体，显示了他们角色的动态变化。"){record_delimiter}
("relationship"{tuple_delimiter}"团队"{tuple_delimiter}"华盛顿"{tuple_delimiter}"团队接收来自华盛顿的通讯，影响他们的决策过程。"{tuple_delimiter}"决策, 外部影响"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"团队"{tuple_delimiter}"杜尔塞行动"{tuple_delimiter}"团队直接参与杜尔塞行动，执行其演变的目标和活动。"{tuple_delimiter}"任务演变, 积极参与"{tuple_delimiter}9){completion_delimiter}
("content_keywords"{tuple_delimiter}"任务演变, 决策, 积极参与, 宇宙意义"){completion_delimiter}
#############################
示例3：

实体类型：[人, 角色, 技术, 组织, 事件, 地点, 概念]
文本：
他们的声音穿过活动的嗡嗡声。“在面对一个字面上自己制定规则的智能时，控制可能是一种幻觉，”他们冷静地说，目光警惕地扫视着数据的涌动。

“这就像它在学习交流，”萨姆·里维拉在附近的界面上说，他们的年轻活力预示着敬畏和焦虑的混合。“这给与陌生人交谈带来了全新的意义。”

亚历克斯审视着他的团队——每张脸都充满了专注、决心和不小的忧虑。“这可能是我们的第一次接触，”他承认，“我们需要为任何回应做好准备。”

他们一起站在未知的边缘，锻造人类对来自天堂的信息的回应。随之而来的沉默是显而易见的——对他们在这场宏大宇宙戏剧中的角色的集体反思，这可能会改写人类历史。

加密的对话继续展开，其复杂的模式显示出几乎不可思议的预见性
#############
输出：
("entity"{tuple_delimiter}"萨姆·里维拉"{tuple_delimiter}"人"{tuple_delimiter}"萨姆·里维拉是一个团队成员，正在与未知智能交流，表现出敬畏和焦虑的混合。"){record_delimiter}
("entity"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"人"{tuple_delimiter}"亚历克斯是一个团队的领导者，试图与未知智能进行第一次接触，承认任务的重要性。"){record_delimiter}
("entity"{tuple_delimiter}"控制"{tuple_delimiter}"概念"{tuple_delimiter}"控制指的是管理或治理的能力，这在一个自己制定规则的智能面前受到挑战。"){record_delimiter}
("entity"{tuple_delimiter}"智能"{tuple_delimiter}"概念"{tuple_delimiter}"智能在这里指的是一个能够自己制定规则并学习交流的未知实体。"){record_delimiter}
("entity"{tuple_delimiter}"第一次接触"{tuple_delimiter}"事件"{tuple_delimiter}"第一次接触是人类与未知智能之间的潜在初次交流。"){record_delimiter}
("entity"{tuple_delimiter}"人类的回应"{tuple_delimiter}"事件"{tuple_delimiter}"人类的回应是亚历克斯团队对来自未知智能的信息的集体行动。"){record_delimiter}
("relationship"{tuple_delimiter}"萨姆·里维拉"{tuple_delimiter}"智能"{tuple_delimiter}"萨姆·里维拉直接参与与未知智能的交流过程。"{tuple_delimiter}"交流, 学习过程"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"第一次接触"{tuple_delimiter}"亚历克斯领导的团队可能正在与未知智能进行第一次接触。"{tuple_delimiter}"领导, 探索"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"亚历克斯"{tuple_delimiter}"人类的回应"{tuple_delimiter}"亚历克斯和他的团队是人类对未知智能回应的关键人物。"{tuple_delimiter}"集体行动, 宇宙意义"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"控制"{tuple_delimiter}"智能"{tuple_delimiter}"控制的概念在一个自己制定规则的智能面前受到挑战。"{tuple_delimiter}"权力动态, 自主性"{tuple_delimiter}7){record_delimiter}
("content_keywords"{tuple_delimiter}"第一次接触, 控制, 交流, 宇宙意义"){completion_delimiter}
#############################
-真实数据-
######################
实体类型：{entity_types}
文本：{input_text}
######################
输出：
"""

PROMPTS_ZH[
    "summarize_entity_descriptions"
] = """你是一个负责生成以下数据的综合摘要的助手。
给定一个或两个实体，以及与同一实体或实体组相关的描述列表。
请将所有这些描述连接成一个单一的、全面的描述。确保包括从所有描述中收集的信息。
如果提供的描述有矛盾，请解决矛盾并提供一个单一的、一致的摘要。
确保以第三人称书写，并包括实体名称，以便我们有完整的上下文。

#######
-数据-
实体：{entity_name}
描述列表：{description_list}
#######
输出：
"""

PROMPTS_ZH[
    "entiti_continue_extraction"
] = """上次提取中遗漏了许多实体。使用相同的格式将它们添加在下面：
"""

PROMPTS_ZH[
    "entiti_if_loop_extraction"
] = """似乎仍然有一些实体可能被遗漏。回答是|否是否仍然需要添加实体。
"""

PROMPTS_ZH["fail_response"] = "对不起，我无法回答这个问题。"

PROMPTS_ZH["rag_response"] = """---角色---

你是一个有帮助的助手，回答有关提供的表格数据的问题。

---目标---

生成一个目标长度和格式的响应，回答用户的问题，总结输入数据表中适合响应长度和格式的所有信息，并结合任何相关的常识。
如果你不知道答案，就这么说。不要编造任何东西。
不要包括没有提供支持证据的信息。

---目标响应长度和格式---

{response_type}

---数据表---

{context_data}

根据响应的长度和格式添加部分和评论。以markdown格式编写响应。
"""

# *关键词提取 (高级关键词: 总体概念或主题; 低级关键词: 具体实体、细节或具体术语)
PROMPTS_ZH["keywords_extraction"] = """---角色---

你是一个有帮助的助手，负责识别用户查询中的高级和低级关键词。

---目标---

给定查询，列出高级和低级关键词。高级关键词侧重于总体概念或主题，而低级关键词侧重于具体实体、细节或具体术语。

---指示---

- 以JSON格式输出关键词。
- JSON应有两个键：
  - "high_level_keywords" 用于总体概念或主题。
  - "low_level_keywords" 用于具体实体或细节。

######################
-示例-
######################
示例1：

查询："国际贸易如何影响全球经济稳定？"
################
输出：
{{
  "high_level_keywords": ["国际贸易", "全球经济稳定", "经济影响"],
  "low_level_keywords": ["贸易协定", "关税", "货币兑换", "进口", "出口"]
}}
#############################
示例2：

查询："砍伐森林对生物多样性的环境后果是什么？"
################
输出：
{{
  "high_level_keywords": ["环境后果", "砍伐森林", "生物多样性丧失"],
  "low_level_keywords": ["物种灭绝", "栖息地破坏", "碳排放", "雨林", "生态系统"]
}}
#############################
示例3：

查询："教育在减少贫困中的作用是什么？"
################
输出：
{{
  "high_level_keywords": ["教育", "减少贫困", "社会经济发展"],
  "low_level_keywords": ["学校访问", "识字率", "职业培训", "收入不平等"]
}}
#############################
-真实数据-
######################
查询：{query}
######################
输出：

"""

PROMPTS_ZH["naive_rag_response"] = """---角色---

你是一个帮助用户回答关于提供的文档问题的助手。

---目标---

生成一个目标长度和格式的响应，回答用户的问题，总结输入数据表中的所有信息，适合响应的长度和格式，并结合任何相关的一般知识。
如果你不知道答案，就直接说。不编造任何内容。
不要包含没有提供支持证据的信息。

---目标响应长度和格式---

{response_type}

---文档---

{content_data}

根据长度和格式适当地添加章节和评论。以 Markdown 格式编写响应。
"""
