# WWII Pacific War：补充公开网页检索路线

检查时间：**2026-10-12 00:33:45 UTC**。数据文件：[`data/cbi/platform-web-checks.json`](../data/cbi/platform-web-checks.json)。本文件补充英国、日文及中文资料入口，并与 API 连通性测试分开记录。

本轮识别 **3 条官方目录记录、1 篇官方研究文章**。检索依据是官方站点的可检索内容，同时对四个直接 URL 做了 `HEAD` 检查。没有下载扫描影像、影片或 PDF 文件，没有注册账户或使用新凭据，也没有认定任何项目与 CBI 参考网站上的照片或实物完全相同。

| 平台 | 本轮结果 | 可定位的线索 | 访问限制与下一步 |
| --- | --- | --- | --- |
| 英国国家档案馆（The National Archives，TNA） | `public_record`：官方档案目录 | [缅甸皇家工兵 177 CRE Works](https://discovery.nationalarchives.gov.uk/details/r/C952223)，Discovery ID `C952223`，档号 **WO 172/7849**，1945 年 1–12 月 | 目录明确说明未数字化、不可下载。索引内容可读；直接 `HEAD` 返回 202，网页工具遇缓存缺失。需要完整档案时使用馆方到馆／复制服务，不能称其全文已在线。 |
| 日本亚洲历史资料中心（Japan Center for Asian Historical Records，JACAR） | `public_record`：官方档案目录 | [缅甸等地区电报卷第 5 部分](https://www.jacar.archives.go.jp/das/meta/C12122376900)，参考号 **C12122376900**；防卫省防卫研究所索书号 **中央-作戦指導重要電報-90** | 官方元数据摘要涉及缅甸航空作战。`HEAD` 返回 200 HTML；未测试逐页影像查看器或自动 API 搜索。下一步核对相关画幅和日期，保留原馆索书号。 |
| 台湾档案管理局（National Archives Administration, Taiwan） | `public_article`：官方研究文章，非目录 API | [《虎翔天际：Flying Tiger》官方 PDF，标题略写](https://www.archives.gov.tw/wSite/public/Attachment/0/f1717664345611.pdf) | `HEAD` 返回 200 PDF，网页工具获取全文超时；仅使用官方索引中的标题线索与档号。下一步在[国家档案资讯网](https://aa.archives.gov.tw/ELK/AdvSearch)逐件检索下列档号，再核对在线影像及使用条件。 |
| 美国数字公共图书馆（Digital Public Library of America，DPLA） | `public_record`：聚合目录记录 | [U.S. TROOPS ON ALASKAN FRONT [ETC.]](https://dp.la/item/26d3b44f2299cc1e6b6e8da45178a394)，DPLA ID **26d3b44f2299cc1e6b6e8da45178a394** | 官方记录描述 1942 年新闻片，内容包括飞虎队任务前准备，提供者为美国国家档案馆（NARA）电影部门。索引可读；直接网页工具返回 403，`HEAD` 返回 202。下一步在浏览器跟进原馆链接、取得 NAID，再验证播放与权利。 |

台湾档案管理局（National Archives Administration, Taiwan）文章中的三个具体检索线索：

| 文中档号 | 文中案名 | 当前证据层级 |
| --- | --- | --- |
| `0026/152.1/2320` | 外籍空軍志願隊參加抗日戰史 | 官方文章引用，未取得单件目录返回 |
| `0031/107.9/8043` | 美自願軍歸建移交案 | 官方文章引用，未取得单件目录返回 |
| `0033/544.2/8043` | 美十四航空隊在華戰果統計表 | 官方文章引用，未取得单件目录返回 |

文章索引 OCR 对完整标题中的一个字出现不一致，因此这里只使用略写标题，不把 OCR 当作精确转录。保留 PDF 原链接以供人工核对。

## 怎样用于演示

- **公开目录记录**：可以展示机构、标题、档号和相关性说明。没有确认完整影像可用的条目，按钮只链接原馆。
- **公开研究文章**：作为研究入口及档号指针，明确标为文章，不能伪装成档案单件。
- **API 状态**：四条记录均设置 `api_verified: false`，表示本项网页检查没有验证 API；实际 API 测试结果应读取独立的访问报告。
- **HTTP 状态**：200 的 `HEAD` 只证明该请求获得相应类型的响应；202、403 或搜索索引命中都不等于已获取有效正文、成功检索或可下载原件。

## 本地重新检查

以下命令只读取响应头，不获取媒体正文，也不需要 API key：

```bash
# 在本应用目录执行（memory-next 仓库中的 step1/）
python3 - <<'PY'
import json
import urllib.request

with open('data/cbi/platform-web-checks.json') as source:
    checks = json.load(source)['platforms']
for item in checks:
    request = urllib.request.Request(item['url'], method='HEAD')
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(item['source'], response.status,
                  response.headers.get('Content-Type'), item['record_id'])
    except Exception as error:
        print(item['source'], type(error).__name__, str(error))
PY
```

需要展示真实搜索结果时，仍应调用项目中的各平台访问脚本。网页能被搜索引擎索引、目录可以人工打开、API 可以自动调用、原件可以在线浏览，是四个不同的检查结果。
