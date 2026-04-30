# 图灵知识图谱构建实验报告

## 一、实验目标与方法原则

本实验围绕 Alan Turing（阿兰·图灵）构建一个多主体知识图谱。课程要求强调“从原始文本抽取知识”，因此项目没有直接手写结构化三元组，也没有调用大模型或预训练模型，而是使用词典匹配、正则表达式、上下文打分和事件规则完成整条流程。

作为本科课程作业，我对项目的定位是：算法不追求复杂，但每一步都要能解释、能复现、能在答辩时指向具体文件。最终图谱不只表现图灵本人，还加入 Joan Clarke、Alonzo Church、Max Newman、John von Neumann 等相关人物，以及 Bletchley Park、Princeton University、University of Manchester、Bombe、Manchester Mark I 等机构和设备，尽量体现“图灵相关知识网络”而不是单个人物简介。

## 二、数据来源与预处理

原始数据放在 `data/raw/`，共有 16 份短文本，来源信息记录在 `data/raw/source_manifest.json`。这些文本主要根据公开资料整理，包括 The Turing Digital Archive、Bletchley Park、Princeton University、University of Manchester、NPL 等资料页。为了让课堂演示更完整，我也补充了少量 demo 文本，例如 Bombe 和 Manchester Mark I 的设备关系；这些数据在 manifest 中明确标注为课堂补充，不冒充真实网页出处。

数据整理时，我没有直接复制网页全文，而是把资料整理成适合规则抽取的短句。这样做有两个原因：第一，后续每个 mention、事件和关系都能回到原始句子；第二，规则法对句子表达比较敏感，短句更方便观察规则是否漏抽。对于一些代词较多的句子，我会改成显式主语，例如把“他提出……”改成“Alan Turing 提出……”。这不是为了掩盖规则不足，而是因为本项目没有实现复杂共指消解，必须把数据准备阶段也纳入可解释流程。

预处理阶段会读取 `data/raw/` 中的文本，进行基础清洗和分句。完整链路如下：

```text
data/raw/*.txt
  -> 预处理与分句
  -> data/intermediate/mentions.jsonl
  -> data/intermediate/linked_entities.jsonl
  -> data/output/events.json
  -> data/output/relations.csv
  -> data/output/entities.json
  -> data/output/graph.json
  -> web/index.html 可视化展示
```

这条链路是本项目最重要的部分，因为它说明最终图谱来自 raw text 的逐步抽取，而不是直接生成好的结构化数据。

## 三、实体抽取流程

实体抽取的任务是从分句后的 raw 文本中识别实体 mention。本阶段可以概括为：

- 输入：预处理后的句子。
- 方法：词典别名匹配 + 时间正则匹配。
- 输出：`data/intermediate/mentions.jsonl`。
- 可解释依据：每个 mention 都保留 `text_id`、`sentence_id`、表面词、起止位置、实体类型、上下文和抽取方法。

我采用了两类规则：

1. 对人物、机构、地点、设备、概念、作品等实体，使用 `data/kb/seed_entities.json` 中的种子词典和别名进行匹配。
2. 对时间等格式比较明显的内容，使用正则表达式识别。

例如，句子中出现 `Princeton University` 时，它会被词典规则识别为 Organization；出现 `1936` 这类年份时，会由时间规则识别为 Time。这样设计的优点是结果稳定、解释简单：可以直接说明“这个实体是因为命中了哪个词典别名或哪个正则规则”。缺点也很明确，词典之外的新实体不会自动识别，需要后续人工补充。

实体抽取页签展示的就是这一阶段的典型案例：在原始句子中高亮 mention，并标出每个 mention 使用的是词典匹配还是正则匹配。

## 四、实体消歧流程

实体抽取只解决“句子里出现了什么词”，还没有解决“这个词到底指哪个实体”。例如 `Cambridge` 可能指 Cambridge 这座城市，也可能指 University of Cambridge 相关机构。本阶段可以概括为：

- 输入：`data/intermediate/mentions.jsonl`。
- 方法：候选实体生成 + 加权打分。
- 输出：`data/intermediate/linked_entities.jsonl`。
- 可解释依据：保留候选实体、各项分数和最终选择结果。

我的消歧方法没有使用模型训练，而是给候选实体做简单打分。分数主要由三部分组成：

1. `alias_score`：mention 和候选实体名称、别名是否相近。
2. `context_keyword_score`：句子上下文是否命中候选实体的关键词。
3. `type_prior_score`：抽取阶段判断的实体类型是否和候选实体类型一致。

最后按照加权分数选择最高的候选实体。如果上下文中出现“学习、学院、数学”等词，`Cambridge` 更可能被连到 `University of Cambridge`；如果上下文强调“城市、英格兰东部”，则更可能连到 `Cambridge` 这个地点。这个过程虽然简单，但每个分数都能展示出来，比较适合课程答辩时说明“为什么选这个实体，而不是另一个候选”。

在网页的实体消歧页签中，我保留了 Cambridge 的候选打分案例。答辩中如果需要解释某个歧义词的判断依据，可以直接查看别名分、上下文关键词分、类型分和最终总分。

## 五、事件抽取流程

如果直接从句子生成三元组，解释时会比较跳跃。因此我在关系之前增加了事件层。本阶段可以概括为：

- 输入：已经完成消歧的实体 mention。
- 方法：事件触发词 + 参与实体类型规则。
- 输出：`data/output/events.json`。
- 可解释依据：事件记录保留触发词、参与实体、证据句和来源信息。

事件抽取主要依赖“触发词 + 参与实体类型”的规则。根据图灵主题，我设置了几类最常见、也最容易解释的事件：

- `EducationEvent`：学习、就读、接受教育等句子。
- `PublicationEvent`：发表论文或作品的句子。
- `ResearchEvent`：提出概念、研究机器、讨论测试等句子。
- `WarWorkEvent`：Bletchley Park、Enigma、Bombe 等战争密码工作相关句子。
- `EmploymentEvent`：在某机构工作、任职或参与项目的句子。
- `InfluenceEvent`：人物之间影响或启发关系的句子。

例如，原句“Alan Turing 在 1936 年发表 Computable Numbers，并提出 Turing Machine 概念”会被识别出 `PublicationEvent` 和 `ResearchEvent`。这样做的好处是，后面每一条关系都可以先回到一个事件，再回到原始文本。

我在实现时刻意没有扩展太多事件类型，因为过多类型会让规则变得难维护，也不符合本科课程作业的难度。当前这些事件已经足够覆盖图灵的求学、研究、战争工作、曼彻斯特阶段和相关人物网络。

## 六、关系抽取流程

关系抽取负责把事件和部分明显句式转换为三元组。本阶段可以概括为：

- 输入：已消歧实体和事件记录。
- 方法：事件类型到关系类型的规则映射，并补充少量句式规则。
- 输出：`data/output/relations.csv`，同时导出 `data/output/triples.csv`。
- 可解释依据：每条关系保留来源事件、证据句和原始文本编号。

核心思路是先判断事件类型，再根据参与实体角色生成三元组。例如：

```text
PublicationEvent
  -> author: Alan Turing
  -> work: Computable Numbers
  -> Alan Turing - published - Computable Numbers
```

目前保留的关系类型包括 `studied_at`、`worked_at`、`published`、`proposed`、`influenced_by`、`participated_in`、`used`、`located_in`。这些关系数量不算多，但能够覆盖本项目的主要知识：学习经历、研究成果、人物影响、战争密码工作、设备使用和机构地点。

本实验没有为了让图谱显得复杂而加入很多细碎关系，因为关系越多，解释成本越高，误抽风险也越大。现在的设计更适合展示“事件如何转成关系”：先给出证据句，再说明事件类型和参与实体，最后生成三元组。

## 七、知识图谱建立方式

最终图谱不是直接写出来的，而是由前面几个阶段的输出组合得到。`src/kg/pipeline.py` 中的完整顺序是：

1. 从 `data/raw/` 读取原始文本并分句。
2. 执行实体抽取，生成 `data/intermediate/mentions.jsonl`。
3. 执行实体消歧，生成 `data/intermediate/linked_entities.jsonl`。
4. 基于已消歧实体抽取事件，生成 `data/output/events.json`。
5. 基于事件和句式规则抽取关系，生成 `data/output/relations.csv`。
6. 汇总成功链接的唯一实体，生成 `data/output/entities.json`。
7. 根据实体和关系构建节点、边和事件信息，生成 `data/output/graph.json`。
8. 额外导出 `traceability.json` 和 `explainability.json`，用于说明来源追踪和网页案例。

`graph.json` 中的节点来自成功链接的实体，边来自关系抽取结果。每条边都会保留证据句、触发词、来源文本编号和来源标题。这样，在可视化界面点击某条关系或某个节点时，不只能看到图谱结果，还能回到“这条边为什么存在”。

可视化部分使用本地静态网页实现，运行端口后打开 `web/index.html`。网页分成五个页签：实体抽取、实体消歧、事件抽取、关系抽取、知识图谱。前四个页签分别展示一个典型过程案例，最后一个页签展示力导向图。知识图谱页支持点击节点查看直接连边和节点信息，也支持拖动节点调整局部布局；人物视角按钮可以突出 Alan Turing、Joan Clarke、Alonzo Church、Max Newman 等主体及其一跳邻居。

## 八、结果统计与人工核对

当前 `data/output/report.json` 中的统计结果为：

- 原始文本：16 份。
- 分句数量：47 句。
- 抽取 mention：134 个。
- 成功链接 mention：124 个。
- 唯一链接实体：28 个。
- 事件：33 个。
- 关系：44 条。

为了避免只看页面效果，我还做了一个小样本人工核对，结果保存在 `data/output/evaluation_summary.json`。目前实体消歧、关系抽取、事件抽取三个小样本都是 8/8 命中。这个评测集规模不大，不能说明系统完全没有错误，但它能证明核心展示案例不是随意写出来的，而是能被当前规则稳定复现。

在核对过程中也发现过规则漏例。例如 `Sherborne School` 的句子最初写成“接受中学教育”，没有命中原来的求学触发词；补充触发词后，相关 `EducationEvent` 和 `studied_at` 关系才能被抽取出来。这个过程让我认识到，规则系统需要通过人工样本持续检查，不能只凭一次运行结果判断效果。

## 九、局限性与改进方向

这个项目的主要局限来自规则法本身。实体抽取依赖种子词典，词典没有覆盖的新实体容易漏掉；事件和关系抽取依赖触发词，句子换一种表达方式也可能漏抽；代词和省略表达需要在数据整理阶段尽量改成显式主语，否则系统不会自动理解上下文。

我没有在本项目中加入复杂模型，是因为课程要求强调可解释性，也明确不允许调用大模型和预训练模型。站在本科课程作业的角度，我认为当前方案的重点不在“算法看起来高级”，而在完整走通了从 raw text 到知识图谱的链路，并且每一步都有中间结果可以检查。

后续如果继续完善，可以优先做三件事：补充更系统的触发词表，扩大人工核对样本，增加更多侧人物的文本。这样既能让图谱更充实，也不会破坏当前简单、可解释的实现方式。

## 十、实验总结

通过这次实验，我更清楚地理解了知识图谱不是只画一张关系图，而是由数据来源、实体识别、实体链接、事件组织、关系生成和可视化展示共同组成。本次实验的主要收获，是把每条边都和原始句子、中间事件、抽取规则联系起来。这样答辩时如果需要说明“这条关系从哪里来”，就可以沿着 `raw_data -> mentions -> linked_entities -> events -> relations -> graph` 的链路一步步解释，而不是只展示最后的图谱结果。
