# 接入验证记录

更新日期：2026-10-12（UTC）。此记录区分自动化离线测试与真正的外馆请求；不把未请求的来源算作接通。

## 当前离线测试

Step 1 已通过 **214 项 Python 测试、25 项 Node.js 测试**。Python 中 **120 项匹配接入测试入口**，包括台湾 CSV 的解析、导入和访问检查；其余 94 项为其他元数据、专题目录、内部核查与本地 HTTP 隔离测试。不读取真实凭据、不访问外馆。接入部分如下：

| 测试文件 | 数量 | 重点 |
| --- | ---: | --- |
| `test_archive_access.py` | 37 | 缺／有／无须凭据、字面量配置、审批、HTTP 错误、异常脱敏 |
| `test_access_public.py` | 12 | 美国国会图书馆（LoC）、美国国家档案馆（NARA）公开数据集请求及返回结构 |
| `test_access_restricted.py` | 17 | 美国数字公共图书馆（DPLA）、美国国家档案馆（NARA） v2、英国国家档案馆（TNA）、日本亚洲历史资料中心（JACAR）、帝国战争博物馆（IWM）的请求与跳过行为，以及台湾 CSV 路径的公共声明 |
| `test_access_transport.py` | 11 | 超时、2 MiB 大小上限、重定向、请求端点和次数限制 |
| `test_access_europeana.py` | 6 | 认证参数、成功／空结果／畸形响应、凭据回显隔离 |
| `test_access_cli.py` | 13 | 统一关键词、逐来源跳过、空结果、单源失败、表格／JSON、凭据脱敏及退出码 |
| `test_access_taiwan.py` | 24 | CSV 字段、BOM、截断与引号、重复、有限别名、字节／行边界、部分扫描、本地导入、日期语义与错误处理 |

运行方法见 [接入与测试说明](archive-access.md#5-unit-tests覆盖哪些情况)。测试用虚构 key 模拟 401／403 等错误，不把错误 key 发送给真实机构。

## 既有实际外馆访问（默认查询词）

当前接入路径保留的三项实际请求记录在 **2026-10-11 22:08 UTC** 完成，每个来源只发一次请求，`rows=3`。没有刷新或覆盖已有网页样本；只在内存校验响应，并保留以下运行状态摘要。

| 方式 | 本次状态 | 请求数 | 校验样本数 | 说明 |
| --- | --- | ---: | ---: | --- |
| 美国国会图书馆（LoC）照片 JSON API | `ok` | 1 | 3 | `Burma Road`；无 key |
| 美国国家档案馆（NARA）公开数据集 | `ok` | 1 | 3 | 固定 RG 493 JSONL 分片；不是关键词搜索 |
| 欧洲数字文化遗产平台（Europeana） Search API | `ok` | 1 | 3 | 精确短语 `"Burma Road"`；使用已有本机 key |
| 美国数字公共图书馆（DPLA） | `missing_credential` | 0 | — | 代码及模拟测试已完成；没有实测认证请求 |
| 美国国家档案馆（NARA） Catalog API v2 | `missing_credential` | 0 | — | 独立于已通过的公开数据集；没有实测认证请求 |
| 英国国家档案馆（TNA） Discovery | `permission_required` | 0 | — | 尚未确认来源 IP 获批，本次没有请求 |
| 日本亚洲历史资料中心（JACAR） | `manual_only` | 0 | — | 返回官方入口，不是 API 实测 |
| 帝国战争博物馆（IWM） | `manual_only` | 0 | — | 返回官方入口，不是 API 实测 |

成功表示当时端点可达、响应满足预期结构，不代表主题相关性、全文权限、媒体版权或完整馆藏覆盖已经核实。今后的 key、网络和接口状态可能不同，复测以脚本实际结果为准。

## 当前配置检查的预期结果

仅配置欧洲数字文化遗产平台（Europeana）的 key，运行 `python3 tools/check_archives.py --env-file .env.europeana` 时，预期为 `ready=4`、`missing_credential=2`、`permission_required=1`、`manual_only=2`。这是当前代码的离线预期，不是新的外馆实测；全部 `request_sent=false`，退出码为 `2`。

有效的环境变量优先于凭据文件。新 clone 不自带 key；显式指定不存在的凭据文件会报告 `credential_error`。

## 台湾档案管理局（Taiwan NAA）：有界 CSV 实测与导入

新 CSV 路径无需凭据，统一检查 ID 为 `taiwan`。以下命令在 **2026-10-12 02:45:51.547688 UTC** 完成一次真实请求：

```sh
python3 tools/access_taiwan.py --live --query '驻印军' --rows 3
```

| 字段 | 实测值与含义 |
| --- | --- |
| `status` / `request_sent` | `ok` / `true`；退出码 0 |
| 凭据 | 无 API key、Authorization 或登录 Cookie |
| `bytes_read` | `4,194,305`，即 4 MiB 加 1 字节截断检测 |
| `scanned_rows` | `42,721` 条完整目录行 |
| `matched_count` / `sample_count` | `3` / `3`；在本次扫描范围观察到的匹配及报告样本 |
| `scan_complete` / `source_exhausted` | `false` / `false`；没有扫描完整官方目录 |
| `total_results` | **不提供**，不能将观察到的 3 条解释为全馆只有 3 条 |
| 资料层级 | 案卷标题目录，非 A+ 实时 API、全文或影像访问证明 |

用于演示目录的快照另基于一次较大的官方 CSV 前缀：**14,942,208 字节、147,274 条完整目录行**，`source_exhausted=false`。查询 `驻印军|滇缅|远征军|缅甸` 在该范围观察到 **67 条匹配**，人工挑选其中 **11 条军事主题案卷**进入 `data/taiwan-discovery.json`。67 不是全馆总数，11 不是接口命中总数；完整 CSV 没有存入仓库。

共享网页因此为 **55 条去重记录、10 个来源机构、10 个双语专题**，获取方式为 22 条 API 元数据、16 条公开数据集记录、17 条人工整理记录。台湾 11 条均没有从目录制作日期推断历史日期，原件语言仍未知；只确认目录文字为繁体中文。保留全宗、档号和 A+ 检索入口，两个已核实的驻印军专题页另列为阅读链接，不伪装成全部案卷的单件详情。

早期 **2026-10-11** 的独立 GET 只读取前 4,096 字节，确认 HTTP 200、`text/csv` 与表头 `序號,全宗名,檔號,案名,資料產製日期`。当时没有 `Content-Range`，新脚本主动限制读取量。早期表头验证、上述 CSV 匹配与官方专题页核查是三个不同的证据层级。

字段与更多可复制命令见[台湾来源说明](taiwan-archives.md)，数据集依据见[官方国家档案案名清单](https://data.gov.tw/dataset/95315)。本轮未下载影像、PDF 或全文；合作查询／影像 API 未取得文档、权限或实测。

## 统一关键词的真实测试（2026-10-11）

以下保留 **2026-10-11 的旧版检查器**真实结果，当时台湾来源仍为网页入口。当前台湾 CSV 已接入，见上节，不能将旧表视为当前状态。下表非 mock；每个 API 请求限制 `rows=3`，未保存原始响应或更新网页。计数来自各 API，不代表已经人工确认每条记录与飞虎队相关，也不能相加作为去重后的档案总数。

```sh
python3 tools/check_archives.py --live --env-file .env.europeana --query '飞虎队' --rows 3 --format table
python3 tools/check_archives.py --live --env-file .env.europeana --query 'Flying Tigers' --rows 3 --format table
```

| 平台／路径 | `飞虎队` | `Flying Tigers` | 本次状态及范围 |
| --- | ---: | ---: | --- |
| 美国国会图书馆（LoC） | 0 | 60 | `ok`；照片目录；英文请求校验修复后单独复测 |
| 欧洲数字文化遗产平台（Europeana） | 0 | 5 | `ok`；使用已有本机 key |
| 美国国家档案馆（NARA）公开数据集 | — | — | `query_not_supported`；未下载固定分片 |
| 美国国家档案馆（NARA） Catalog API | — | — | `missing_credential`；未发请求 |
| 美国数字公共图书馆（DPLA） | — | — | `missing_credential`；未发请求 |
| 英国国家档案馆（TNA） | — | — | `permission_required`；未发请求 |
| 日本亚洲历史资料中心（JACAR） | — | — | `manual_only`；未发请求 |
| 帝国战争博物馆（IWM） | — | — | `manual_only`；未发请求 |
| 台湾档案管理局（Taiwan NAA） | — | — | 当时为 `manual_only`；当前 CSV 能力与后续实测另列，不改写历史结果 |

中文统一命令在 **22:46:55–22:47:04 UTC** 执行；表中两个 API 均成功，退出码 `2` 表示仍有跳过来源。英文统一命令在 **22:47:19–22:47:27 UTC** 执行，首次美国国会图书馆（LoC）响应因某条记录采用 `//lccn.loc.gov/...` 目录链接而被旧校验误拒，退出码为 `1`；其他来源继续完成。现在适配器可使用该记录中有效的 `http://www.loc.gov/item/...` 标识完成验证，并有回归测试。**22:48:20 UTC** 仅复测美国国会图书馆（LoC），成功返回 `sample_count=3`、`total_results=60`，退出码 `0`。未为重做整张报告而重复请求其他来源。

上表为中文统一测试、英文统一测试以及修复后单源复测的结果汇总。表中两个 API 的中文／英文词都按原文发送；不自动翻译、不保证短语精确匹配。`0` 表示成功查询但无匹配；`—` 表示没有执行查询。每次运行的最新数字以实际响应为准。
