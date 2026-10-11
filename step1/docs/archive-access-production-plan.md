# 档案平台接入状态、统一测试与生产整合计划

更新日期：2026-10-11。范围为目前 Step 1 推荐清单中的 **8 个档案／聚合平台、9 种访问方式**，NARA 的公开数据集和实时 Catalog API 单列。本文件集中说明当前证据、API 配好后的测试命令，以及接入生产系统的工作顺序。

**当前有 4 种方式完成真实小请求；3 种方式已有脚本，待 key 或 IP 审批后实测；另 2 个平台只有网页入口，取得正式 API 后还需开发。** 本文中的“API 将可获得”是后续实施假设，不代表已经取得凭据、审批或接口资料。

现有网页仍使用 LoC、NDL、Europeana、NARA 的 **31 条目录快照**。接入检查脚本输出状态和计数，既不导入新记录，也不会自动增加网页中的来源。馆藏管理不在本计划范围内。

## 1. 全部平台的访问状态

最近一次真实小请求在 **2026-10-11 22:08 UTC** 完成；每种已测试方式仅请求一次、检查 3 条样本。本次文档整理没有重新调用档案 API。详细执行证据见 [验证记录](archive-access-validation.md)。

| 平台／访问方式 | 当前代码入口 | 当前状态 | 凭据／访问前提 | 条件就绪后可以做什么 |
| --- | --- | --- | --- | --- |
| 美国国会图书馆 LoC | [access_loc.py](../tools/access_loc.py) | **实测通过**，照片 JSON API | 无需 key | 直接复测，随后扩展主题样本、分页和字段映射 |
| 日本 NDL Search | [access_ndl.py](../tools/access_ndl.py) | **实测通过**，`iss-ndl-opac` 书目 | 该数据子集无需 key | 直接复测；增加数据提供方时逐项核实接口及元数据条件 |
| NARA 公开数据集 | [access_nara.py](../tools/access_nara.py) | **实测通过**，RG 493 一个固定分片 | 无需 key 或 AWS 账户 | 直接复测；规划分片选择与更新机制；不是关键词搜索 |
| Europeana Search API | [access_europeana.py](../tools/access_europeana.py) | **实测通过**，已有本地 personal key | `EUROPEANA_API_KEY` | 开发 key 可复测；生产服务按 project key 流程确认用途 |
| DPLA | [access_dpla.py](../tools/access_dpla.py) | **待实测**；请求和解析已有离线测试 | 获取并配置 `DPLA_API_KEY` | 无需重写现有接入检查，配置后直接运行真实小请求 |
| NARA Catalog API v2 | [access_nara_catalog.py](../tools/access_nara_catalog.py) | **待实测**；与公开数据集分开 | 获取并配置 `NARA_API_KEY`；通过 `x-api-key` header 认证 | 配置后直接测试；API 响应和公开数据集分别管理 |
| 英国 TNA Discovery | [access_tna.py](../tools/access_tna.py) | **待实测**；未确认 IP 审批 | 执行机器的出口 IP 获批；没有已配置的 key 参数 | 获批后添加 `--permission-confirmed` 实测 |
| JACAR | [access_jacar.py](../tools/access_jacar.py) | **仅网页入口**；没有已实现的 API 请求 | 假设未来取得官方接口说明和访问授权 | 先实现真实适配器及测试，再加入 API 实测清单 |
| IWM | [access_iwm.py](../tools/access_iwm.py) | **仅网页入口**；没有已实现的 API 请求 | 假设未来取得官方接口说明和访问授权 | 同上；现有脚本不会因为填入 key 就开始检索 |

“实测通过”仅证明当时的小请求可达且响应结构符合预期，不证明持续可用、资料主题准确、全文可读或可再发布。JACAR／IWM 是“当前未确认可接入的官方公开 API”，不是断言机构没有 API。

凭据与访问依据：[Europeana key 类型](https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key)、[DPLA key 申请](https://pro.dp.la/developers/policies)、[NARA API 接入](https://www.archives.gov/research/catalog/help/api)、[TNA IP 接入要求](https://www.nationalarchives.gov.uk/terms-and-conditions/discovery-for-developers-about-the-application-programming-interface-api/)。

## 2. 一个命令检查全部来源

### 2.1 运行位置与准备

使用 `memory-next` 仓库时，从仓库根目录进入应用：

```sh
cd step1
```

使用原来的 `sf-pacific-war-harness` 仓库时，从该仓库根目录执行 `cd step1-discovery`。下文命令均从这个应用目录执行，Python 3.9+ 即可，不需要安装第三方包。

如果已有 `.env.europeana`，现在即可复查四个已实测来源，同时列出其他来源的未满足条件：

```sh
python3 tools/check_archives.py --live --env-file .env.europeana
```

该文件仅配置 Europeana，且其余条件未变化、四个请求均成功时，预期汇总为：

```json
{"ok": 4, "missing_credential": 2, "permission_required": 1, "manual_only": 2}
```

### 2.2 新 API key 获得后

首次创建统一配置文件；`cp -n` 保留已存在的文件：

```sh
cp -n .env.example .env.archives
chmod 600 .env.archives
```

在本地编辑器中填写下列变量。已有的 Europeana key 可以继续使用；DPLA、NARA 获得后再填写。不要将真实值写入 Markdown、命令参数、网页或 Git。

```dotenv
EUROPEANA_API_KEY=
DPLA_API_KEY=
NARA_API_KEY=
```

程序也支持同名进程环境变量，优先级高于文件。空值表示没有配置。有效环境变量已提供当前 key 时，程序不读取配置文件；否则，显式指定不存在／不受 Git 忽略／越出应用目录的文件会报告 `credential_error`。本地文件的检查不替代服务端认证。

**三个 key 已配置，且当前执行机器的出口 IP 已获 TNA 批准后，用这一条命令测试所有访问方式：**

```sh
python3 tools/check_archives.py --source all --live --rows 3 --env-file .env.archives --permission-confirmed
```

没有完成 TNA 审批时，省略 `--permission-confirmed`；其他来源仍可测试。该参数仅表明使用者确认已获批，不会开通权限。换到 staging 或生产主机时，要核对那台主机的实际出口 IP，不能沿用本机测试的假设。

所有已实现的机器接口都成功时，当前代码的**预期结果**是：

```json
{"ok": 7, "manual_only": 2}
```

此情景已用 mock 验证程序行为，**尚未作为真实执行结果发生**。JACAR、IWM 仍为网页入口，因此统一命令会返回退出码 **2**，不是 0。未来两者适配器完成且全部九路真实成功时，才预期为 `{"ok": 9}` 和退出码 0。

只想检查配置而不访问外馆，移除 `--live`。三个 key 和 TNA 确认齐备时，预检会返回 `{"ready": 7, "manual_only": 2}`、退出码 0、实际请求数 0；`ready` 不证明 key 有效。

### 2.3 结果与失败怎么判断

| 输出／退出码 | 含义 | 下一步 |
| --- | --- | --- |
| `ok` | 已发请求并通过结构校验；可能是有效的零结果 | 继续内容与生产整合验收 |
| `missing_credential` | 没有目标 key，未发送请求 | 配置对应变量后复测 |
| `credential_error` | key 格式或文件条件不正确，未发送请求 | 检查变量、文件位置和忽略规则 |
| `permission_required` | TNA 审批尚未确认，未发送请求 | 完成出口 IP 接入并在正确主机复测 |
| `manual_only` | 仅提供网页入口，未发送 API 请求 | 保留网页入口，取得文档后开发适配器 |
| `access_denied` | 401／403 | 检查 key、账号范围、审批和出口 IP |
| `rate_limited` | 429 | 停止本轮，按来源要求等待，不连续重试 |
| `timeout`／`network_error` | 网络或超时错误，不是“没有档案” | 查网络、服务状态，之后低频复测 |
| `invalid_response` | 返回结构异常、大小超限或返回 HTML 等 | 核实真实 API 文档和解析器 |
| 退出 `0` | 所要求的检查成功；预检不等于已联网 | 同时阅读每个来源的状态 |
| 退出 `2` | 有缺凭据、待审批、网页入口或输入参数问题 | 阅读逐来源状态，不能一律当作测试失败或通过 |
| 退出 `1` | 出现实际请求、响应或配置错误；聚合时优先于 2 | 处理具体错误后复测 |

每个满足访问条件的来源最多一次请求：串行、默认 3 条、30 秒超时、2 MiB 响应上限，不自动重试或翻页。NARA 数据集会读取整个固定小分片，`--rows` 只限制校验后报告的样本数。测试不同来源使用各自默认查询；统一检查不接受跨来源共用的 `--query`。

## 3. 每个平台配置好之后怎样单独复测

下表每条命令均可独立执行。配置文件可以含全部三个 key，各脚本只读取自己需要的变量。

| 来源 | 单条命令 | 通过标准 |
| --- | --- | --- |
| LoC | `python3 tools/access_loc.py --live --query 'Burma Road' --rows 3` | `ok`、`request_sent=true`、退出 0 |
| NDL | `python3 tools/access_ndl.py --live --query 'ビルマ' --rows 3` | 同上，当前限定 NDL 自有书目 |
| NARA 数据集 | `python3 tools/access_nara.py --live --rows 3` | 同上；不传 `--query`，不把样本数当查询总数 |
| Europeana | `python3 tools/access_europeana.py --live --env-file .env.archives --rows 3` | 同上，默认精确短语 `"Burma Road"` |
| DPLA | `python3 tools/access_dpla.py --live --env-file .env.archives --rows 3` | 同上；缺 key 时应明确跳过 |
| NARA Catalog API | `python3 tools/access_nara_catalog.py --live --env-file .env.archives --rows 3` | 同上，确认是 v2 响应；总量下界不显示为精确总量 |
| TNA | `python3 tools/access_tna.py --live --permission-confirmed --rows 3` | 在获批出口 IP 上得到 `ok`、退出 0 |
| JACAR | `python3 tools/access_jacar.py --live` | **当前预期 `manual_only`、退出 2**；实现真正 API 后才改为要求 `ok` |
| IWM | `python3 tools/access_iwm.py --live` | 同上 |

保存执行日期、代码版本、来源 ID、状态及计数即可，不把认证 URL、原始响应、错误正文或 key 加入证据文件。测试结果应标注执行环境；本机成功不能直接替代生产网络验收。

## 4. 获得暂未开放 API 后的开发清单

### DPLA、NARA Catalog API、TNA：现有探针已准备好

1. 配置自己的 key，或确认 TNA 出口 IP 已获批。
2. 先做一次单来源小请求，确认响应与离线 fixture 的结构一致；没有通过就保留“待验证”。
3. 对当前未覆盖的真实结构差异补解析及合成 fixture，再运行 unit tests。真实响应是否可以留作 fixture，按来源条件决定。
4. 抽查资料的标题、稳定 ID、所属机构、日期语义、原馆链接和层级。成功计数不能替代内容核对。
5. 通过后才进入下一节的生产 connector 开发；现有 `access_*.py` 继续保留作诊断入口。

### JACAR、IWM：取得权限后仍有开发工作

| 顺序 | 需要拿到或实现的内容 | 完成条件 |
| --- | --- | --- |
| 1 | 官方 API base URL、版本、认证方式、账号 scope、测试和生产环境 | 有可引用的正式文档或机构提供的接口说明 |
| 2 | 查询、分页、详情、ID、错误码和限流格式；元数据／原件使用条件 | 能确定哪些字段可显示、保存、索引及用于后续研究功能 |
| 3 | 将现有 portal 模块补成真实 `probe()`，更新 `Source` 能力声明 | 不再是 `probe=None`；保留原有 `jacar`／`iwm` source ID |
| 4 | 按真实认证方式补配置模板与加载逻辑 | key、OAuth 或 IP 审批按实际文档实现；不预先虚构变量或端点 |
| 5 | 增加成功、空结果、缺凭据、过期凭据、401/403、429、超时、分页及错误结构测试 | 合成 fixture 的 unit tests 全部通过 |
| 6 | 获权后做一次真实小请求和人工内容核对 | 从 `manual_only` 更新为带日期的“实测通过” |
| 7 | 按下一节选择索引／实时／外链路线，并升级 production connector | 生产数据与网页实际可用后，才标记“已整合” |

现有统一检查器已经注册这两个 source ID。适配器和认证支持完成后可以沿用统一命令；仅填写一个假定的 API key 不会改变现有脚本行为。

## 5. 从访问成功到生产系统：按来源选择数据路线

以下是**建议实施路线，尚未部署**。生产状态要分别记录 `credential_ready`、`live_verified`、`content_verified`、`staging_verified`、`production_enabled`，不能用一个“已接入”覆盖所有阶段。

| 来源／路线 | 生产整合方式 | 还需要完成的来源特有工作 |
| --- | --- | --- |
| LoC | 在所选元数据使用范围确认后，继续构建本地索引；保留原馆链接 | 扩大查询／分页；处理日期区间、类型和在线资源证据；按机构限流 |
| NDL | 对获准的数据提供方同步书目，建立索引 | 保留提供方和许可；日文检索、刊物／书籍类型、出版日期单独处理；不能把所有 NDL 子库视为同一条件 |
| NARA 公开数据集 | 作为可持久化的 NARA 目录来源，分批导入索引 | 选择相关档案组与分片、校验完整性、检测更新、版本化发布；保留 NAID 与层级 |
| Europeana | 按项目用途确认后同步获准元数据，或代理实时查询 | 将开发 personal key 的用途与运营 project key 区分；保留聚合平台和实际持有机构；审阅同名误命中 |
| DPLA | 取得 key 后补记录标准化与检索接入；保存策略按其元数据政策确定 | 映射 `sourceResource`、提供机构与原馆 URL；处理列表／字符串差异、分页和与其他聚合来源的重复关系 |
| NARA Catalog API | 按现有条件规划请求时查询，不写入持久化目录或公共缓存 | 实现 v2 查询／详情；密钥在服务端；保持档案层级及总量精度；不能用 API 抓全库 |
| TNA Discovery | 获批后通过后端做请求时查询；不缓存为本地目录 | 生产固定出口 IP、来源级限流、档案层级字段；失败时提供原馆检索入口 |
| JACAR、IWM | API 获得且验证后，再根据授权选择同步索引或实时查询 | 在正式数据权利和协议确定前保留外链；不把网页入口算作检索数据来源 |

NDL 的使用条件按数据提供方区分；目前 `iss-ndl-opac` 列为 CC BY。见 [NDL 官方提供方清单](https://ndlsearch.ndl.go.jp/en/help/api/provider)。Europeana 运营服务用途按其 [project key 流程](https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key)处理。

NARA Catalog API 与 TNA Discovery 的当前条款要求不要缓存或保存 API 返回内容；因此这里将其默认规划为请求内存中的结果，且不写进 CDN、日志正文、数据库、向量库、问答记忆或研究导出。需要其他用法时先取得明确允许。NARA 的公开数据集是独立路线；不要把两条路径的权利条件互相套用。依据：[NARA API 条款](https://www.archives.gov/research/catalog/help/api)、[TNA API 条款](https://www.nationalarchives.gov.uk/terms-and-conditions/discovery-for-developers-about-the-application-programming-interface-api/)、[NARA 公开数据集](https://www.archives.gov/developer/national-archives-catalog-dataset)。

### 建议的托管架构

```mermaid
flowchart LR
    A[允许保存的目录数据] --> B[托管同步任务]
    B --> C[版本化数据与检索索引]
    C --> D[统一检索服务]
    E[获批的实时 API] --> F[请求内存中的来源适配器]
    F --> D
    D --> G[公开网页]
    G -->|点击访问| H[仅提供外链的原馆入口]
```

先发布托管静态试点也可行：只发布获准公开的 `site/` 数据与资源，继续采用受控的人工更新。需要 DPLA／TNA 等实时结果融合时，再增加托管后端；本地 `tools/serve.py` 是预览服务，不作为生产 API 服务。数据规模需要时再使用托管数据库与搜索索引，不要求先重写现有前端。

## 6. 生产整合的实施步骤与验收

以下步骤均为待办；其中凭据申请由项目负责人完成，工程负责实现及运行验证，内容负责人核对史料相关性、字段与出处。

| 阶段 | 要做什么 | 可验收的结果 |
| --- | --- | --- |
| P0：明确每个来源的边界 | 登记端点、认证、可用 scope、维护人、限流、允许保存字段、实时／索引模式及来源开关 | 每个来源都有独立配置；未获权来源默认不启用 |
| P1：完成 live verification | 依第 2–4 节配置并测试；记录环境、版本和执行时间 | 每个准备启用的来源单独 `status=ok` 且退出 0；保留内容抽查结果 |
| P2：实现生产 connector | 单独实现查询／详情／分页／标准化层，保留 `access_*.py` 作为只输出计数的诊断工具 | 获取到的记录具有稳定 ID、原文标题、持有机构、出处、日期语义、许可与获取时间；来源错误不会变成空结果 |
| P3：接入数据与检索 | 索引来源实现幂等写入、增量／批次更新、审阅排除及版本切换；实时来源只在请求期间保留结果 | 合格新来源能在网页被检索；重复导入不重复增加记录；失败更新保留此前成功版本 |
| P4：托管运行与凭据 | 用托管任务及服务端 Secret 注入环境变量；设置 dev／staging／prod 隔离、TNA 出口 IP、HTTPS、预算和日志脱敏 | 浏览器与发布目录无 key；staging 和 prod 各自验证实际凭据及网络 |
| P5：前端与结果解释 | 接入后端查询接口、每来源状态、分页、访问类型和查询范围；保留原馆外链 | 用户能区分本地快照／实时结果／仅网页入口；单源故障时其他来源仍可用 |
| P6：测试及发布 | 启用 CI、做 staging 集成／内容／端到端测试、灰度启用来源、验证监控和回滚 | 每个启用来源的验收证据齐全；可以单独关闭失败来源或回退公开索引版本 |

### 代码与数据需要补齐的具体内容

- **不要让诊断函数直接承担导入。** 当前 `check_source()` 只允许返回 `sample_count`／`total_results`，会拒绝原始记录字段。生产 connector 应另外实现 `search()`、`fetch_record()`、`normalize()`，只有来源支持时才实现分页或 `list_changes()`；公开数据集使用分片／批次接口。
- **扩展实际发布链路。** 当前 `build_site_data.py` 只识别四个来源快照。新增允许保存的来源时，需要同时扩展来源注册、字段映射、快照 schema、排除规则、前端筛选标签和检索测试。实时来源通过未来后端加入结果，不硬塞进 `catalog.json`。
- **保留来源与档案语义。** 用来源 ID 和原始记录 ID 标识记录；保留提供机构、档案祖先层级、目录日期含义、原馆 URL、元数据与媒体许可、来源更新时间和获取时间。NARA API 与数据集即使命中同一 NAID，也要保留不同访问路线和保存规则。
- **去重不抹去出处。** 聚合平台与原馆可能描述同一材料，保留独立来源描述并建立关系；不按相似标题自动合并。书目、系列、案卷和扫描件不能当作同一层级。
- **分别设计同步和在线请求。** 同步任务按来源限速、有界退避、幂等和断点运行；在线检索使用整体时间预算、受控并行和部分结果返回，不能直接将当前串行、每源最多等待 30 秒的诊断流程搬到用户请求中。
- **按来源控制持久化和降级。** 可保存来源保留最后成功快照及版本；不可保存的实时来源在故障时显示不可用和原馆链接，不使用历史响应缓存，也不把查询正文写入日志。
- **生产 Secret 不依赖本地 Git。** 现有 `--env-file` 要求本机文件受 Git 忽略，容器可能没有 Git。托管环境应直接注入相应进程环境变量；补 key 轮换和权限变更后的复测。
- **观测来源，不记录密钥或原始内容。** 记录状态、耗时、错误类别、请求预算和最后成功时间，提供单来源停用开关。具体阈值在 staging 基线测试后确定。

后续 LLM／研究发布只使用已获得相应处理与保存许可的材料，保留引用与日期／来源语义；只有目录时不能声称读取了全文。它们属于后续阶段，不是本轮“API 接通”的自动结果。

## 7. 测试与上线门槛

已有离线测试为 **141 项 Python + 10 项 JavaScript**，其中 93 项覆盖本次接入模块；这些是既有通过记录，本次只整理文档。运行命令如下：

```sh
# API 接入模块的离线单元测试，不用真实 key、不请求外馆
python3 -B -m unittest discover -s tests -p 'test_a*.py' -v

# 完整 Step 1 测试；HTTP 隔离检查会使用临时本机端口
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/search.test.mjs
```

| 层级 | 何时执行 | 验证内容 |
| --- | --- | --- |
| Unit / contract tests | 每次代码 PR，合成凭据及 fixture | 认证位置、错误分类、字段映射、有效空结果、分页、日期、层级、凭据脱敏 |
| Live smoke | 新 key／scope、出口 IP、端点或解析协议变动后；受控低频执行 | 对明确选择的已启用来源做真实小请求；禁止用无效 key 连续试探 |
| 内容与检索评估 | 新来源进入 staging 时 | 原馆链接、主题相关性、跨语种命中、日期语义、层级及元数据／原件权限；保留一组人工核对的基准查询 |
| Staging 集成测试 | 来源准备上线时 | 同步幂等、分页边界、部分来源失败、索引版本切换、实时结果不落盘、浏览器无法读取 Secret |
| 发布与运维验证 | 灰度启用及回滚演练 | 来源单独停用、版本回退、限流告警、key 轮换和实际生产出口网络 |

生产门槛按**本次启用的来源集合**判断。当前包含两个 portal 的 `--source all --live` 即使七路成功也退出 2，不能机械要求全清单退出 0，也不能用 `|| true` 忽略错误。当前可逐个执行第 3 节单源命令；未来自动化门槛应读取 JSON，要求每个必选来源 `status=ok` 且 `request_sent=true`，其余来源的跳过必须在发布范围中明确列出。

仓库现有 [CI 模板](https://github.com/sf-pacific-war/memory-next/blob/58d62ad4528b19ea7e48ca326ca73df2ae693ecb/ci/demo-tests.yml) 尚未启用，原因是此前推送凭据缺少 `workflow` 权限。维护者按 [启用说明](https://github.com/sf-pacific-war/memory-next/blob/58d62ad4528b19ea7e48ca326ca73df2ae693ecb/ci/README.md) 启用后，离线测试才会自动运行；真实 key 不提供给不受信任的 PR 测试。上述链接指向 `memory-next` PR 中已提供的模板版本。

## 8. 下一步执行清单

| 顺序 | 行动 | 交付物 |
| --- | --- | --- |
| 1 | 获取 DPLA、NARA Catalog key，办理 TNA 出口 IP；整理 JACAR／IWM 未来提供的正式 API 资料 | 凭据存入 Secret／本地忽略文件，清单只写配置状态与文档出处 |
| 2 | 在正确环境运行统一命令，再对未通过来源做单独检查 | 更新带执行日期和环境的验证记录；不将预期结果写成实测结果 |
| 3 | 对拟上线来源确认查询、保存、索引、展示及引用范围 | 每源能力与处理规则、首批上线来源列表 |
| 4 | 优先将已实测且允许保存的来源做稳定静态公开试点 | 经审阅的数据版本、托管网址、HTTPS、发布回滚路径 |
| 5 | 补 DPLA 等记录 connector；按条件加入 TNA／NARA 实时查询 | staging 中可检索的真实记录及逐来源验收证据 |
| 6 | JACAR／IWM 接口明确后实现并验收，再灰度启用 | 正式 API 适配器、测试、运行证据；完成前继续仅作外链 |

操作细节参见 [逐平台接入与测试说明](archive-access.md)；历史实测参见 [接入验证记录](archive-access-validation.md)；页面当前能力参见 [Step 1 README](../README.md)。
