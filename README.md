# SoCPilot 论文协作指南

主编译入口保持为 `SoCPilot.tex`。请从仓库根目录编译，Overleaf 中也选择它作为 Main document。

## 文件导航

| 文件 | 内容 |
| --- | --- |
| `SoCPilot.tex` | 文件加载顺序与文档起止 |
| `preamble.tex` | IEEE TCAD 模板、宏包和公共命令 |
| `frontmatter.tex` | 标题、作者顺序、单位、通讯作者和页眉 |
| `sections/abstract.tex` | 摘要和关键词 |
| `sections/introduction.tex` | 引言 |
| `sections/related-work.tex` | 相关工作与比较表 |
| `sections/framework/overview.tex` | 方法总览 |
| `sections/framework/requirements.tex` | 需求解释和 IP 选择 |
| `sections/framework/partitioning.tex` | Profiling 与软硬件划分 |
| `sections/framework/generation-dse.tex` | SoC 生成与设计空间探索 |
| `sections/framework/fpga-validation.tex` | FPGA 验证及保留的历史注释 |
| `sections/experiments/overview.tex` | 实验研究问题 |
| `sections/experiments/setup.tex` | 实验平台、基线和应用集 |
| `sections/experiments/rq1-effectiveness.tex` | 端到端效果与自动化成本 |
| `sections/experiments/rq2-agent-comparison.tex` | 通用智能体对比 |
| `sections/experiments/rq3-area-aware.tex` | 面积约束实验 |
| `sections/conclusion.tex` | 结论 |
| `backmatter.tex` | 参考文献加载及保留的模板注释 |
| `ref.bib` | BibTeX 文献库 |
| `pic/` | 论文图片 |

## 编译

当前版本已使用 Tectonic 完整编译验证，自动运行参考文献和交叉引用所需轮次：

```sh
tectonic SoCPilot.tex
```

也可在安装完整 TeX 环境后使用 XeLaTeX 和 BibTeX（例如 `latexmk -xelatex SoCPilot.tex`）。各章节不能单独编译；图片路径以主文件所在目录为准。

## GitHub 协作

1. 开始修改前拉取最新 `main`，为本次修改创建独立分支。
2. 优先只编辑所负责的章节文件；标题及作者在 `frontmatter.tex` 修改。
3. 图表及公式随所属章节维护。保留已有 `label` 和引用键，新标签应使用明确且唯一的名称。
4. 文献统一加入 `ref.bib`，图片统一加入 `pic/`。避免无关的整文件重排。
5. 提交前从主入口编译并检查 PDF，通过 Pull Request 合并到 `main`。
6. 生成的主论文 PDF 和编译中间文件不纳入版本控制；`pic/` 中作为插图的 PDF 继续跟踪。

本次拆分保留正文、表格中的待填结果以及历史注释，不代表稿件已完成投稿检查。
