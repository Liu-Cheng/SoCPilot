# SoCPilot 论文协作

主入口为 `SoCPilot.tex`，从仓库根目录编译；Overleaf 的 Main document 也设置为此文件。

| 文件 | 编辑内容 |
| --- | --- |
| `preamble.tex` | 模板、宏包、公共命令 |
| `frontmatter.tex` | 标题、作者顺序、单位、通讯作者、页眉 |
| `sections/abstract.tex` | 摘要与关键词 |
| `sections/introduction.tex` | Section I: Introduction |
| `sections/related-work.tex` | Section II: Related Work |
| `sections/framework.tex` | Section III: SoCPilot Framework |
| `sections/experiments.tex` | Section IV: Experiments |
| `sections/conclusion.tex` | Section V: Conclusion |
| `backmatter.tex` | 参考文献加载 |
| `ref.bib` | 文献条目 |
| `pic/` | 图片 |

## 编译

已使用 Tectonic 验证：

```sh
tectonic SoCPilot.tex
```

使用完整 TeX 环境也可运行 `latexmk -xelatex SoCPilot.tex`。章节文件不能单独编译，图片路径以主入口所在目录为准。

## 协作约定

- 编辑前拉取最新版本，尽量按章节分工，在独立分支修改后提交 Pull Request。
- 图表及其标签随所属章节维护，保持引用标签唯一，文献统一加入 `ref.bib`。
- 提交前编译主入口并检查 PDF，避免提交编译中间文件。
- Overleaf 同步时应保留完整的多文件结构，避免用旧单文件版本覆盖仓库。
- 本次拆分保留已有正文、数据及历史注释。

## 2026-10-31 实验结果更新

当前实验图表以 `data/experiment_results.json` 为入口。原始串口日志、每个应用的最终 DSE 参数和综合面积报告冻结在 `data/board_20261031/`，该 JSON 中记录了来源及 SHA-256。Nightvision 使用 `nightvision_ariane_new.DAT`，WAMI 应用对比使用 `wami_ibex.DAT` 的 3 mm² 点及其同配置 CPU-only 基线。

```sh
python scripts/draw_experiment_results.py
python scripts/draw_wami_tradeoff.py
python scripts/check_board_results.py
latexmk -pdf SoCPilot.tex
```

第二个脚本生成 Table VI、WAMI 配置表（Table VII）和 Fig. 9。Fig. 5 仅展示主计时对应的应用加速比；原配对计时表已移除。Fig. 9 仅选取 1.8、2.2、3、4、8、9、10 mm² 点；6、8 mm² 修正版时间来自 `trade_off_80_90.DAT`（文件名中的 90 不代表其内容是 9 mm²）。历史 Nightvision 扫描文件仍保留，但不参与当前 Fig. 9。

计时同时保留 preparation-excluded 和 full elapsed，不能将扣除准备时间后的结果称为完整端到端时间。表中综合面积标为 normalized synthesis area：同一 45 nm 等效口径下的单元面积，包含 SRAM 宏，排除 1000 KiB 应用 RAM，并非布线后芯片面积。完整来源报告保留原工艺与换算记录。原始日志均标记 `verification=unchecked`，不能据此宣称已完成原始浮点算法的全应用等价验证。

## Paper application display names

The manuscript uses `plate_roi` for license-plate candidate-region extraction and `color_target` for color-target localization. `scripts/paper_app_names.py` maps the original `plate_recognition` and `recognition` identifiers to these display names. Frozen data keys, source filenames, benchmark code, configurations, and measurements retain their original identifiers.
