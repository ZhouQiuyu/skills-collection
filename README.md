# Skills Collection

个人技能收藏仓库，供 **CC Switch** 发现、安装和更新。技能保留上游原文和许可证，由 GitHub Actions 自动同步。

## 已收录

| 技能 | 用途 | 上游 | 许可 |
| --- | --- | --- | --- |
| [plain-writing](skills/plain-writing/SKILL.md) | 用简单、直接的语言撰写和修改文字 | [docwriter-org/plain-writing-skill](https://github.com/docwriter-org/plain-writing-skill) | MIT |
| [humanizer](skills/humanizer/SKILL.md) | 修改文字中的常见 AI 写作痕迹，保留原意 | [blader/humanizer](https://github.com/blader/humanizer) | MIT |

## 在 CC Switch 中安装

打开 **Skills → 仓库管理 → 添加仓库**，填写：

| 项目 | 内容 |
| --- | --- |
| 仓库 URL | `https://github.com/ZhouQiuyu/skills-collection` |
| Owner（旧版界面） | `ZhouQiuyu` |
| Name（旧版界面） | `skills-collection` |
| 分支 | `main` |
| 技能路径 / 子目录（如果有） | `skills` |

添加后到“发现”中选择技能并安装。没有子目录选项的版本可从仓库根目录递归发现 `SKILL.md`。

仓库同步与电脑上的技能更新是两步：本仓库自动获取上游更新；电脑上的已安装技能，在 CC Switch 中点击 **检查更新 → 更新**。仓库同步不会直接改动你的电脑。

参考：[CC Switch 官方技能管理文档](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/zh/3-extensions/3.3-skills.md)。不同版本的界面名称可能略有差异。

## 自动同步

- 每天北京时间 **09:17** 检查两个上游仓库的 `main` 分支。GitHub 的定时任务可能延迟。
- 在 **Actions → Sync upstream skills → Run workflow** 中可立即检查。
- 修改 `sources.json` 或同步脚本后也会触发检查。
- 按上游固定提交复制完整技能目录，保留引用文件、文件权限和版权声明。这里使用实际文件，方便 CC Switch 通过 GitHub ZIP 下载。
- `sources.lock.json` 记录每个技能的上游提交和每个文件的 SHA-256；没有变化时不重复提交。
- 下载、技能结构或许可证检查失败时，任务失败且不会发布不完整更新。自动流程不会运行上游仓库里的脚本或工作流。
- 上游许可证的内容变化时暂停同步，待核对后再更新清单中的许可指纹；避免在条款变化后继续自动转载。
- 为减少公开仓库连续 60 天无活动导致定时任务停用的情况，45 天无新提交时会生成一条空的维护提交。若任务已停用，仍需在 Actions 中重新启用。
- 使用仓库自带的 `GITHUB_TOKEN` 推送，不需要额外配置个人访问令牌。新仓库需允许 Actions 运行和工作流写入内容；分支规则也必须允许机器人的同步提交。

参考：[GitHub 定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

## 以后添加技能

把技能的 GitHub 链接发到维护本仓库的对话中，并在新对话中附上本仓库链接。维护时会确认技能目录和许可，添加来源，然后同步。首次添加后，后续更新由本仓库的工作流完成。

来源清单 `sources.json` 中每项包含：

| 字段 | 含义 |
| --- | --- |
| `name` | 技能目录名，与上游 `SKILL.md` 的 `name` 一致 |
| `repository` | 上游 `owner/repository` |
| `ref` | 跟踪的分支或标签；需要持续更新时选择分支 |
| `path` | 上游技能目录，根目录写 `.` |
| `license_file` | 上游许可证路径，会复制到技能目录的 `LICENSE` |
| `license_sha256` | 已核对许可文本的 SHA-256；条款变化需重新核对 |

一次只选择一个技能目录。多技能仓库中，每个要收录的技能分别配置一项。不自动导入未来新增的技能，也不覆盖未指定的其他仓库文件。

`skills/` 是由来源清单管理的镜像目录：移除来源并重新同步后，对应技能也会移除。请勿直接修改其中的镜像文件，否则下次同步会覆盖；需要定制时应另建自己的技能。

## 本地维护与检查

需要 Python 3.10+ 和 Git，无额外 Python 依赖。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_skills.py
python3 scripts/sync_skills.py --check
```

## 版权

各技能属于其原作者，分别遵循各自目录中的 `LICENSE`。本仓库的维护脚本、测试及工作流采用根目录的 MIT 许可。收录不代表原作者背书。
