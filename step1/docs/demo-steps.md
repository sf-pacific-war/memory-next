# 统一发现 Demo 实施步骤

更新日期：2026-10-11。当前交付范围缩小为第一步“统一发现”：在同一页面搜索中国与缅甸战场相关资料，筛选来源与资料类型，查看目录信息并跳转原馆。先做本地可演示版本，使用容易取得的免费元数据接口；需要人工审批或不适合本地索引的来源暂时跳过。

此前的完整数字图书馆设计作为后续参考，不作为本 demo 的实施门槛。当前不需要登录、LLM、OCR、出版、研究工作台、云账号或托管数据库。搜索网页、美国国会图书馆（LoC）／日本国立国会图书馆（NDL）／欧洲数字文化遗产平台（Europeana） API 获取工具、美国国家档案馆（NARA）官方公开数据集获取工具及本地预览入口已实现；当前展示 31 条真实目录快照，见下文的范围和演示步骤。

先运行：

```sh
# 从 memory-next 仓库根目录进入应用
cd step1
python3 tools/serve.py
```

浏览器打开 **http://127.0.0.1:8000**。无需注册更多账号、提供 key 或安装前端依赖。启动会自动生成 `site/data/catalog.json`；停止时按 `Ctrl+C`。

顶部“数据来源”打开独立页面，也可直接访问 [中文来源页](http://127.0.0.1:8000/sources.html?lang=zh-CN)／[英文来源页](http://127.0.0.1:8000/sources.html?lang=en)。来源页展示当前四个来源、样本数、范围说明和官网链接；与检索页往返时保留 URL 中的搜索、筛选、排序和语言。

平台中英文名称见 [名称对照](archive-platform-names.md)。后续来源研究已补充 [台湾档案管理局（archives.gov.tw）](taiwan-archives.md)，其 CSV 已验证可读取，尚未计入当前网页样本或以下已实现来源。

## 1 先确定可用来源

| 来源 | 获取方式 | 本轮决定 | 已验证情况 |
| --- | --- | --- | --- |
| 美国国会图书馆（LoC） | 公开 JSON API，无需 key | 已接入照片及相关目录 | 当前展示 16 条，保留来源日期与原馆链接 |
| 日本国立国会图书馆检索平台（NDL Search） | 公开 OpenSearch XML；限定 `iss-ndl-opac` 书目数据 | 已接入，用日文补充检索；书目与战后研究材料明确标注 | 当前展示 9 条；不将目录访问状态推断为全文开放 |
| 欧洲数字文化遗产平台（Europeana） | 免费账户，经邮箱确认后自助申请 personal key | 已接入个人开发测试的元数据获取工具 | 原始 3 条候选保留在源文件；展示其中 1 条，另 2 条因同名误命中或相关性未确认而排除 |
| 美国数字公共图书馆（DPLA） | 免费 API，按官方流程用邮箱申请 key | 独立接入检查脚本已提供；尚未纳入网页 | 未配置 key，真实请求未测 |
| 英国国家档案馆（TNA） Discovery | 接口可读，但接入条款要求邮件／IP 信息，且禁止缓存 API 返回内容 | 接入检查脚本待 IP 审批，不导入本地索引 | 当前未确认审批，脚本不发送请求 |
| 美国国家档案馆（NARA） | 官方 AWS 公开目录数据集，无需 key 或 AWS 账户 | 已接入 RG 493 中缅印战区档案小样本；不调用 Catalog API | 当前展示 5 条，包含系列与案卷层级，保留 NAID、原馆和数据文件链接 |
| 日本亚洲历史资料中心（JACAR）、帝国战争博物馆（IWM）及其他机构 | 本轮不依赖尚未确认的自助公开 API | 保留原站入口，不计为已接入来源 | 不为本 demo 逆向内部接口 |

美国国会图书馆（LoC）提供免认证接口并有限流要求，导入按低频串行请求执行。[美国国会图书馆（LoC）使用限制](https://www.loc.gov/apis/json-and-yaml/working-within-limits/)

日本国立国会图书馆（NDL）的 `iss-ndl-opac` 元数据在官方列表列为 CC BY；展示时注明日本国立国会图书馆检索平台（NDL Search） API、数据提供机构及许可。这里使用的是书目元数据，不代表取得原书或扫描件的再发布许可。[日本国立国会图书馆（NDL）数据源及许可](https://ndlsearch.ndl.go.jp/help/api/provider)、[接口说明](https://ndlsearch.ndl.go.jp/help/api/specifications)

欧洲数字文化遗产平台（Europeana） personal key 面向个人探索和开发测试，公开运营服务需按其 project key 流程处理。欧洲数字文化遗产平台（Europeana）已作为第三个来源接入当前快照，美国数字公共图书馆（DPLA）仍不作为演示依赖。[欧洲数字文化遗产平台（Europeana）免费 API](https://www.europeana.eu/en/apis)、[自助申请与用途](https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key)、[美国数字公共图书馆（DPLA）申请说明](https://pro.dp.la/developers/policies)

英国国家档案馆（TNA）暂不导入本地索引。[英国国家档案馆（TNA） API 条款](https://www.nationalarchives.gov.uk/terms-and-conditions/discovery-for-developers-about-the-application-programming-interface-api/)。美国国家档案馆（NARA）则使用独立发布、明确供下载的官方公开数据集；其 Catalog API 仍需邮件申请 key，而且条款要求不要缓存／保存 API 返回内容，入门教程却演示保存文件，两份文档对存储存在冲突。本实现无需依赖这一冲突，因为未调用 Catalog API。[美国国家档案馆（NARA）数据集说明](https://www.archives.gov/developer/national-archives-catalog-dataset)、[无需 AWS 账户的访问说明](https://registry.opendata.aws/nara-national-archives-catalog/)、[美国国家档案馆（NARA） API 条款](https://www.archives.gov/research/catalog/help/api)、[API 入门教程](https://www.archives.gov/research/catalog/help/api-getting-started)。

## 2 验证两个免注册接口

以下请求不带凭据，不产生模型调用费。可直接在终端运行；只读取少量公开目录，不下载原件。

美国国会图书馆（LoC）：

```sh
curl --fail --max-time 30 --get 'https://www.loc.gov/search/' \
  --data-urlencode 'q=Burma Road' \
  --data-urlencode 'fo=json' \
  --data-urlencode 'c=3'
```

日本国立国会图书馆（NDL）：

```sh
curl --fail --max-time 30 --get 'https://ndlsearch.ndl.go.jp/api/opensearch' \
  --data-urlencode 'any=ビルマ' \
  --data-urlencode 'dpid=iss-ndl-opac' \
  --data-urlencode 'cnt=3'
```

2026-10-09 的小请求均返回 HTTP 200。美国国会图书馆（LoC）结果中有《Save Burma》（1943）；日本国立国会图书馆（NDL）结果中有《噫インパール作戦 : 潰走千里・奇跡の生還》（1996）。后者是战后出版物，不能把其出版年份写成战役年份，也不能把所有返回记录称作战时原始档案。

实测也遇到精确短语照片检索和日本国立国会图书馆（NDL）数字开放数据带年份检索超时，因此只把已成功的端点作为首批基础。超时不代表零结果；保留来源状态，不用虚构记录填补。

## 3 用一个主题准备小样本

首个演示主题为“滇缅公路与缅甸战场”。当前合并目录有 31 条：美国国会图书馆（LoC） 16 条、日本国立国会图书馆（NDL） 9 条、欧洲数字文化遗产平台（Europeana） 1 条、美国国家档案馆（NARA） 5 条。源快照保存在 `data/`；网页构建应用 `data/review-notes.json`，暂不展示欧洲数字文化遗产平台（Europeana）中关于耶路撒冷同名道路的记录，以及主题相关性未确认的另一条记录。其他记录仍为候选，不宣称已完成学术鉴定。

以后可扩展至 60 至 100 条，但不是本地演示的前提。先审阅已有记录和新增来源前 10 条，再决定是否增加请求；当前工具不会自动翻页。

准备小型可审阅词表，不调用翻译或模型 API：

| 中文入口 | 英文检索词 | 日文检索词 |
| --- | --- | --- |
| 缅甸 | Burma；Myanmar | ビルマ |
| 滇缅公路 | Burma Road | ビルマ公路；援蒋ルート |
| 英帕尔 | Imphal | インパール |
| 中国远征军 | Chinese Expeditionary Force | 中国遠征軍 |

这些是检索扩展词，不全部是严格同义词。例如“援蒋ルート”更宽；词表保留关系说明，界面可展示实际使用的扩展词。Burma Road 与 Ledo Road 不自动合并为同一地名或同一路线。保留原始标题，不自动生成中文标题或摘要。

导入脚本从固定允许的主机请求，每来源串行，建议至少间隔 5 秒、单请求 30 秒超时。遇到 429 按返回的 Retry-After 等待或停止本轮，不提高并发绕过限制。一个来源失败不会覆盖已有成功样本；终端报告失败，快照保留最后成功更新时间。许可允许的元数据写入本地 JSON，前端检索这份样本，不在每次输入字符时访问外馆。

## 4 将结果整理为统一字段

| 字段 | 处理规则 |
| --- | --- |
| `id` | 来源名加原始 ID；同来源重复 ID 只保留一条 |
| `source`、`holding_institution` | 分开记录 API／聚合来源与原提供机构；未知留空 |
| `title`、`description` | 原始语言；缺失时明确显示未提供 |
| `date_display`、`date_kind` | 保留来源日期及 `source_supplied` 标记；日本国立国会图书馆（NDL）出版日期不作为战役日期，不推测未标明的日期含义 |
| `year` | 保存来源日期中解析出的年份；前端据此计算目录年份区间，日期未知项可保留或排除 |
| `format`、`language` | 照片／地图／书目等统一类型；不从 API 所在国家猜原件语言 |
| `source_url` | 原馆条目稳定链接，是必填字段 |
| `access_status` | 当前仅使用 `online` 和 `unverified`；只有来源提供明确依据才标为可在线访问，其余待确认，不等同于全文开放 |
| `metadata_rights`、`content_rights` | 元数据与原件许可分开，不互相推导 |
| `retrieved_at`、`query_used` | 记录获取时间和查询词，说明样本范围 |
| `subjects` | 保留来源主题词；跨语言检索别名在 `site/search.mjs` 单独维护 |
| `archival_context`、`level_of_description`、`record_group` | 美国国家档案馆（NARA）的真实档案祖先标题、目录层级与档案组；祖先标题参与检索并在详情显示，不从祖先推断本条日期 |
| `dataset_url`、`dataset_updated_at` | 公开数据文件出处及其更新时间；不是战事发生时间，也不保证数据等同于当前实时目录 |

只按 `source + source_id` 去重。不同机构可能描述同一事件、不同复制件或不同层级的记录，首轮不自动跨馆合并。默认展示文字卡片；缩略图有明确使用依据后再增加。

## 5 做一个页面完成发现流程

页面已提供搜索框、主题快捷词、来源／类型／目录日期／访问状态筛选、排序、分页、结果列表和详情区；手机上筛选可折叠。搜索及筛选条件写入 URL，刷新或复制地址可以恢复同一查询；本地地址只能在运行此 demo 的环境访问。每条结果显示标题、来源、日期含义、类型、访问状态及“前往原馆”。界面注明这是演示样本、记录总数和最后更新时间，不宣称覆盖全部馆藏。

搜索采用标题、描述、主题词的关键词匹配；小词表扩展中文入口，优先排标题匹配，再排描述匹配。无需向量数据库、LLM 或全文 OCR。初期结果只对导入的样本有效，不称为实时联邦搜索。

数据来源位于独立的 `sources.html` 页面，与检索页共享语言偏好和样式。来源页有自己的加载提示、失败重试和使用说明；仍读取同一份目录快照，不发起外馆实时查询。

当前结构为“Python 获取工具 → `data/` 源快照 → `build_site_data.py` → `site/data/catalog.json` → 静态 HTML/CSS/JavaScript”。31 条记录直接在浏览器内筛选，无需应用 API 服务器或数据库。可选 key 只供获取工具使用，不写入 JSON、网页、URL 日志或 Git；本地运行时从环境变量读取。

所有 Step 1 文件已集中到仓库根目录的 `step1/`。当前实际结构如下；运行方式见[项目 README](../README.md)：

```text
step1/
  README.md
  .gitignore
  .env.example
  .env.europeana                  可选本机配置，不随仓库提供
  tools/fetch_europeana_metadata.py
  tools/fetch_public_metadata.py
  tools/fetch_nara_metadata.py
  tools/build_site_data.py
  tools/serve.py
  tests/test_europeana_metadata.py
  tests/test_site_data.py
  tests/test_nara_metadata.py
  tests/search.test.mjs
  data/europeana-discovery-candidates.json
  data/loc-discovery.json
  data/ndl-discovery.json
  data/nara-discovery.json
  data/review-notes.json
  site/index.html                检索页面
  site/sources.html              独立数据来源页面
  site/styles.css
  site/app.js                    检索页交互
  site/sources.js                来源页交互、加载与重试
  site/search.mjs
  site/i18n.mjs                  中英文界面文案
  site/page-links.mjs            保留查询条件和语言的跨页链接
  site/icon.svg
  site/data/catalog.json
  docs/demo-steps.md
  docs/europeana.md
```

`python3 tools/serve.py` 自动构建目录，并在 `127.0.0.1:8000` 仅提供 `site/` 内的内容；不会提供 `.env.europeana` 或源快照。只预览现成样本无需 key。不能通过双击 HTML 代替本地 HTTP 服务，否则浏览器可能无法读取 JSON。端口被占用时可用 `--port 8001`。

更新三个免 key 来源（美国国会图书馆（LoC）、日本国立国会图书馆（NDL）与美国国家档案馆（NARA）公开数据集）：

```sh
python3 tools/fetch_public_metadata.py --source all
python3 tools/fetch_nara_metadata.py
python3 tools/build_site_data.py
```

构建后刷新浏览器；来源失败时原有快照保留。数据刷新是显式操作，搜索输入不会调用外馆。每次刷新各来源仅发起一个请求，同一来源多次运行至少间隔 5 秒。

配色来自两个参考项目的页面源码：[memory-next 旧应用的 CSS](../../step0/static/styles.css) 与 [archives-infrastructure](https://sf-pacific-war.github.io/archives-infrastructure/)。界面采用 archives 的纸色 `#f4f2ed`、海军蓝 `#21374d`、黄铜色 `#a8792e`，结合 memory 的墨色 `#17202a`、次级文字 `#627081`、青绿 `#2b6f78` 和边线 `#d8dee5`。大标题使用本机衬线字体，表单和正文使用系统字体。

本地演示无需云账号；公开分享另做静态托管，不承接此前完整平台的云部署复杂度。尚未进行公开部署。

## 6 可选的欧洲数字文化遗产平台（Europeana）凭据配置

现有欧洲数字文化遗产平台（Europeana）样本曾通过真实认证请求取得，但仓库不包含该请求使用的凭据。预览无需 key；若要刷新数据，使用自己的 personal key，按 [README 的配置步骤](../README.md#可选刷新真实来源数据) 从 `.env.example` 创建本地 `.env.europeana`，设置权限为 `0600` 并填入 key。获取工具也支持进程环境变量 `EUROPEANA_API_KEY`。

在 `step1/` 内执行：

```sh
python3 tools/fetch_europeana_metadata.py \
  --env-file .env.europeana \
  --query '"Burma Road"' \
  --rows 3 \
  --output data/europeana-discovery-candidates.json
```

获取工具只调用一次官方接口，保存选定的元数据，不保存原始 API 响应或媒体。候选记录仍需核对主题相关性，接口命中数不等于合格史料数量。错误和超时明确失败，原有成功样本保持不变。字段及凭据处理见[欧洲数字文化遗产平台（Europeana）接入说明](europeana.md)。

美国数字公共图书馆（DPLA）仍作为备选；尚未申请其 key，也无需为了首版 demo 注册更多账号。

## 7 演示顺序与完成标准

演示时按以下顺序：输入“缅甸” → 查看跨语言扩展说明 → 在同一列表查看不同来源 → 筛选为图像或文献 → 组合目录年份与访问状态 → 切换排序、加载更多 → 打开详情查看原始描述与日期含义 → 点击进入原馆 → 刷新或复制查询 URL → 清除筛选返回全部结果。另用手机窄屏检查折叠筛选和详情阅读。

完成标准：

- 至少两个实际接入来源，各有相关记录；原站搜索链接不计为 API 接入。
- 所有记录都有有效 ID、来源和原馆链接；每来源抽查至少 10 条，不足 10 条则检查全部。
- 中文主题入口能命中已标注的英文／日文样本；不声称支持任意跨语言语义检索。
- 来源、类型、日期和访问状态筛选可组合；日期未知项有明确处理。
- 未提供全文的记录不显示“在线全文”；API 失败不显示“零结果”。
- 同来源重复记录不重复显示；原文可见，来源归属与必要许可说明完整。
- 无密钥进入静态文件、Git 或浏览器；没有模型调用、自动收费资源或外馆原件批量下载。

本地自动化测试命令：

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/search.test.mjs
```

测试不调用真实 API；Node.js 仅用于搜索逻辑测试，运行网页不需要 Node.js 或 npm。若系统 `node` 损坏，可以用另一个可运行的 Node.js 运行时绝对路径替换 `node`。接口刷新与浏览器人工演示是独立检查，不能用离线测试通过替代真实接口验证。

本次实现验证：48 项 Python 测试与 10 项搜索逻辑测试通过。浏览器已检查 1280px 桌面与 390px 手机布局、中文主题命中日文书目、组合筛选、无结果恢复、日期范围错误提示、排序、加载更多、刷新恢复筛选、详情和使用说明。人为移走目录 JSON 后能显示加载失败，恢复文件并点击“重新载入”可恢复结果；正常使用未发现浏览器错误。新增美国国家档案馆（NARA）后，检索“缅甸”实测返回 29 条：美国国会图书馆（LoC） 16、日本国立国会图书馆（NDL） 7、欧洲数字文化遗产平台（Europeana） 1、美国国家档案馆（NARA） 5；来源筛选、档案层级、公开数据出处和四来源布局均已在浏览器核对。美国国家档案馆（NARA）的 5 条样本中，1 条存在数字对象且访问限制为 Unrestricted，其余 4 条保留为 unverified。原馆链接保留源地址，未逐个验证外部页面仍然在线。

新增的独立平台检查与凭据清单见 [逐平台接入测试](archive-access.md)；最新 unit test 数量和本次真实请求状态见 [验证记录](archive-access-validation.md)。上文浏览器演示记录保留当时的验证范围。
