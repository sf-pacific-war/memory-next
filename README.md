# Pacific War Memory — Demo Apps

本仓库保留两个**独立运行**的应用，研究主题为太平洋战争，重点包括中国、缅甸及中缅印战区。`step0/` 保存已有馆藏管理原型；`step1/` 是当前的跨平台统一发现 Demo。数字编号用于区分阶段，运行 Step 1 无需先运行 Step 0。

| 目录 | 用途与当前功能 | 本地地址 | 运行要求 |
| --- | --- | --- | --- |
| [step0/](step0/README.md) | 历史馆藏管理原型：目录、媒体、模拟 AI 入库、权限、存储位置和备份 | `http://127.0.0.1:8787` | Python 3.9–3.12 |
| [step1/](step1/README.md) | 统一发现：English／中文界面、跨来源搜索、主题别名、筛选、排序、详情和跳转原馆 | `http://127.0.0.1:8000` | Python 3.9+、现代浏览器 |

两个应用均使用 Python 标准库，无需安装 Python 或 npm 依赖。一起开发和运行全部测试时推荐 **Python 3.12 + Node.js 22**；Step 0 依赖已在 Python 3.13 删除的 `cgi`，暂不支持 Python 3.13+。Node.js 仅用于 Step 1 的检索与界面语言逻辑测试。

## 快速开始：Step 1 统一发现

```sh
git clone https://github.com/sf-pacific-war/memory-next.git
cd memory-next
python3 step1/tools/serve.py
```

打开 **http://127.0.0.1:8000**。顶部可切换 English／中文，也支持 `?lang=en` 和 `?lang=zh-CN`。档案原文保留。可以搜索“缅甸”“滇缅公路”或“英帕尔”，组合来源、资料类型、目录日期和访问状态筛选，再查看记录详情及原馆链接。按 `Ctrl+C` 停止；端口占用时运行 `python3 step1/tools/serve.py --port 8001`。

当前包含 **31 条真实目录样本**：美国国会图书馆（LoC） 16 条、日本国立国会图书馆（NDL） 9 条、欧洲数字文化遗产平台（Europeana） 1 条、美国国家档案馆（NARA） 5 条。网页检索本地快照，不实时查询外馆，也不代表完整馆藏。已有样本可直接预览，**不需要注册 API 或配置 key**。

更新样本时，美国国会图书馆（LoC）、日本国立国会图书馆（NDL） 和 美国国家档案馆（NARA） 公开数据集无需 key；欧洲数字文化遗产平台（Europeana） 获取工具需要自己的 `EUROPEANA_API_KEY`。仓库仅包含空白 [凭据模板](step1/.env.example)，不包含可用密钥。具体命令、来源范围、凭据说明和后续规划见 [Step 1 README](step1/README.md)。新增 [逐平台接入检查](step1/docs/archive-access.md) 覆盖 9 平台、10 种方式，分别说明无须凭据、已有／缺少 key、待 IP 审批和仅网页入口的状态。统一入口可用 `--live --query '飞虎队' --format table` 测试同一关键词；完整命令和中英文实测结果见 [关键词测试说明](step1/docs/archive-search-commands.md)。

档案平台使用中英文对照名称，见 [名称表](step1/docs/archive-platform-names.md)。[台湾档案管理局（archives.gov.tw）总结](step1/docs/taiwan-archives.md)记录免 key CSV 的访问验证、合作 API 状态和后续生产接入；已作为 `taiwan` 状态入口加入统一检查器，目前返回 `manual_only`；尚未实现 CSV 检索或加入当前四来源网页。

## 运行旧应用：Step 0

在仓库根目录另开终端：

```sh
python3 step0/app.py
```

打开 **http://127.0.0.1:8787**；演示账户为 `admin / admin` 和 `viewer / viewer`。首次运行自动在 `step0/` 下创建本地 SQLite 和演示数据。它是本机管理原型，保留原有能力和演示账户；本次整理未将其部署为公开服务。

两个默认端口不同，可以同时运行。各应用以自身文件位置定位资源，因此从仓库根目录启动不会混用数据。Step 0 的 `/api/*` 与 Step 1 的静态页面属于各自服务，没有共享登录、数据库或自动数据导入。

## 目录结构

```text
memory-next/
  README.md
  ci/demo-tests.yml               待启用的 GitHub Actions 测试模板
  step0/                          原有馆藏管理 Demo
    app.py
    static/
    demo-samples/
    docs/
    pacific-war-dam-product-technical-design.html
    README.md
  step1/                          独立的统一发现 Demo
    .env.example                  可选凭据的空白模板
    tools/                        获取、标准化、构建和预览
    data/                         来源元数据快照及审阅排除清单
    site/                         可单独托管的前端和公开目录 JSON
    tests/
    docs/
    README.md
  tests/test_step0_layout.py       旧应用迁移后的启动与权限检查
```

原来的 `app.py`、`static/`、`docs/`、设计 HTML、样本和说明整体保留在 `step0/`。Step 1 的页面、工具、数据、文档和功能测试集中在 `step1/`；其范围不包含馆藏管理。

### 已有本地数据的处理

Git 不会搬运原来被忽略的根目录 `data/`、`storage/`、`backups/`。已有用户应先停服并完整备份，再将旧运行数据作为一组恢复到 `step0/` 的同名目录；未经迁移直接启动会创建新的演示库。完整步骤见 [Step 0 数据迁移说明](step0/README.md#existing-local-data-after-the-folder-move)。本次 PR 不包含本机未提交修改或运行数据。

## 测试与发布

按平台列出的中英文名称、关键词和可复制命令见 [检索词与测试命令](step1/docs/archive-search-commands.md)。各档案平台已经实测／待 API 配置后测试的状态、统一命令和生产接入步骤，集中列在 [访问状态与生产整合计划](step1/docs/archive-access-production-plan.md)。

在仓库根目录运行：

```sh
# Python 3.9–3.12；CI 使用 3.12
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s step1/tests -p 'test_*.py' -v
node --test step1/tests/*.test.mjs
```

Step 0 的 7 项检查使用临时副本和新建的演示数据库，验证迁移后的启动、静态资源、登录、搜索和权限。Step 1 的 149 项 Python 测试、17 项 JavaScript 测试验证数据处理、凭据边界、HTTP 文件隔离和搜索。测试无需 API key、不连接外馆；HTTP 检查会短暂绑定本机端口。

仓库提供 [GitHub Actions 测试模板](ci/demo-tests.yml)，**尚未启用自动 CI**。当前推送凭据缺少 GitHub 的 `workflow` 权限，因此模板保存在 `ci/`；有相应权限的维护者可以按 [启用说明](ci/README.md) 将其放入 `.github/workflows/`。启用后会在 PR 和 `main` 更新时运行这些检查，不自动部署。

两个本地服务都仅监听 `127.0.0.1`。未来的公开试点优先将 **`step1/site/`** 部署到托管静态服务，并在发布前核对样本、来源许可和凭据用途；不要将仓库根目录作为网站发布目录。

下一步依次是：完善相关样本与检索评估、发布托管静态试点、按来源条件接入实时检索，随后再考虑带引用的 LLM 对话和研究成果发布。这些功能尚未实现，详见 [Step 1 下一步计划](step1/README.md#下一步计划)。
