# 接入验证记录

验证日期：2026-10-11。此记录区分自动化离线测试与真正的外馆请求；不把未请求的来源算作接通。

## 当前离线测试

Step 1 共 **188 项 Python 测试**，其中 **96 项为接入检查测试**，92 项为元数据、专题目录、内部核查与本地 HTTP 隔离测试。全部通过；不读取真实凭据、不访问外馆。接入部分如下：

| 测试文件 | 数量 | 重点 |
| --- | ---: | --- |
| `test_archive_access.py` | 37 | 缺／有／无须凭据、字面量配置、审批、HTTP 错误、异常脱敏 |
| `test_access_public.py` | 12 | 美国国会图书馆（LoC）、美国国家档案馆（NARA）公开数据集请求及返回结构 |
| `test_access_restricted.py` | 17 | 美国数字公共图书馆（DPLA）、美国国家档案馆（NARA） v2、英国国家档案馆（TNA）、日本亚洲历史资料中心（JACAR）、帝国战争博物馆（IWM）、台湾档案管理局（archives.gov.tw）的请求与跳过行为 |
| `test_access_transport.py` | 11 | 超时、2 MiB 大小上限、重定向、请求端点和次数限制 |
| `test_access_europeana.py` | 6 | 认证参数、成功／空结果／畸形响应、凭据回显隔离 |
| `test_access_cli.py` | 13 | 统一关键词、逐来源跳过、空结果、单源失败、表格／JSON、凭据脱敏及退出码 |

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

仅配置欧洲数字文化遗产平台（Europeana）的 key，运行 `python3 tools/check_archives.py --env-file .env.europeana` 时，预期为 `ready=3`、`missing_credential=2`、`permission_required=1`、`manual_only=3`。这是当前代码的离线预期，不是新的外馆实测；全部 `request_sent=false`，退出码为 `2`。

有效的环境变量优先于凭据文件。新 clone 不自带 key；显式指定不存在的凭据文件会报告 `credential_error`。

## 台湾档案管理局（archives.gov.tw）的独立访问验证

2026-10-11 在前一轮来源调研中对官方“国家档案案名清单”CSV 做了有界 GET；本轮只把既有结果写入文档，没有重新请求或下载目录。详见 [台湾来源总结](taiwan-archives.md)和 [官方数据集说明](https://data.gov.tw/dataset/95315)。

| 项目 | 已观察到的结果／边界 |
| --- | --- |
| 凭据 | 未提供 API key、Authorization 或登录 Cookie |
| 响应 | HTTP `200`、`Content-Type: text/csv` |
| 读取量 | 只读取前 `4096` 字节后关闭连接；未下载完整清单 |
| 表头 | `序號,全宗名,檔號,案名,資料產製日期` |
| Range | 服务端未返回 `Content-Range`，不能依赖 Range 限制读取量；复测命令主动限制 `read()` |
| 证明范围 | URL 可匿名读取且头部为预期 CSV；没有校验全量目录、关键词结果、影像权限或生产稳定性 |
| 当前代码状态 | 已新增 `access_taiwan.py` 和 `--source taiwan`，仅返回 `manual_only`；未实现 CSV 检索或 API。尚未导入网页，不计入上面的三项脚本 `ok` |
| 实时 API | 有官方合作案例，当前项目未取得接口资料或凭据，未发起实时 API 请求 |

“资料产制日期”是目录数据的制作时间，不等于档案历史年代。官方专题中的中缅印相关档案示例，与此 CSV 前缀验证属于两种证据，不能据此宣称已从 CSV 检索出这些档案。


## 统一关键词的真实测试（2026-10-11）

当前检查器共 8 个平台、9 条路径，新增 `--query` 同词检查和 `--format table`。以下为真实请求结果，非 mock；每个 API 请求限制 `rows=3`，未保存原始响应或更新网页。计数来自各 API，不代表已经人工确认每条记录与飞虎队相关，也不能相加作为去重后的档案总数。

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
| 台湾档案管理局（archives.gov.tw） | — | — | `manual_only`；未发请求，不检索 CSV |

中文统一命令在 **22:46:55–22:47:04 UTC** 执行；表中两个 API 均成功，退出码 `2` 表示仍有跳过来源。英文统一命令在 **22:47:19–22:47:27 UTC** 执行，首次美国国会图书馆（LoC）响应因某条记录采用 `//lccn.loc.gov/...` 目录链接而被旧校验误拒，退出码为 `1`；其他来源继续完成。现在适配器可使用该记录中有效的 `http://www.loc.gov/item/...` 标识完成验证，并有回归测试。**22:48:20 UTC** 仅复测美国国会图书馆（LoC），成功返回 `sample_count=3`、`total_results=60`，退出码 `0`。未为重做整张报告而重复请求其他来源。

上表为中文统一测试、英文统一测试以及修复后单源复测的结果汇总。表中两个 API 的中文／英文词都按原文发送；不自动翻译、不保证短语精确匹配。`0` 表示成功查询但无匹配；`—` 表示没有执行查询。每次运行的最新数字以实际响应为准。
