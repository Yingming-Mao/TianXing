# TianXing（天行）

[English](README.md) | 中文

自动化论文审稿、改进与修订工具，基于 [Claude Code](https://claude.ai/claude-code) 构建。安装一次，即可在所有论文项目中使用。

### 两种模式，覆盖论文全生命周期

| | **Review**（`/review-loop`） | **Revise**（`tianxing revise`） |
|---|---|---|
| 场景 | 投稿前自我打磨 | 收到审稿意见后改稿 |
| 方式 | 单次 Claude Code 会话 | Python 编排器 + Claude 作为 worker |
| 实验 | 不跑新实验 | 跑新实验（后台、可恢复） |
| 时长 | 分钟级 | 小时到天级 |
| 安全 | Git checkpoint + 回滚 | Claim 门禁写回 + 人工确认 |

```
写初稿 → review-loop（打磨到能投）→ 投稿 → 收到审稿意见 → revise（改稿）→ 再投
```

### 核心亮点

- **按目标期刊校准评审** — 评分标准自动适配你的目标期刊/会议（从网上抓取真实审稿指南）。支持 ML 会议、OR 期刊、能源/电力系统期刊等。
- **重实质轻润色** — 技术严谨性和创新性占总分权重 45%，光改文字润色拉不动分数。
- **实验感知** — 自动构建论文↔代码↔测试↔结果的知识图谱。发现某个表格有问题，能直接追溯到生成它的代码。
- **安全兜底** — 每轮修改前自动 git checkpoint，失败自动回滚，修改按风险分级执行。修订写回仅限已验证的 claim。

## 安装

```bash
git clone https://github.com/Yingming-Mao/TianXing.git
cd TianXing
pip install -e .
```

需要 Python >= 3.8 和已安装的 [Claude Code](https://claude.ai/claude-code)。

## 快速开始：Review 循环（投稿前）

### 1. 初始化论文项目

```bash
cd /path/to/your-paper-project
bash /path/to/TianXing/scripts/setup_project.sh
```

### 2. 配置

编辑论文项目中的 `config.yaml`：

```yaml
review:
  venue: "NeurIPS 2026"        # 目标期刊/会议 — reviewer 会按其标准校准评分
  # venue: "Applied Energy"    # 能源/电力系统
  # venue: "Operations Research"  # 运筹学/管理科学
  # venue: "IEEE TSG"          # 智能电网
  # 留空则 agent 自动从论文内容推断最匹配的期刊

compile:
  main_file: "paper/main.tex"

project:
  env: "myenv"                # conda 环境名（或路径，或 venv python 路径；留空用当前环境）
```

### 3. 运行

在论文项目中打开 Claude Code：

```
/review-loop
```

## 快速开始：Revision 修订（审稿后）

### 1. 初始化修订目录

```bash
cd /path/to/your-paper-project
tianxing revise-setup
```

会生成两个目录：

```
tianxing_revision/              ← 你来填
  REVISION_SPEC.md              ← 审稿意见 + 修订目标（主文件）
  SUCCESS_CRITERIA.md           ← 什么算"改完了"
  CLAIMS_TO_PRESERVE.md        ← 必须保住的核心 claim
  EXPERIMENT_RULES.yaml         ← 实验规则（先 smoke、full run 要确认）
  EXECUTION_ENV.yaml            ← 运行环境（conda/GPU/代理）
  OPERATOR_NOTES.md             ← 随时可改的运行时备注
  MANUAL_OVERRIDES.yaml         ← 跳过阶段、强制重跑等覆盖项

revision/                       ← 系统管理，不用手动改
  state.json                    ← 阶段状态机
  knowledge_state.json          ← 系统对论文的理解
  master_plan.json              ← 活跃的修订计划
  task_registry.json            ← 任务跟踪
  result_registry.json          ← 实验运行跟踪
  claim_registry.json           ← 论文 claim 验证状态
  ...
```

### 2. 填写修订说明

编辑 `tianxing_revision/REVISION_SPEC.md`，把审稿意见和目标写进去：

```markdown
# Revision Specification

## Reviewer Comments

### Reviewer 1
- 缺少大规模实验（1000 EVs）
- Table 1 的 baseline 不公平

### Reviewer 2
- 叙事不清晰，建议重构 introduction
- 需要补充 ablation study

## Revision Goals
- 补 1000-EV 实验，强化 scalability claim
- 重写 intro，改用 service-envelope 叙事
- 加 ablation，拆分各组件贡献

## New Story Arc
从 "我们提出了一个方法" 改为 "service-envelope 是一种可扩展的 EV 充电框架"
```

编辑 `tianxing_revision/CLAIMS_TO_PRESERVE.md`，列出必须保住的核心结论：

```markdown
## Core Claims
1. Service envelope 降低充电成本 15%（Table 1）
2. 方法在 50 次迭代内收敛（Figure 3）
```

检查 `tianxing_revision/EXECUTION_ENV.yaml`（conda 环境名、是否需要 GPU）。

### 3. 运行

**交互模式（推荐首次使用）** — 在 Claude Code 中逐步执行：

```
/revise-loop
```

**自动模式** — Python 编排器驱动完整循环：

```bash
tianxing revise
```

**随时查看状态：**

```bash
tianxing revise-state --action get
```

**系统请求确认时**（如跑 full experiment 前）：

```bash
tianxing revise-state --action confirm
```

### 修订流程原理

系统运行一个 observe–reason–act 循环：

```
INIT → AUDIT → PLAN → IMPLEMENT → SMOKE_TEST → [人工确认] → FULL_RUN → VERIFY → WRITEBACK → FINALIZE
```

- **Python 编排器**管运行事实：状态机、实验调度、监控
- **Claude Code**管语义判断：审计论文、规划改动、写代码/文本、验证结果
- **文件系统**是共享协议：所有状态在 `revision/*.json`，不依赖 stdout

关键安全机制：
- Full experiment 需要人工确认才能开跑
- 只有**已验证**的 claim 才会被写回论文
- Claude worker 按角色最小授权（auditor 不能改代码，verifier 不能改论文）
- 所有状态持久化到磁盘 — 中断后随时恢复

## 工具列表

所有工具输出结构化 JSON，通过 `tianxing <命令>` 或 `python -m tianxing.<模块名>` 调用。

| 工具 | 用途 |
|------|------|
| `checkpoint_repo` | 修改前创建 git 检查点（tag） |
| `rollback_repo` | 回滚到之前的检查点 |
| `compile_paper` | 编译 LaTeX 并报告错误/警告 |
| `run_tests` | 运行项目测试（仅在代码被修改且测试已启用时运行） |
| `record_round` | 保存审稿产物（review、plan、changes） |
| `update_status` | 跟踪审稿进度和分数 |
| `notify_status` | 记录通知日志 |
| `collect_metrics` | 扫描 results 目录收集指标 |
| `experiment_map` | 自动发现和查询 论文↔代码↔测试↔结果 的双向映射 |
| `revise-setup` | 初始化修订目录结构和模板 |
| `revise` | 运行修订编排循环 |
| `revise-state` | 查看/管理修订状态（get、confirm、reset） |

## 仓库结构

```
tianxing/                Python 包（可 pip 安装）
  revision/             修订编排器模块
commands/               Claude Code slash command（review-loop、revise-loop）
prompts/                Agent prompt 模板（reviewer、planner、rewriter、6 个修订角色）
skills/                 详细的 Skill prompt
templates/              用户项目模板文件（AGENT.md、.gitignore）
scripts/                项目初始化脚本
tests/                  测试套件（73 个测试）
```

## 实验知识图谱（Experiment Map）

TianXing 会自动构建并维护 `experiment_map.json`，双向映射：

- **论文章节**（section、table、figure）↔ **代码文件**
- **代码文件** ↔ **测试命令**
- **代码文件** ↔ **结果文件**（数据、图表）

```bash
tianxing map --action discover   # 扫描并生成
tianxing map --action query --id "tab:results"   # 查找关联代码/测试
tianxing map --action query --path "code/train.py"  # 查找关联测试/论文章节
```

## 配置说明

完整配置见 `config.example.yaml`，关键设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `review.venue` | 目标期刊/会议（如 `"NeurIPS 2026"`、`"Applied Energy"`、`"IEEE TSG"`），未设置时自动推断 | 空 |
| `project.env` | 实验运行环境：conda 环境名、conda 路径、或 venv 的 python 路径 | 当前环境 |
| `review.max_rounds` | 最大改进轮数 | 3 |
| `review.target_score` | 目标分数（达到即停） | 7.0 |
| `compile.main_file` | LaTeX 主文件路径 | `paper/main.tex` |
| `tests.enabled` | 启用测试 | `false` |

## License

MIT
