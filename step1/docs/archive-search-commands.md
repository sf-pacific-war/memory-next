# 档案平台检索词与测试命令

核对日期：2026-10-12（UTC）。以下命令对应当前代码的 **8 个平台、9 种访问路径**，可直接复制到终端。[台湾档案管理局（Taiwan NAA）](taiwan-archives.md)已加入 `taiwan` 有界 CSV 路径，无需 key；可匹配案名、全宗和档号，并独立导入网页快照。A+ 实时 API 尚未接通。平台英文全称见 [中英文名称对照](archive-platform-names.md)。

## 1. 先进入正确目录

目前本机运行的独立 Step 1 应用：

```sh
cd /Users/jingxugao/Documents/sf-pacific-war-harness/step1-discovery
```

当前 `memory-next` PR 的隔离 checkout 对应路径是下面这个目录；仅在需要测试该 checkout 时使用，临时目录可能随后被移除：

```sh
cd /private/tmp/memory-next-step-layout-a2ddwlby/step1
```

在其他位置 clone 的 `memory-next` 中，进入该仓库的 `step1/`。以下所有命令均在所选的 Step 1 目录内执行。两个目录的本地凭据不自动共享，PR 不包含真实 key。

### 一条命令测试“飞虎队”

2026-10-11 已实测“飞虎队”与 `Flying Tigers`；各平台返回值见 [真实测试记录](archive-access-validation.md#统一关键词的真实测试2026-10-11)。不同语言的结果可能差很多，命中仍需人工核对。

在已配置 `.env.europeana` 的本机应用目录执行：

```sh
python3 tools/check_archives.py --source all --live --query 'Flying Tigers' --rows 3 --env-file .env.europeana --format table
```

把英文词替换成自己想测试的任意关键词即可；例如原样向 API 发送中文：

```sh
python3 tools/check_archives.py --source all --live --query '飞虎队' --rows 3 --env-file .env.europeana --format table
```

如果当前目录没有该凭据文件，先去掉 `--env-file .env.europeana`。不需要 key 的来源仍会测试；缺 key 的来源列为 `missing_credential`。已有统一配置时可换成 `--env-file .env.archives`。**五条 API 查询保持原词**；台湾 CSV 额外使用有限的繁简／英文别名，并在 JSON 中列出 `effective_queries`。这不是通用翻译。`飞虎队` 和 `Flying Tigers` 仍是两次独立测试，各馆的查询语法及语言覆盖不同。

表格逐行显示来源、状态、是否发送请求、样本数和总数；不支持查询或缺条件的行没有命中数。默认输出 JSON，移除 `--format table` 即可；JSON 的 `mode=keyword` 和 `query` 记录这次显式查询。完整记录仍不导出、不加入网页。日本亚洲历史资料中心（JACAR）和帝国战争博物馆（IWM）列出 `manual_only`；台湾 CSV 若为部分扫描，表格总数为 `—`，应查看 JSON 中的扫描范围；美国国家档案馆（NARA）固定数据集列出 `query_not_supported`，不会下载后冒充关键词结果。

## 2. 先区分四种测试

| 目的 | 命令特征 | 是否联网／写入样本 |
| --- | --- | --- |
| 检查本机配置 | `access_*.py` 或 `check_archives.py`，不加 `--live` | 不联网；不验证 key 是否被外馆接受 |
| 检查真实访问及检索响应 | 对支持的来源加 `--live --query '关键词'` | 每来源最多一个请求；输出状态和计数，不保存档案记录 |
| 验证代码行为 | `unittest` / `node --test` | 使用本地或合成数据；不访问外馆、不需要真实 key |
| 查询现有网页样本 | `serve.py` 后在网页输入关键词 | 查询当前 10 个来源机构的 55 条本地记录；不会向外馆实时搜索 |

`access_*.py` 不会把新结果导入网页。更新样本由已有 `fetch_*.py` 完成，见 [README 的数据刷新步骤](../README.md#可选刷新真实来源数据)。

## 3. 每个入口的关键词命令

下面三条可直接进行免 key 的真实测试：

```sh
# 美国国会图书馆：滇缅公路；当前限定照片目录
python3 tools/access_loc.py --live --query 'Burma Road' --rows 3


# 美国国家档案馆公开数据集：读取固定 RG 493 分片，没有关键词参数
python3 tools/access_nara.py --live --rows 3

# 台湾档案管理局：下载有界 CSV 后在本地匹配，非 A+ 实时查询
python3 tools/access_taiwan.py --live --query '驻印军' --rows 3
```

欧洲数字文化遗产平台（Europeana）使用本机已有的凭据文件；单引号内部的双引号会作为查询文本的一部分传给 API：

```sh
python3 tools/access_europeana.py --live --env-file .env.europeana --query '"Burma Road"' --rows 3
```

下面三条仅在对应 key 或来源 IP 审批就绪后用于真实测试。美国数字公共图书馆（DPLA）和美国国家档案馆（NARA）的 `.env.archives` 配置方法见下一节：

```sh
# 美国数字公共图书馆：需要 DPLA_API_KEY
python3 tools/access_dpla.py --live --env-file .env.archives --query 'Burma' --rows 3

# 美国国家档案馆实时 Catalog API：需要 NARA_API_KEY
python3 tools/access_nara_catalog.py --live --env-file .env.archives --query 'Burma' --rows 3

# 英国国家档案馆：只在当前请求来源 IP 已经获批之后使用此标记
python3 tools/access_tna.py --live --permission-confirmed --query 'Burma' --rows 3
```

日本亚洲历史资料中心（JACAR）和帝国战争博物馆（IWM）目前只输出官方网页入口及接入说明，不能通过当前脚本发起关键词搜索：

```sh
python3 tools/access_jacar.py
python3 tools/access_iwm.py
```

| 平台／路径 | 未传 `--query` 时的默认词 | 可替换的示例关键词 | 凭据或条件 |
| --- | --- | --- | --- |
| 美国国会图书馆（LoC） | `Burma Road` | `Burma`、`China`、`Ledo Road` | 无需 key |
| 欧洲数字文化遗产平台（Europeana） | `"Burma Road"`，包括双引号 | `Burma`、`China` | `EUROPEANA_API_KEY` |
| 美国国家档案馆（NARA）公开数据集 | 无 | **不支持关键词**；不要加 `--query` | 无需 key 或 AWS 账户 |
| 美国国家档案馆（NARA） Catalog API 实时目录 | `Burma` | `Burma Road`、`China Burma India` | `NARA_API_KEY` |
| 美国数字公共图书馆（DPLA） | `Burma` | `Burma Road`、`China` | `DPLA_API_KEY` |
| 英国国家档案馆（TNA） Discovery | `Burma` | `Imphal`、`Burma Road` | 来源 IP 事先获批 |
| 日本亚洲历史资料中心（JACAR） | 不执行查询 | 在 [官方网页](https://www.jacar.go.jp/english/) 手动检索 `ビルマ` 等词 | 当前是 `manual_only` |
| 帝国战争博物馆（IWM） | 不执行查询 | 在 [Collections Search](https://www.iwm.org.uk/collections/search) 手动检索 `Burma` 等词 | 当前是 `manual_only` |
| 台湾档案管理局（Taiwan NAA） | `駐印軍` | `驻印军`、`滇缅`、`遠征軍`，或 `駐印軍\|滇緬` | 无需 key；案名／全宗／档号的有界 CSV 匹配，非全文 API |

可替换的关键词只是查询示例，不保证有结果，也没有在本次文档核对中逐个进行外网实测。各馆检索语法不同；命令行中的引号用于保护空格，不代表所有 API 都执行完全相同的词组匹配。

API 查询词不会自动翻译；例如 `--query '缅甸'` 原样发送给选定 API，网页主题扩展不用于 API 探针。台湾 CSV 使用单独列明的有限别名：应检查 `effective_query`／`effective_queries`，并结合 `scan_complete` 理解结果。日本亚洲历史资料中心（JACAR）和帝国战争博物馆（IWM）即使收到 `--query` 也返回 `manual_only`，不会执行查询。

“飞虎队”可另用英文 `Flying Tigers` 或 `American Volunteer Group` 逐来源复测；命中是否相关仍需核对。

## 4. 本地 credential 文件

`.env.europeana` 是此前在原应用目录配置的欧洲数字文化遗产平台（Europeana）文件；已有文件可继续使用。其他目录不一定存在此文件。需要统一存放已申请的三个 key 时，可运行：

```sh
# -n 避免覆盖已有配置；随后在本地编辑器中填写已取得的 key
cp -n .env.example .env.archives
chmod 600 .env.archives
```

配置项是：

```dotenv
EUROPEANA_API_KEY=
DPLA_API_KEY=
NARA_API_KEY=
```

只有填入 `EUROPEANA_API_KEY` 后，才能将欧洲数字文化遗产平台（Europeana）命令的 `--env-file .env.europeana` 改为 `--env-file .env.archives`。复制空白模板不会自动复制已有 key，也不会注册新 key。

凭据文件必须已经存在、位于当前 Step 1 内、被 Git 忽略，且不超过 64 KiB。此项目的 `.gitignore` 已忽略 `.env.*`，保留空白 `.env.example`。同一 key 不要重复定义；文件只按字面读取 `KEY=value`，不执行 shell、不展开变量。

程序不会自动加载 `.env.europeana` 或 `.env.archives`；必须传 `--env-file`，或者在进程环境中提供对应变量。有效的环境变量优先于文件。对需要 key 的来源，不存在的文件返回 `credential_error`；存在但对应项为空时返回 `missing_credential`。免 key 的来源不读取凭据文件。真实 key 不应放入命令参数、聊天、网页或 Git。

## 5. 离线预检和统一入口

```sh
# 不联网：一次列出全部来源的配置状态
python3 tools/check_archives.py

# 同样不联网，显式检查已配置的欧洲数字文化遗产平台（Europeana）文件
python3 tools/check_archives.py --env-file .env.europeana

# 单个入口不加 --live，即为离线预检
python3 tools/access_loc.py --query 'Burma Road' --rows 3

# 统一入口选择一个来源后，可替代该来源独立脚本
python3 tools/check_archives.py --source loc --live --query 'Burma Road' --rows 3
python3 tools/check_archives.py --source europeana --live --env-file .env.europeana --query '"Burma Road"' --rows 3

# 所有来源按各自默认词串行检查；缺条件的来源跳过并报告原因
python3 tools/check_archives.py --live --env-file .env.europeana --rows 3

# 所有支持查询的 API 使用同一个关键词；其他路径明确跳过
python3 tools/check_archives.py --live --env-file .env.europeana --query 'Flying Tigers' --rows 3 --format table
```

统一入口可选 `--source` 值：`all`、`loc`、`europeana`、`nara`、`nara_catalog`、`dpla`、`tna`、`jacar`、`iwm`、`taiwan`。默认是 `all`；**`all` 可以同时传 `--query`**。共有 5 条 API 路径和 1 条台湾 CSV 路径支持关键词；API 是否真正请求取决于 key 和审批。美国国家档案馆（NARA）固定数据集及 2 个网页入口不执行关键词查询。

不传 `--query` 时，JSON 的 `mode=access`，使用各 API 自己的默认词并检查固定数据集；传 `--query` 时，`mode=keyword`，以同一词测试所有支持查询且满足条件的来源。这个命令用于状态和计数检查，尚不返回跨平台档案列表。

访问检查的 `--rows` 为 1–5，默认 3；API 查询词须非空且不超过 200 个字符。每个来源最多一个请求，无自动翻页或重试。五条 API 与美国国家档案馆（NARA）固定数据集为 30 秒超时、2 MiB 上限；台湾 CSV 使用 4 MiB 加 1 字节截断检测、200,000 行扫描上限、30 秒网络操作超时与 120 秒读取预算。美国国家档案馆（NARA）数据集只在不传查询词的访问检查中读取整个固定小分片，`--rows` 仅限制报告的样本量。

## 6. Unit tests 和网页关键词测试

```sh
# 只运行接入检查 unit tests；无需真实凭据或外网
python3 -B -m unittest discover -s tests -p 'test_a*.py' -v

# 完整 Python 测试；HTTP 隔离测试会短暂监听本机端口
python3 -B -m unittest discover -s tests -p 'test_*.py' -v

# 网页检索逻辑测试，需要可运行的 Node.js，无需 npm install
node --test tests/*.test.mjs

# 启动网页；读取已有快照，不需要 API key
python3 tools/serve.py
```

启动后保持该终端运行，在浏览器打开以下地址。macOS 也可在另一个终端执行这些命令：

```sh
# 英文关键词：当前共享目录
open 'http://127.0.0.1:8000/?lang=en&q=Burma'

# 中文“缅甸”的 URL 编码，对应网页内置的主题扩展
open 'http://127.0.0.1:8000/?lang=zh-CN&q=%E7%BC%85%E7%94%B8'

# 中文“滇缅公路”
open 'http://127.0.0.1:8000/?lang=zh-CN&q=%E6%BB%87%E7%BC%85%E5%85%AC%E8%B7%AF'

# 限定美国国会图书馆（LoC）和美国国家档案馆（NARA）两个来源
open 'http://127.0.0.1:8000/?q=Burma&source=LoC&source=NARA'
```

`open` 是 macOS 命令；其他系统直接把网址粘贴到浏览器。网页用 `q` 参数保存关键词、`lang=en`／`lang=zh-CN` 选择 English／中文界面；CLI 用 `--query`。切换界面语言不会自动翻译原馆标题、描述或任意检索词。当前网页包含 10 个来源机构、55 条去重记录；来源分别标注 API、公开数据集或人工整理；美国数字公共图书馆（DPLA）／英国国家档案馆（TNA）的检查通过也不会自动成为网页来源。

## 7. 结果如何判断

| 状态 | 含义 |
| --- | --- |
| `ready` | 本机配置满足条件，未验证网络或权限 |
| `ok` | 本次请求成功且响应结构通过校验；`sample_count: 0` 也可为有效结果 |
| `missing_credential` | 当前来源没有 key，未发送请求 |
| `permission_required` | 英国国家档案馆（TNA）来源 IP 尚未确认获批，未发送请求 |
| `manual_only` | 当前只有官方网页入口，未发送请求 |
| `query_not_supported` | 当前路径是固定数据集，不支持本次关键词；未发送请求，不能将其看成零命中 |
| `credential_error` | key 格式、文件路径、文件内容或 Git 忽略条件不满足 |
| `access_denied` / `rate_limited` / `timeout` / `network_error` | 权限、限流或网络问题，不等于零条档案 |

成功检查只输出诊断和计数，不输出完整档案记录。API 明确提供总数时才返回 `total_results`；台湾 CSV 只在完整扫描时提供此值，部分扫描通过 `matched_count`、`scanned_rows`、`scan_complete` 与 `source_exhausted` 说明范围。部分样本的零匹配不是全馆零命中。美国国家档案馆（NARA）固定数据集的样本数不是关键词命中数或整个档案组总数。

退出码：`0` 表示该次检查成功，或离线预检／网页入口正常；`2` 表示缺 key、缺审批、路径不支持关键词、仅网页入口却要求 `--live`，或参数有误；`1` 表示请求失败、响应不符或凭据配置错误。统一检查有混合结果时优先返回 `1`，其次为 `2`，详细状态仍逐来源保留。全来源关键词测试即使可检索来源都成功，也会因为固定数据集和网页入口而返回 `2`。

代码和命令核对不等于新增 API 实测。已有真实访问证据见 [验证记录](archive-access-validation.md)；申请凭据、上线整合和来源限制见 [访问状态与生产整合计划](archive-access-production-plan.md)。[台湾档案管理局（Taiwan NAA）](taiwan-archives.md)已支持 `access_taiwan.py`／`--source taiwan` 有界 CSV 检查；记录导出与网页更新使用独立导入器：

```sh
# 候选先单独保存，审阅后再替换发布快照
python3 tools/fetch_taiwan_metadata.py --live --query '驻印军' --rows 20 --output data/taiwan-discovery-candidates.json
# 已取得的 CSV 可通过 --input 读取；若只下载前缀，必须加 --partial-input
python3 tools/fetch_taiwan_metadata.py --input /absolute/path/to/official.csv --query '駐印軍' --rows 20 --output data/taiwan-discovery-candidates.json
```

完整参数、截断解释、原馆链接及发布步骤见[台湾来源说明](taiwan-archives.md)。
