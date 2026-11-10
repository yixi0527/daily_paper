# Codex Sites 自动更新

项目根目录：`D:\04_yixiPrivate\03_myToolApps\daily_paper`。Sites 项目 ID 以 `.openai/hosting.json` 为准。使用当前安装的 Sites 技能和工具；插件缓存版本会更新，不要复用已经失效的 helper 路径。此流程不推送 GitHub，也不触发 GitHub Pages。

## 采集和翻译

Windows 任务每天在上海时间 07:30、09:30、12:30 调用 `scripts/run_sites_automation.ps1`，通过 PowerShell Guard 执行。任务保留唤醒、错过后补跑、防重入、15 分钟间隔的三次故障重试和四小时运行上限。

`prepare_site_update.py` 从 `codex/site-live` 创建独立 worktree。未完成、失败或已经准备好但未发布的批次继续使用原执行目录；当天已经发布则直接结束。主工作区的未提交代码不会被纳入自动发布。

数据库、锁、翻译缓存、日志及状态在 `data/site-workflow`。采集复用现有来源和重试规则；全部来源成功后才开始翻译。同一天重试复用成功采集的结果。NVIDIA 密钥只从本机用户环境读取；模型固定为已实测的 `nvidia/nemotron-3.5-super-vl-120b-a12b`。翻译完成逐篇写入缓存，之后合并 registry 并校验。任一阶段失败保留完整 traceback 和退出码，不发布不完整数据。

该模型使用 NVIDIA 示例的 temperature=1.0、top_p=0.95，关闭 thinking，输出上限 16384 token。实测两篇标题和摘要均成功返回，关键科学术语正确；先前 Lightning 生成的完整译文继续保留。`finish_reason=length` 会保留响应与错误，并在同一模型、同一参数下最多尝试三次；达到上限即报错。此规则针对实测出现的重复输出和截断，不接受部分 JSON 或手工拼接译文。

## Codex 发布检查

Codex 在上海时间 09:00、11:00、14:00 检查 `data/site-workflow/state.json` 和 `automation-last-run.json`。

1. `status=ready` 才可发布，包括先前尚未发布的完整批次。正在运行时保持安静；失败则读取实际日志，报告具体错误，等待已配置的下一次重试。已经发布时不重复发布。
2. 使用 state 的 `checkout_path`，核对 `.openai/hosting.json`。读取 `get_site` 并取得该 Site 的新 source credential。凭据只保存在内存，通过 stdin 交给当前 Sites `site-workflow.mjs`，不写入文件或命令行。
3. 按 Sites 技能打开执行目录，再用 `build-site.mjs` 构建和 `site-workflow.mjs` 同步精确源码并打包。归档放到运行目录外、项目 `data/site-workflow` 下。打包前所有翻译必须完整。
4. 站点保持 owner-private，调用 `save_version_and_deploy_private`；如果已经有对应的保存版本或进行中的 deployment，按 Sites 技能继续该次发布。将准确的版本 ID、deployment ID、commit 和归档路径保存在 `publication.json`，失败后从这一阶段继续，禁止重复翻译。
5. 仅在原生部署结果 `status=succeeded` 后标记发布成功。使用 main 环境 Python `-X utf8`，将 `PYTHONPATH` 指向主项目的 `apps/api`，将 `DAILY_PAPER_RUNTIME_DIR` 指向主项目的 `data/site-workflow`。向主项目的 `scripts/site_workflow.py publication` 通过 stdin 传入 JSON：`published` 布尔值、`commit_sha`、`url`、`version_id`、`deployment_id` 及可选归档路径。先记录 `published=false` 的发布进度，成功后再传 `published=true`。该操作记录回执并更新 `codex/site-live`，不改写用户的工作分支。
6. 成功后可清理本次独立 worktree；删除前核对其绝对路径位于本项目的 `data/site-workflow/checkouts` 内，保留数据库、缓存和最新状态。不可删除用户目录或清理无关 worktree。

没有新文章或状态未变化时保持安静。只在有实际新增内容成功发布、执行失败或需要用户处理时通知。阅读记录始终由浏览器保存；发布不包含个人已读与收藏记录。
