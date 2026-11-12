# GitHub Pages 展示与自动发布

当前展示地址为 https://yixi0527.github.io/daily_paper/ ，源码仓库为 `yixi0527/daily_paper`。仅切换展示托管，沿用优化后的页面、全部文献、Online 日期、阅读日历、收藏和阅读记录机制。`.openai/hosting.json` 保留历史 Sites 身份，停止向 Sites 发布；原站可用于导出浏览器阅读记录。

## 本机任务执行完整流程

Windows 任务 `Daily Paper NVIDIA Translation` 在上海时间 07:30、09:30、12:30，通过 PowerShell Guard 调用 `scripts/run_sites_automation.ps1`，依次完成采集、NVIDIA 翻译、校验、推送和 GitHub Pages 部署确认。保留唤醒、错过补跑、防重入、15 分钟间隔的三次故障重试和四小时运行上限。电脑需要联网并登录 Windows；无需打开 Codex。Codex 发布自动化 `codex-sites` 已停用，不再参与日常执行。

`prepare_site_update.py` 从已发布的 `codex/site-live` 创建独立 worktree；失败及待发布批次复用原目录，保留用户主工作区未提交的修改。SQLite、锁、翻译缓存、日志、状态仍位于主项目的 `data/site-workflow`。

所有来源成功后才翻译；当天成功采集不重复执行。模型固定为已验证的 `nvidia/nemotron-3.5-super-vl-120b-a12b`，NVIDIA 密钥仅从本机用户环境读取。保留逐篇缓存、同模型重试、严格译文校验和断点恢复，禁止手工生成译文或切换模型。全部翻译完成后生成 `apps/web/public/data/index.json`、文章详情和 `metadata.json`，状态变为 `ready`。

## 自动发布与恢复

`run_sites_update.ps1` 在采集和翻译成功后立即运行发布脚本。已有 `ready` 批次时直接发布原批次，即使它来自前一天，也不重新采集或翻译。当天已成功发布时后续触发直接退出。失败的原始日志、退出码和阶段记录在 `automation-last-run.json` 及其指向的 `task-logs`；Windows 任务按现有重试设置继续。

1. 本机任务在批次的 `checkout_path` 运行 `scripts/publish_github_pages.py`。使用 main 环境 Python `-X utf8`，`PYTHONPATH` 指向该 checkout 的 `apps/api`，`DAILY_PAPER_RUNTIME_DIR` 指向主项目的 `data/site-workflow`。凭据使用本机 Git/GitHub CLI 已有登录。采集或翻译失败会以原退出码结束，不进入发布。
2. 发布脚本先验证完整译文，仅提交生成的数据和 registry，普通推送 `HEAD:main`。不包含主工作区未提交的源码、不强推。已有 GitHub Actions run 时继续同一 run，不重复翻译或重新创建部署。
3. `.github/workflows/pages-sync.yml` 只验证已准备的数据、构建当前优化版前端并部署 `dist`。GitHub 不再采集或翻译，不恢复历史的云端采集与双阶段翻译流程。推送和手动触发都使用同一工作流。
4. GitHub 构建写入准确的 commit 和 workflow run 到线上 `metadata.json`。对应 Actions run 成功后，发布脚本通过 `site_workflow.py publication` 保存 GitHub 回执、更新 `codex/site-live` 并标记 `published`。
5. 失败保留真实退出码、stderr、traceback 和已有 run ID。先读取失败日志，修复后继续原批次；不要重新翻译已完成内容。原 Sites 回执保存在 `data/site-workflow/publications/codex-sites-final.json`。

## 日期和阅读记录

Crossref 缺少 `published-online` 时，Science 使用出版商在 Crossmark 中提交的 `assertion` → `publication_history` → `published`；该字段与纸刊日期分开处理，例：`10.1126/science.ady2660` 为 2026-08-27，纸刊为 2026-10-08。其他期刊仍独立于摘要补查官网 `citation_online_date` 或明确的 `Publication History: Published online`。已核实的日期及来源保存在数据库 `extra_metadata.publisher_online_date`，后续同步保留。纸刊、DOI 注册或 PubMed 入库日期不能替代官网 Online 日期。例：`10.1016/j.tins.2026.09.004` 官网为 2026-10-07，纸刊为 2026-11，PubMed Electronic 为 2026-09-22。

`scripts/backfill_online_dates.py` 保留日期补查能力及失败记录。日期修正后重新导出并发布，无需重译；官网 HTTP 403 等访问失败不填入推测日期。

同一篇 GABAB 示例在 [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0166223626001864) 的 `citation_online_date` 也是 2026/09/22，与 Cell 的 2026-10-07 不同。保留已核实的 Cell 官网日期；补查时逐篇核对 DOI、日期字段与出版商来源，不能混用不同官网的日期或用其他字段覆盖。

阅读与收藏保存在浏览器各自域名下。GitHub Pages 原有记录仍然保留；Sites 域名上的新增记录可在设置中导出，再到 GitHub Pages 设置中导入。导入会合并记录，不覆盖已有已读和收藏。
