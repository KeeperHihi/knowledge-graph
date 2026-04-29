# turing-kg

《认知计算与知识工程》课程作业 —— “图灵主题”知识图谱项目。已实现功能：
- [x] 实体抽取
- [x] 实体消歧
- [x] 事件抽取
- [x] 关系抽取
- [x] 图谱可视化
- [x] 人物视角切换
- [x] 规则解释案例

这个项目只用了词典匹配、正则规则、简单打分和静态网页展示，没有调用大模型，也没有使用预训练模型。

## 0. 先说清楚这份作业是怎么做的

- 原始数据放在 `data/raw/`，每条文本都在 `source_manifest.json` 里记录了来源
- 中间过程会输出到 `data/intermediate/`，可以直接看到 mention 和消歧结果
- 最终图谱和统计结果放在 `data/output/`
- 本项目重点是“过程清楚、可以解释”，不是追求复杂模型

## 1. 项目结构

```text
.
├─ README.md
├─ requirements.txt
├─ main.py
├─ config.py
├─ data/
│  ├─ raw/                 # 示例原始文本
│  │  └─ source_manifest.json
│  ├─ kb/                  # 种子知识库
│  ├─ intermediate/        # mentions / linked_entities 等中间结果
│  └─ output/              # 最终导出结果与统计报告
├─ docs/
│  ├─ student_method.md    # 学生口吻的方法说明
│  └─ demo_walkthrough.md  # 答辩演示顺序
├─ web/                    # 本地可视化网页
├─ src/
│  ├─ utils/               # IO 与文本工具
│  ├─ schema/              # Mention / Entity / Triple 等数据结构
│  ├─ preprocess/          # 清洗与分句
│  ├─ extraction/          # 实体抽取
│  ├─ disambiguation/      # 实体消歧
│  ├─ kg/                  # 流水线与导出
│  └─ evaluation/          # 统计与报告
├─ scripts/
│  ├─ run_extraction.py
│  ├─ run_disambiguation.py
│  ├─ run_demo.py
│  ├─ run_pipeline.py
│  └─ run_visualization.py
└─ tests/
   ├─ test_basic.py
   ├─ test_graph_features.py
   └─ test_reporting.py
```

## 2. 运行方式

本项目默认只依赖 Python 标准库，因此不需要额外安装第三方包。

先在项目根目录执行：

```bash
python3 -m unittest discover -s tests -v
```

如果测试通过，再运行主流程：

统一入口：

```bash
python3 main.py --mode extraction
python3 main.py --mode disambiguation
python3 main.py --mode pipeline
```

启动图谱网页：

```bash
python3 scripts/run_visualization.py --port 8000
```

然后访问：

```text
http://127.0.0.1:8000/web/index.html
```

如果想按“中间结果展示”的顺序演示，推荐实际答辩时按下面顺序操作：

```bash
python3 main.py --mode extraction
python3 main.py --mode disambiguation
python3 main.py --mode pipeline
python3 scripts/run_visualization.py --port 8000
```

如果想一边跑完整流程一边拿到演示提示，可以直接执行：

```bash
python3 scripts/run_demo.py --prepare-only
```

如果希望它同时启动网页：

```bash
python3 scripts/run_demo.py --port 8000
```

## 3. 当前已经验证通过的结果

我在本地重新跑过一次，当前这份仓库可以直接得到下面这些结果：

- 单元测试：`python3 -m unittest discover -s tests -v`，`10` 个测试全部通过
- 完整流程：`python3 main.py --mode pipeline`
- 当前统计结果：`12` 份原始文本、`32` 个句子、`91` 个 mention、`83` 个成功链接、`28` 条关系、`22` 个事件
- 关键检查已经通过：
  - `PublicationEvent` 已经能抽到
  - `published` 关系已经能生成
  - 不再出现 `Alan Turing studied_at Cambridge` 这种把城市当学校的关系
  - 网页已经支持 `Alan Turing / Joan Clarke / Alonzo Church / Max Newman` 等人物视角切换
  - 网页已经支持实体消歧打分案例和“事件 -> 关系”解释案例
  - 本地网页可以通过 `python3 scripts/run_visualization.py --port 8000` 正常启动

## 4. 答辩推荐顺序

如果按老师现场查看项目的习惯来演示，推荐下面这个顺序：

1. 先打开 `data/raw/` 和 `data/raw/source_manifest.json`
   - 说明原始文本来自公开资料整理，不是直接下载现成知识图谱
2. 再看 `data/intermediate/mentions.jsonl` 和 `data/intermediate/linked_entities.jsonl`
   - 说明实体抽取和实体消歧的中间结果
3. 再看 `data/output/report.json`、`data/output/traceability.json`
   - 说明统计摘要、关系数量、事件数量和来源回溯
4. 最后打开网页 `http://127.0.0.1:8000/web/index.html`
   - 建议先看 `Cambridge` 消歧案例和论文发表案例，再切人物视角里的 `Alan Turing / Joan Clarke / Alonzo Church / Max Newman`

如果现场时间只剩 2 分钟，优先展示这 4 个入口：

- `data/raw/source_manifest.json`
- `data/output/report.json`
- `data/output/traceability.json`
- `http://127.0.0.1:8000/web/index.html`

配套的讲解文档：

- `docs/student_method.md`
- `docs/demo_walkthrough.md`

## 5. 示例输出说明

运行完整流水线后，会生成以下结果：

- `data/intermediate/mentions.jsonl`
  - 每行一个 Mention，包含 `text_id`、`sentence_id`、`mention`、`start`、`end`、`entity_type`、`context`、`method`
- `data/intermediate/linked_entities.jsonl`
  - 每行一个消歧结果，包含候选得分和最终链接结果
- `data/output/events.json`
  - 事件抽取结果，保留 `event_type`、`participants`、`trigger`、`evidence`，同时附带 `source_title/source_url`
- `data/output/relations.csv`
  - 关系抽取结果，包含 `head / relation / tail / evidence`
- `data/output/entities.json`
  - 本轮文本中成功链接到的唯一实体集合
- `data/output/triples.csv`
  - 简化版三元组结果，便于展示和导入
- `data/output/graph.json`
  - 网页可视化直接读取的节点边数据，节点、边、事件都尽量保留原文编号和来源信息
- `data/output/explainability.json`
  - 给网页“规则解释”区域使用，里面放了消歧打分案例和事件生成关系案例
- `data/output/traceability.json`
  - 每个 raw 文本对应的来源、抽取统计、示例关系和示例事件，便于答辩时回溯
- `data/output/report.json`
  - 包括文本数、句子数、mention 数、消歧成功数、NIL 数、关系数、事件数、类型统计和分文本统计
- `docs/student_method.md`
  - 用学生口吻说明为什么选择规则法、事件层、可视化展示，便于答辩讲解

## 6. 当前阶段的局限性

- 实体抽取主要依赖种子词典与少量正则，覆盖面有限
- 未使用统计学习或深度学习模型，泛化能力较弱
- 实体消歧只使用简单打分函数，复杂上下文理解能力有限
- 规则法覆盖面仍然有限，遇到代词、省略和复杂长句时容易漏抽
- 目前更适合“图灵主题”的小规模课程作业，不追求跨领域泛化

## 7. 后续可扩展方向

后续可以在保持结构稳定的前提下继续扩展：

1. 关系抽取
   - 从句子中识别“人物-机构”“人物-作品”“人物-地点”等关系
2. 知识融合
   - 合并重复实体、处理冲突属性、引入外部百科数据
3. 图数据库存储
   - 导入 Neo4j 等图数据库进行可视化和查询
4. 问答与检索
   - 面向图灵主题构建简单的知识问答系统
5. 更丰富的评估
   - 增加人工标注样本，计算 precision / recall / F1

## 8. 当前实现的技术路线

- 预处理：清洗空白、按中英文标点分句
- 抽取：词典匹配 + 正则规则
- 消歧：候选生成 + 加权打分
- 事件抽取：触发词 + 实体类型组合
- 关系抽取：事件驱动 + 少量句式规则
- 可视化：静态网页直接读取 `graph.json`

打分公式为：

```text
score = 0.5 * alias_score + 0.3 * context_keyword_score + 0.2 * type_prior_score
```

其中：

- `alias_score`：mention 与实体别名的匹配程度
- `context_keyword_score`：上下文与实体关键词的重合程度
- `type_prior_score`：抽取类型与候选实体类型的一致程度

## 9. 数据来源说明

- 原始文本都放在 `data/raw/`，不是直接写死结构化图谱
- 每个 raw 文本的来源记录在 `data/raw/source_manifest.json`
- 主要来源包括：
  - The Turing Digital Archive
  - The University of Manchester
  - Bletchley Park
  - National Physical Laboratory
  - Princeton University
