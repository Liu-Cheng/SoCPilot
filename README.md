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
