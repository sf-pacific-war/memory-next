# 各档案平台的 Python 接入与测试

核对日期：2026-10-12（UTC）。覆盖 Step 1 清单中的 **8 个平台、9 种接入方式**；美国国家档案馆（NARA）公开数据集与 Catalog API 分开。每种方式都有独立 `.py` 入口，其中 2 个入口仅提供官方网页及说明。默认只检查本机配置；只有显式添加 `--live` 才会尝试请求支持的外馆接口。

这些脚本用于确认“能否访问及返回结构是否正确”，输出状态和计数，不保存原始 API 响应、档案记录或密钥。它们不会改变网页目前的 10 个来源机构、55 条记录，也不会自动把美国数字公共图书馆（DPLA）／英国国家档案馆（TNA）等加入网页搜索。现有 `fetch_*.py` 仍负责允许持久化来源的元数据获取。

面向后续 API 就绪和生产集成的路线、统一命令预期结果及上线门槛，见 [访问状态与生产整合计划](archive-access-production-plan.md)。

平台中文名、英文全称和缩写见 [名称对照](archive-platform-names.md)。[台湾档案管理局（Taiwan NAA）](taiwan-archives.md)已注册为 `taiwan`，无需 key，已支持官方 CSV 的有界读取、有限别名关键词匹配与快照导入；这不是 A+ 实时检索或影像 API。

## 1. 逐平台清单

“已配置”描述本次测试时的本机状态，不表示新 clone 自带凭据；“已通过”仅指下述小请求，不能证明全部接口或全文访问可用。

| 平台／方式 | 独立脚本（相对本应用目录） | 凭据要求 | 本次配置与实测 | 未满足条件时 |
| --- | --- | --- | --- | --- |
| 美国国会图书馆（LoC） | [tools/access_loc.py](../tools/access_loc.py) | 无需 key | 小请求通过，检查 3 条目录 | 可直接 `--live`；网络错误单独报告 |
| 美国国家档案馆（NARA）公开数据集 | [tools/access_nara.py](../tools/access_nara.py) | 无需 key 或 AWS 账户 | RG 493 固定分片通过，校验后选取 3 条 | 可直接 `--live`；这不是关键词 API |
| 欧洲数字文化遗产平台（Europeana） | [tools/access_europeana.py](../tools/access_europeana.py) | `EUROPEANA_API_KEY` | 使用已有本机 key，小请求通过，检查 3 条候选 | `missing_credential`，不发送请求 |
| 美国数字公共图书馆（DPLA） | [tools/access_dpla.py](../tools/access_dpla.py) | `DPLA_API_KEY` | 未配置；离线测试通过，真实请求未测 | `missing_credential`，不发送请求 |
| 美国国家档案馆（NARA） Catalog v2 | [tools/access_nara_catalog.py](../tools/access_nara_catalog.py) | `NARA_API_KEY`，以 `x-api-key` header 发送 | 未配置；离线测试通过，真实请求未测 | `missing_credential`，不发送请求 |
| 英国国家档案馆（TNA） Discovery | [tools/access_tna.py](../tools/access_tna.py) | 无 key 参数；需要事先申请来源 IP 接入 | 未确认审批；离线测试通过，本次未发送真实请求 | `permission_required`；获批后显式确认 |
| 日本亚洲历史资料中心（JACAR） | [tools/access_jacar.py](../tools/access_jacar.py) | 公开网页可浏览；本实现没有已确认的公开 API | 返回官方入口；仅入口及无请求行为经过测试 | `manual_only`，不冒充 API 接通 |
| 帝国战争博物馆（IWM） | [tools/access_iwm.py](../tools/access_iwm.py) | 公开网页可浏览；本实现没有已确认的公开 API | 返回官方 Collections Search 入口 | `manual_only`，不发送 API 请求 |
| 台湾档案管理局（Taiwan NAA） | [tools/access_taiwan.py](../tools/access_taiwan.py) | 官方 CSV 无需 key；合作 API 条件另行确认 | 有界读取 CSV，在案名、全宗和档号中匹配；独立导入器输出快照 | 无凭据门槛；必须区分部分扫描与全量结果 |

日本亚洲历史资料中心（JACAR）／帝国战争博物馆（IWM）的判断是“本次未确认可接入的官方公开 API”，不是断言机构绝对没有 API。两个脚本提供访问说明和官方链接，不抓取网页或逆向内部接口。

## 2. 一次列出全部状态

在终端进入本应用目录。使用 `memory-next` 仓库时，从仓库根目录执行：

```sh
cd step1
```

若使用原来的 `sf-pacific-war-harness` 工作目录，从该仓库根目录执行 `cd step1-discovery`。下面所有命令均从应用目录运行。

```sh
# 不联网，只检查凭据和接入条件
python3 tools/check_archives.py

# 使用之前已经配置的欧洲数字文化遗产平台（Europeana）文件（不会打印 key）
python3 tools/check_archives.py --env-file .env.europeana

# 显式实测：各来源串行，缺 key／未获批／仅网页入口的来源自动跳过
python3 tools/check_archives.py --live --env-file .env.europeana

# 同一个关键词测试所有平台；表格显示逐来源状态
python3 tools/check_archives.py --live --query 'Flying Tigers' --env-file .env.europeana --rows 3 --format table
```

不带 `--query` 的在线命令使用各 API 默认词，并读取美国国家档案馆（NARA）固定数据集；无需 key 的台湾档案管理局（Taiwan NAA）同时读取有界 CSV 样本。带 `--query` 时，五条支持检索的 API 原样接收同一关键词；台湾 CSV 在本地按有限别名匹配并报告 `effective_queries`。固定美国国家档案馆（NARA）数据集返回 `query_not_supported` 且不请求，两个网页入口返回 `manual_only`。其余跳过和错误也逐来源保留。

`--query '飞虎队'` 同样合法；五条 API 路径不会自动翻译成 `Flying Tigers`，台湾 CSV 仅使用代码中列明的有限别名。可用两种词分别测试，并按机构语言补日文等词；零结果不代表接口不可用。各 API 默认最多请求 3 条，`--rows` 仅支持 1–5。没有查询词的数据集检查仍读取一个约 300 KB 的固定分片，行数只限制检查后报告的样本量。

## 3. 每个平台分别运行

```sh
# 三种免凭据访问：照片 API、固定数据集和有界 CSV
python3 tools/access_loc.py --live --query 'Burma Road' --rows 3
python3 tools/access_nara.py --live --rows 3
python3 tools/access_taiwan.py --live --query '驻印军' --rows 3

# 已有欧洲数字文化遗产平台（Europeana）本地 key
python3 tools/access_europeana.py --live --env-file .env.europeana --rows 3

# 未配置时只报告 missing_credential，不会发出无 key 请求
python3 tools/access_dpla.py --live
python3 tools/access_nara_catalog.py --live

# 英国国家档案馆（TNA）未确认获批：只报告 permission_required
python3 tools/access_tna.py --live

# 网页入口及说明；即使加 --live 也不会伪造 API 请求
python3 tools/access_jacar.py
python3 tools/access_iwm.py
```

每个脚本都支持 `--help`。`check_archives.py --source loc --live` 等价于对应独立入口；`--source all` 为默认值，也接受自定义 `--query`。不传查询词时，API 使用各自默认词。固定美国国家档案馆（NARA）数据集遇到有效 `--query` 会返回 `query_not_supported`，不会悄悄退回到默认数据读取。

## 4. 凭据如何配置

可以使用进程环境变量，也可以显式传入本应用目录内、被 Git 忽略的配置文件。变量优先于文件；程序只解析当前平台的 `KEY=value`，不执行 shell、不展开变量，也不自动查找其他目录的凭据。

新建配置时：

```sh
cp .env.example .env.archives
chmod 600 .env.archives
```

用本地编辑器填入已申请的 key；没有的保持为空。无需为了运行 unit tests 申请任何 key。已有 `.env.europeana` 可以继续使用，不需要复制其中的 key 到聊天、网页或版本库。

| 凭据 | 如何取得 | 有凭据之后 |
| --- | --- | --- |
| `EUROPEANA_API_KEY` | 免费账户的 API key 管理页申请 personal key；用于个人探索和开发测试，运营服务按 project key 流程办理 | `python3 tools/access_europeana.py --live --env-file .env.archives` |
| `DPLA_API_KEY` | 按美国数字公共图书馆（DPLA）官方政策通过自己的邮箱申请；其文档提供 key 注册接口 | `python3 tools/access_dpla.py --live --env-file .env.archives` |
| `NARA_API_KEY` | 联系 `Catalog_API@nara.gov` 申请只读 Catalog API key | `python3 tools/access_nara_catalog.py --live --env-file .env.archives` |
| 英国国家档案馆（TNA） IP 审批 | 联系 `webmaster@nationalarchives.gov.uk`，提供请求来源 IP；这是接入审批，不是 key | 获批后执行 `python3 tools/access_tna.py --live --permission-confirmed` |

`--permission-confirmed` 只记录使用者确认已获批，不会开通权限或绕过服务端限制。本次没有替使用者申请账户或发送邮件。

## 5. Unit tests：覆盖哪些情况

```sh
# 仅新增的接入测试：test_access_* 和 test_archive_access
python3 -B -m unittest discover -s tests -p 'test_a*.py' -v

# 整个 Step 1 的 Python 测试，包含原来的元数据与 HTTP 隔离检查
python3 -B -m unittest discover -s tests -p 'test_*.py' -v

# 原网页搜索逻辑测试，需要 Node.js
node --test tests/search.test.mjs
```

新增 unit tests 完全使用合成凭据、合成响应和 mock transport，**不读取真实 key、不发外部请求**。原有 HTTP 隔离测试会短暂绑定本机端口。

| 场景 | 预期结果／断言 |
| --- | --- |
| 无需凭据的来源 | 不读取凭据；请求参数正确；返回结构经过校验 |
| 需要凭据但没有／为空 | `missing_credential`，确认 transport 未被调用 |
| 已有格式有效的凭据，未加 `--live` | `ready`，不联网；不宣称 key 有效 |
| 已配置凭据并 `--live` | 只向对应官方端点发一次请求，key 位置正确 |
| key 含换行、重复配置、配置文件不受 Git 忽略或越界 | `credential_error`，不联网 |
| 英国国家档案馆（TNA）未确认审批 | `permission_required`，不联网 |
| 日本亚洲历史资料中心（JACAR）／帝国战争博物馆（IWM） | `manual_only`，无论是否 `--live` 均不联网 |
| 台湾档案管理局（Taiwan NAA） CSV | 无需凭据；字段、BOM、繁简别名、重复档号、截断、行数限制与日期语义经过离线测试；部分扫描不提供全库总数 |
| 对美国国家档案馆（NARA）固定数据集传有效查询词 | `query_not_supported`，不下载固定分片、不返回命中数 |
| HTTP 401／403 | `access_denied`，不泄露请求 URL、header 或异常正文 |
| HTTP 429 | `rate_limited`，不自动重试 |
| 超时／DNS 或连接失败 | `timeout`／`network_error`，不当作零结果 |
| HTML 验证页、畸形 JSON/XML、错误 API 结构、响应超限 | `invalid_response` |
| 有效 API 响应确实为空 | `ok` 且 `sample_count: 0`，与错误区分 |
| 重定向或试图向其他主机／路径发请求 | 阻止，不转发凭据 |
| API 将 key 回显在标题或错误中 | 只允许计数进入报告；拒绝额外字段；异常文字不打印 |

API 传输层设 30 秒超时、2 MiB 响应上限；台湾 CSV 为默认 4 MiB 加 1 字节截断检测、200,000 行扫描上限、30 秒网络操作超时与 120 秒读取预算。每来源一次请求，无自动重试、翻页或后台定时任务。人工重复实测建议同一来源至少间隔 5 秒；遇到限流先停止。

## 6. 读懂结果与退出码

默认结果为 JSON，包含 `source`、`access_mode`、`credential_state`、`request_sent`、`status` 和检查时间；成功时包含 `sample_count`，仅在 API 提供明确总数或 CSV 完整扫描时附 `total_results`。台湾 CSV 另报告已扫描行数、观察到的匹配数和是否完整；这些计数不等于全馆总数。统一报告还记录 `mode`（`access` 或 `keyword`）和本次显式 `query`；`--format table` 显示来源、状态、请求是否发送、样本数和总数。未发送请求的来源不显示命中数。原始响应只在内存中解析，报告不包含档案正文、认证 URL 或凭据。

- `credential_state`: `not_required`、`configured`、`missing`、`invalid`、`not_applicable`。
- `status=ready` 只表示配置满足发请求的前提；`status=ok` 才表示本次请求及响应结构检查通过。
- 退出码 `0`：本次要求的检查成功，或无联网要求的正常配置／网页入口说明。
- 退出码 `2`：因缺 key、缺审批、目标不支持关键词或 `--live` 目标只有网页入口而跳过；命令行参数错误也使用 `2`。
- 退出码 `1`：真实请求失败、响应不符或凭据文件配置错误。

统一检查只要有未满足条件的来源就会返回 `2`；这不是脚本崩溃。混合结果中实际错误优先返回 `1`，仍保留每个平台的详细状态。没有匹配资料的有效响应可以返回 `0`。

本次独立实测结果见 [接入验证记录](archive-access-validation.md)。unit test 通过不等于真实账号已获授权，也不代表数据已经加入网页。

## 官方依据

- [美国国会图书馆（LoC） JSON API 请求](https://www.loc.gov/apis/json-and-yaml/requests/)
- [欧洲数字文化遗产平台（Europeana） key 注册与用途](https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key)
- [美国国家档案馆（NARA）公开数据集](https://www.archives.gov/developer/national-archives-catalog-dataset)、[无需 AWS 账户的公开访问](https://registry.opendata.aws/nara-national-archives-catalog/)
- [美国数字公共图书馆（DPLA）请求说明](https://pro.dp.la/developers/requests)、[key 与政策](https://pro.dp.la/developers/policies)
- [美国国家档案馆（NARA） v2 端点和响应示例](https://www.archives.gov/research/catalog/help/api-getting-started)、[接入要求与条款](https://www.archives.gov/research/catalog/help/api)
- [英国国家档案馆（TNA）接入和 API 条款](https://www.nationalarchives.gov.uk/terms-and-conditions/discovery-for-developers-about-the-application-programming-interface-api/)、[搜索接口参数](https://discovery.nationalarchives.gov.uk/API/Help/Api/GET-search-records)
- [台湾档案管理局（Taiwan NAA）国家档案案名清单](https://data.gov.tw/dataset/95315)及[专用导入说明](taiwan-archives.md)
- [日本亚洲历史资料中心（JACAR）官方入口](https://www.jacar.go.jp/english/)、[帝国战争博物馆（IWM） Collections Search](https://www.iwm.org.uk/collections/search)

英国国家档案馆（TNA）和美国国家档案馆（NARA） Catalog API 的响应不缓存为本地目录；现有美国国家档案馆（NARA）持久化导入继续使用另行发布的官方公开数据集。
