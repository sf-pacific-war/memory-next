# 接入验证记录

验证日期：2026-10-11。此记录区分自动化离线测试与真正的外馆请求；不把未请求的来源算作接通。

## 离线测试

Step 1 共 **141 项 Python 测试**，其中 **93 项为本次新增的接入检查测试**，48 项为已有元数据与本地 HTTP 隔离测试。全部通过；不读取真实凭据、不访问外馆。新增部分如下：

| 测试文件 | 数量 | 重点 |
| --- | ---: | --- |
| `test_archive_access.py` | 37 | 缺／有／无须凭据、字面量配置、审批、HTTP 错误、异常脱敏 |
| `test_access_public.py` | 17 | LoC、NDL、NARA 公开数据集请求及返回结构 |
| `test_access_restricted.py` | 17 | DPLA、NARA v2、TNA、JACAR、IWM 的请求与跳过行为 |
| `test_access_transport.py` | 11 | 超时、2 MiB 大小上限、重定向、请求端点和次数限制 |
| `test_access_europeana.py` | 6 | 认证参数、成功／空结果／畸形响应、凭据回显隔离 |
| `test_access_cli.py` | 5 | 独立入口、统一清单、跳过来源、CLI 脱敏和退出码 |

运行方法见 [接入与测试说明](archive-access.md#5-unit-tests覆盖哪些情况)。测试用虚构 key 模拟 401／403 等错误，不把错误 key 发送给真实机构。

## 实际外馆访问

四次实际请求在 **2026-10-11 22:08 UTC** 完成，每个来源只发一次请求，`rows=3`。没有刷新或覆盖已有网页样本；只在内存校验响应，并保留以下运行状态摘要。

| 方式 | 本次状态 | 请求数 | 校验样本数 | 说明 |
| --- | --- | ---: | ---: | --- |
| LoC 照片 JSON API | `ok` | 1 | 3 | `Burma Road`；无 key |
| NDL OpenSearch | `ok` | 1 | 3 | `ビルマ`，限定 `iss-ndl-opac`；无 key |
| NARA 公开数据集 | `ok` | 1 | 3 | 固定 RG 493 JSONL 分片；不是关键词搜索 |
| Europeana Search API | `ok` | 1 | 3 | 精确短语 `"Burma Road"`；使用已有本机 key |
| DPLA | `missing_credential` | 0 | — | 代码及模拟测试已完成；没有实测认证请求 |
| NARA Catalog API v2 | `missing_credential` | 0 | — | 独立于已通过的公开数据集；没有实测认证请求 |
| TNA Discovery | `permission_required` | 0 | — | 尚未确认来源 IP 获批，本次没有请求 |
| JACAR | `manual_only` | 0 | — | 返回官方入口，不是 API 实测 |
| IWM | `manual_only` | 0 | — | 返回官方入口，不是 API 实测 |

成功表示当时端点可达、响应满足预期结构，不代表主题相关性、全文权限、媒体版权或完整馆藏覆盖已经核实。今后的 key、网络和接口状态可能不同，复测以脚本实际结果为准。

## 本地状态清单复核

使用现有 `.env.europeana` 执行不带 `--live` 的统一检查，得到：

```json
{
  "ready": 4,
  "missing_credential": 2,
  "permission_required": 1,
  "manual_only": 2
}
```

这次清单检查的所有 `request_sent` 都为 `false`，退出码为 `2`，表示有待满足的接入条件。Europeana 的 `configured` 来自显式本地配置文件；新 clone 没有该文件时会显示 `missing_credential`。
