# 答辩演示顺序

这个文档不是讲原理细节，而是我给自己准备的答辩顺序。真到现场的时候，如果一上来就点网页，老师可能会觉得“图是画出来了，但过程在哪”。所以我更想按“数据 -> 中间结果 -> 图谱 -> 页面”这个顺序来讲。

## 1. 先讲数据从哪来

先打开 `data/raw/` 和 `data/raw/source_manifest.json`。

我会先说两句话：

- 这些原始文本是我自己根据公开资料整理成的小片段，不是直接下载别人做好的知识图谱。
- 每个文本都记了来源链接，所以后面的关系和事件都能回溯到原文主题。

这里不用展开太久，主要是先把“数据来源清楚、不是直接编结构化结果”这件事说清楚。

## 2. 再讲中间结果

第二步我会打开：

- `data/intermediate/mentions.jsonl`
- `data/intermediate/linked_entities.jsonl`

这一步我想强调的是：我不是从原文直接跳到图谱，中间还有实体抽取和实体消歧。

如果老师追问，我会拿“剑桥”举例：

- 先抽到 mention
- 再根据上下文判断它更像城市还是大学

这个例子很好讲，也能体现这个项目不是只做表面展示。

## 3. 再讲事件和关系是怎么出来的

第三步我会打开：

- `data/output/events.json`
- `data/output/relations.csv`
- `data/output/report.json`
- `data/output/traceability.json`

这里我会重点说一句：我没有直接从句子里硬抽三元组，而是先抽事件，再从事件里生成关系。这样每条边都能回到事件和证据句。

我准备重点举这几个例子：

- `Alan Turing studied_at Princeton University`
- `Alan Turing worked_at Bletchley Park`
- `Alan Turing influenced_by Alonzo Church`

如果时间够，我会再补一句：`traceability.json` 是为了答辩时更方便，从某个原文片段直接看到它贡献了哪些事件和关系。

## 4. 最后打开网页

最后再运行网页服务，打开图谱页面。

推荐点击顺序：

1. 先看页面最上方的“构建过程”卡片
2. 再点“规则解释”里的 `Cambridge` 消歧案例
3. 接着点论文发表那张事件案例卡
4. 然后再切到“人物视角”里的 `Alan Turing`
5. 再切到 `Joan Clarke`
6. 再切到 `Alonzo Church` 或 `Max Newman`
7. 最后点左侧关系图里的 `Princeton University` 或 `Bletchley Park`
8. 任意一条 `studied_at` 或 `worked_at` 的边
9. 右侧任意一个事件卡片

我想让老师先看到的是：这不是直接画出来的图，而且它也不是黑箱。通过规则解释卡，我可以先说明“为什么这样判”，再通过人物视角切换说明“同一套规则怎样把不同人物放到同一张知识图里”。

原来的图谱点击顺序也还可以保留：

1. `Alan Turing`
2. `Princeton University`
3. `Bletchley Park`
4. 任意一条 `studied_at` 或 `worked_at` 的边
5. 右侧任意一个事件卡片

我想让老师看到的不是“页面很炫”，而是：

- 节点能看到它连到谁
- 边能看到证据句
- 详情里能看到原文编号和来源链接
- 右侧能看到统计摘要和来源回溯

## 5. 最后收个尾

最后我会自己主动承认局限：

- 这是规则法，不是通用模型，所以跨领域泛化一般
- 代词和复杂长句处理得还不够强
- 但是对课程作业来说，它的优点是过程清楚、结果可回溯、每一步都能解释

我觉得这样收尾比硬说“我的系统很强”更自然，也更像自己真的做过这个项目。
