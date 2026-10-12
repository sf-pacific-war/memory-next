# 台湾档案管理局（archives.gov.tw）访问验证与接入计划

本文整理 `archives.gov.tw` 的访问渠道、已验证范围、测试方法和生产接入步骤。**CSV 数据可公开访问；Step 1 统一检查器已加入 `taiwan` 入口，但它仅返回 `manual_only`，未实现 CSV 同步、关键词查询或网页目录接入。**

机构为台湾的国家发展委员会档案管理局（官网用字：國家發展委員會檔案管理局），官方英文名为 **National Archives Administration, National Development Council**，可核对[官方组织法英文版](https://www.archives.gov.tw/tw/arctw/274.html)。

验证日期：**2026-10-11**。以下 HTTP 结果来自该日此前完成的检查；增加 `taiwan` 清单入口不重复下载 CSV，也不把历史结果作为本轮自动请求结果。

## 1. 官网、目录与开放数据的区别

| 入口／中英文名称 | 用途 | 凭据和目前状态 |
| --- | --- | --- |
| [档案局官网（National Archives Administration, National Development Council）](https://www.archives.gov.tw/) | 机构信息、档案应用说明、开放数据入口 | 公共网页可访问；不是统一搜索 API |
| [A+ 国家档案资讯网（Archives Access Service, A+）](https://aa.archives.gov.tw/) | 查询该局档案目录、查看档案详情、申请利用 | 可浏览公开目录；会员申请服务与公开浏览是不同功能，影像是否公开需逐条确认 |
| [机关档案目录查询网（Navigating Electronic Agencies’ Records, NEAR）](https://near.archives.gov.tw/) | 查询各机关公布的档案目录 | 目录存在不代表原件由档案局保管；申请利用通常需向档案保管机关办理 |
| [档案资源整合查询平台（Archives Cross Boundaries, ACROSS）](https://across.archives.gov.tw/) | 跨档案馆、图书馆及博物馆的资源发现入口 | 官方介绍的整合查询网站；本项目未验证rename 可供第三方调用的公开检索 API |
| [国家档案案名清单（National Archives Case-title List，英文为本文说明性译名）](https://data.gov.tw/dataset/95315) | 案卷层级标题目录 CSV | 免费、无需 API key；已验证文件访问和表头，可作为本地索引的数据来源 |

三个查询系统的英文名和职责可参见[档案局官方英文介绍](https://www.archives.gov.tw/wSite/public/Attachment/0/f1715659234651.pdf)及[档案应用指南](https://www.archives.gov.tw/wSite/public/Attachment/0/f1715653511448.pdf)。

## 2. 已验证的 CSV 与适用边界

[政府资料开放平台的数据集 95315](https://data.gov.tw/dataset/95315)提供案卷层级清单，说明按年更新、提供至前一年资料，标注免费及「政府資料開放授權條款-第1版」。集成时应保留来源与授权标注；目录的开放授权不能直接推定档案影像也可转载。授权文本见[官方授权条款](https://data.gov.tw/licenses)。

2026-10-11 的实际检查：向官方 CSV 地址发出 GET 请求，得到 **HTTP 200、Content-Type: text/csv**，读取前 **4,096 bytes** 后关闭连接。服务端未返回 `Content-Range`，不能仅靠 Range 请求保证小样本下载，命令需主动限制读取量。以下表头与官方字段说明一致：

```text
序號,全宗名,檔號,案名,資料產製日期
```

可用于检索和展示的字段是全宗名、档号、案名；`資料產製日期` 表示数据产制日期，**不能映射成档案的历史年代**。表头没有完整摘要、全文、档案起止年代或逐条详情 URL。

这次有限读取只证明当时文件可访问且表头符合预期，尚未验证全文件完整性、总记录数、重复记录、战时关键词命中率，也没有获取全文或批量影像。官方年度更新说明不等于本项目已经核实文件内容的最新日期。

## 3. 与中国、缅甸战场的关系

官方[中国驻印军专题](https://art.archives.gov.tw/tw/art/1632.html)介绍 1942 年中国远征军入缅作战后部分部队转入印度整训，以及之后参与缅北反攻和中印公路相关战事；专题列有「駐印軍案」「中華民國駐印軍編制案」。这证明该机构有相关研究资源，**尚不能证明这两条记录已经在本项目的 CSV 样本或网页目录中**。

后续主题验收可使用 `飛虎隊／飞虎队`、`滇緬／滇缅`、`遠征軍／远征军`、`駐印軍／驻印军`、`緬甸／缅甸`、`Burma`、`China Burma India`。这些是待验证的查询词，不是已经获得的命中结果。应结合真实档案年代筛选 1937–1945 年；仅凭关键词也可能命中战后材料。

## 4. 命令行复测

在 Step 1 应用目录中，可以先查看已注册的入口：

```sh
python3 tools/access_taiwan.py
python3 tools/check_archives.py --source taiwan --live --query '飛虎隊' --format table
```

两条命令都返回 `manual_only`，不会发送 API 或 CSV 请求；第二条要求在线查询，因此退出码为 `2`。`--query` 只是记录本次意图，不意味着该来源已经支持检索。在 [A+ 国家档案资讯网（Archives Access Service）](https://aa.archives.gov.tw/)可手动尝试 `飛虎隊` 等繁体词，具体命中需另行核实。

以下命令只依赖 Python 3 标准库，不需要 credential。它请求官方文件、最多读取 4 KB、验证首行并打印状态与列名；不下载整包、不保存档案内容、也不执行关键词搜索。不会自动跟随重定向。

```bash
python3 - <<'PY'
import csv
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

url = "https://www.archives.gov.tw/opendata/" + quote("國家檔案案名清單.csv")
request = Request(url, headers={"User-Agent": "Step1DiscoveryAccessCheck/1.0"})
try:
    with build_opener(NoRedirect).open(request, timeout=30) as response:
        status = response.status
        content_type = response.headers.get_content_type()
        sample = response.read(4096)
except HTTPError as exc:
    code = exc.code
    if exc.fp is not None:
        exc.close()
    raise SystemExit("HTTP error: %s" % code)
except (URLError, TimeoutError, OSError) as exc:
    raise SystemExit("Request failed: %s" % type(exc).__name__)

if status != 200 or content_type != "text/csv":
    raise SystemExit("Unexpected response: %s %s" % (status, content_type))
if b"\n" not in sample:
    raise SystemExit("No complete header within the 4096-byte limit")
# Decode only a complete line, so a cut-off UTF-8 character at the end is harmless.
header_bytes = sample.split(b"\n", 1)[0].rstrip(b"\r")
columns = next(csv.reader([header_bytes.decode("utf-8-sig")]))
expected = ["序號", "全宗名", "檔號", "案名", "資料產製日期"]
if columns != expected:
    raise SystemExit("CSV schema changed; inspect before importing")
print(json.dumps({"status": status, "content_type": content_type,
                  "bytes_read": len(sample), "columns": columns}, ensure_ascii=False))
PY
```

成功时退出码为 `0`；网络失败、响应类型异常或字段变化时为非 `0`。`timeout=30` 是网络操作超时，读取上限是 4 KB。上面的 CSV 命令仍是独立的有界检查；`tools/access_taiwan.py` 和 `tools/check_archives.py --source taiwan` 都不会调用它。

## 5. 实时 API：存在合作案例，公开接入方式待确认

[官方合作交流记录](https://www.archives.gov.tw/tw/arctw/59.html)记载：依据合作协议，曾为国史馆（Academia Historica）提供目录接口，并为促进转型正义委员会（Transitional Justice Commission）提供查询及影像相关接口。这能证明合作接口曾存在；尚不能据此认定有公开自助申请、任何人可调用的实时 API。

目前没有确认供本项目使用的官方 endpoint、认证协议或测试账号。不设置猜测的 API 地址或环境变量，也不把网页路径中的 `API/v1` 当成开发者接口承诺。取得接口后，应先确认文档版本、允许用途、测试与生产权限、认证方式、IP 限制、配额、分页和错误格式，以及目录缓存、公开展示、全文与影像利用范围，再编写适配器和真实请求测试。

## 6. 接入生产系统的下一步

1. **同步与解析：** 新建专门的 CSV 同步任务，设定下载大小、超时及重试上限；记录来源 URL、获取时间、校验和、授权和数据版本。按字段而非列位置解析，保留原始繁体文字。
2. **稳定标识：** 验证档号的唯一性后，以来源命名空间和档号生成 ID；必要时结合全宗。不要把行序号作为跨版本稳定 ID。
3. **补全与搜索：** 增加繁简中文和历史地名别名；档案年代、摘要及详情链接仅从已核实的数据补入，缺失时保持为空。提供来源筛选并保留原文案名。
4. **测试：** 离线覆盖 UTF-8 BOM、繁体字、引号和逗号、缺列、空档号、重复及超大文件；网络模拟覆盖超时、HTML 错误页、字段漂移和下载中断。另设显式开启的有限在线检查，并用人工核验记录测试相关性。
5. **加入 Step 1 检索：** 在已有 `taiwan` 状态入口之外，实现统一记录模型和网页目录构建，验证跨平台搜索、语言切换和缺失字段展示；完成前保持 `manual_only`，不把状态入口视为数据已接入。
6. **托管更新与回滚：** 由托管任务定期检查官方年度发布变化，先构建候选索引，经完整性和数量变化检查后切换；保留上一成功版本、失败告警与回滚入口。实时 API 若获批，再作为另一条独立接入路线验收。

平台全称对照见 [中英文名称表](archive-platform-names.md)。其余来源及测试入口见[访问检查说明](archive-access.md)、[关键词命令](archive-search-commands.md)和[生产接入计划](archive-access-production-plan.md)。
