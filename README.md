# turing-kg

《认知计算与知识工程》课程作业 —— “图灵主题”知识图谱项目。已实现功能：
- [x] 实体抽取
- [x] 实体消歧

## 1. 项目结构

```text
.
├─ README.md
├─ requirements.txt
├─ main.py
├─ config.py
├─ data/
│  ├─ raw/                 # 示例原始文本
│  ├─ kb/                  # 种子知识库
│  ├─ intermediate/        # mentions / linked_entities 等中间结果
│  └─ output/              # 最终导出结果与统计报告
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
│  └─ run_pipeline.py
└─ tests/
   └─ test_basic.py
```

## 2. 运行方式

统一入口：

```bash
python main.py --mode extraction
python main.py --mode disambiguation
python main.py --mode pipeline
```

## 3. 示例输出说明

运行完整流水线后，会生成以下结果：

- `data/intermediate/mentions.jsonl`
  - 每行一个 Mention，包含 `text_id`、`sentence_id`、`mention`、`start`、`end`、`entity_type`、`context`、`method`
- `data/intermediate/linked_entities.jsonl`
  - 每行一个消歧结果，包含候选得分和最终链接结果
- `data/output/entities.json`
  - 本轮文本中成功链接到的唯一实体集合
- `data/output/triples.csv`
  - 当前阶段仅生成表头，后续关系抽取阶段可以直接接入
- `data/output/report.json`
  - 包括文本数、句子数、mention 数、消歧成功数、NIL 数、类型统计等

## 4. 当前阶段的局限性

- 实体抽取主要依赖种子词典与少量正则，覆盖面有限
- 未使用统计学习或深度学习模型，泛化能力较弱
- 实体消歧只使用简单打分函数，复杂上下文理解能力有限
- 当前尚未构建实体间关系，因此图谱仍是“实体层”的最小版本

## 5. 后续可扩展方向

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

## 6. 当前实现的技术路线

- 预处理：清洗空白、按中英文标点分句
- 抽取：词典匹配 + 正则规则
- 消歧：候选生成 + 加权打分

打分公式为：

```text
score = 0.5 * alias_score + 0.3 * context_keyword_score + 0.2 * type_prior_score
```

其中：

- `alias_score`：mention 与实体别名的匹配程度
- `context_keyword_score`：上下文与实体关键词的重合程度
- `type_prior_score`：抽取类型与候选实体类型的一致程度
