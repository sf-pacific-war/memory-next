# 台湾档案管理局（Taiwan NAA）接入、测试与使用边界

台湾档案管理局（National Archives Administration, National Development Council）的公开“国家档案案名清单”已采用 **CSV 元数据路线**：`access_taiwan.py` 检查访问并在有界样本中匹配关键词，`fetch_taiwan_metadata.py` 生成网页目录快照。两者无需注册、API key 或登录。A+ 国家档案资讯网（Archives Access Service）的实时查询／影像 API 尚未接通，CSV 导入不是全馆实时检索。

机构官方用字为“國家發展委員會檔案管理局”；英文全称依据[官方组织法英文版](https://www.archives.gov.tw/tw/arctw/274.html)。检查命令的来源 ID 为 `taiwan`，网页与快照的来源 ID 为 `Taiwan NAA`。

## 访问渠道

| 官方入口 | 用途 | 当前接入与限制 |
| --- | --- | --- |
| [档案管理局官网（National Archives Administration）](https://www.archives.gov.tw/) | 机构资讯、研究文章、开放政策 | 信息入口，不是检索 API |
| [国家档案资讯网 A+（Archives Access Service）](https://aa.archives.gov.tw/) | 国家档案目录、详情、影像及应用申请 | 网页链接；公开目录、会员功能与影像开放是不同权限 |
| [机关档案目录查询网 NEAR（Navigating Electronic Agencies’ Records）](https://near.archives.gov.tw/) | 各机关档案目录 | 分散保管的机关目录，不代表原件均由档案局持有 |
| [档案资源整合查询平台 ACROSS（Archives Cross Boundaries）](https://across.archives.gov.tw/) | 跨机构发现入口 | 未确认供本项目直接调用的公开 API |
| [国家档案案名清单（National Archives Case-title List，说明性译名）](https://data.gov.tw/dataset/95315) | 案卷层级标题目录 CSV | 当前机器读取和关键词匹配路线；免费、无需凭据 |

查询系统的英文名称及职责见[档案局英文介绍](https://www.archives.gov.tw/wSite/public/Attachment/0/f1715659234651.pdf)和[档案应用指南](https://www.archives.gov.tw/wSite/public/Attachment/0/f1715653511448.pdf)。

## 字段与覆盖范围

官方字段为 `序號,全宗名,檔號,案名,資料產製日期`。同步器保留全宗名、完整档号和原始繁体案名，使用全宗与档号的哈希生成记录 ID，不能使用可能重排的行号。**“資料產製日期”是目录制作时间，不是档案年代**；仅凭 CSV 无法确认历史日期时，网页日期保持不详。目录语言为繁体中文，不代表原件语言已知；原件 `language` 保持空值，目录语言单列 `metadata_language`。

CSV 不含完整案情摘要、逐件稳定详情链接、扫描图地址或逐图权利。普通 CSV 记录只提供 A+ 检索入口和档号，`source_url_kind=catalogue_search`；不伪造单件链接，也不标成在线全文。另有经过人工核查的原馆详情链接时，须保留核查依据。

在线读取默认最多 4 MiB 加 1 字节的截断检测，扫描最多 200,000 行；导入器默认导出最多 20 条匹配记录。请求为一次固定官方 CSV GET，无凭据、重定向、重试或媒体下载。报告保留 `bytes_read`、`scanned_rows`、`matched_count`、`scan_complete`、`source_exhausted` 和 `row_limit_reached`。只有完整扫描才报告 `total_results`。**部分样本中的零命中不等于全馆没有相关资料**，输出条数也不是全馆命中总数。

早期 4,096 字节检查只确认匿名 HTTP 200、`text/csv` 和预期表头；服务端没有返回 `Content-Range`，因此程序主动限制读取量。较大样本及新连接器的实际执行证据见[接入验证记录](archive-access-validation.md)。

## 命令行测试与网页更新

在本应用目录执行；`memory-next` 仓库中是 `step1/`，原工作目录是 `step1-discovery/`。

```sh
# 离线预检：不读取外馆，不需要凭据
python3 tools/access_taiwan.py

# 在线有界检查：输出状态与计数，不写入网页
python3 tools/access_taiwan.py --live --query '驻印军' --rows 3
python3 tools/check_archives.py --source taiwan --live --query '飛虎隊' --rows 3 --format table

# 生成候选快照：明确联网，最多输出 20 条匹配记录
python3 tools/fetch_taiwan_metadata.py --live --query '驻印军' --rows 20 --output data/taiwan-discovery-candidates.json

# 使用已有的完整官方 CSV；不联网
python3 tools/fetch_taiwan_metadata.py --input /absolute/path/to/official.csv --query '駐印軍' --rows 20 --output data/taiwan-discovery-candidates.json

# 如果输入文件只是下载前缀，必须标明，不能将文件末尾当成源目录末尾
python3 tools/fetch_taiwan_metadata.py --input /absolute/path/to/partial.csv --partial-input --query '駐印軍|滇緬|中印' --rows 20 --output data/taiwan-discovery-candidates.json
```

`access_*.py` 的 `--rows` 为 1–5，默认 3；导入器的 `--rows` 为 1–100，默认 20。导入器可通过 `--max-bytes`（最多 64 MiB）和 `--max-scan-rows`（最多 1,000,000 行）扩大有界读取。`--query` 支持最多 8 个以 `|` 分隔的 OR 短语及有限的繁简／英文别名，默认 `駐印軍`；这不是任意中文翻译或全文检索。

本地 CSV 可以用 `--fetched-at` 指定有时区的 ISO 获取时间；未提供时保持未知，不把本地文件修改时间当成获取时间。未提供 `--live` 或 `--input` 时只返回就绪状态，不访问文件或网络。

检查候选的档号、主题和覆盖范围后，将选定记录及其获取范围写入 `data/taiwan-discovery.json`，保留已核查的上一版以便回滚。不要直接用查询的前若干条覆盖当前 11 条人工选定的军事主题记录。然后执行：

```sh
python3 tools/build_site_data.py
python3 tools/serve.py
```

```sh
# 浏览器仅检索已收录快照，不实时请求台湾站点
open 'http://127.0.0.1:8000/?lang=zh-CN&q=驻印军&source=Taiwan%20NAA'

# 合成响应与本地数据测试，无需凭据或外网
python3 -B -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
```

## 已核实的中缅印研究入口

以下线索来自直接核对官方 HTML 元数据，与 CSV 命中是独立证据；不能据此声称都在本次 CSV 样本内。没有下载影像或 PDF，也没有认定它们与 CBI 参考站上的照片／实物相同。

| 官方标题与链接 | 完整档号 | 日期与内容 | 访问层级 |
| --- | --- | --- | --- |
| [駐印軍案](https://art.archives.gov.tw/tw/art/1632-15619.html) | `B5018230601/0031/0503/7031` | 展示备忘录为 1944-07-13；中缅印战区总部致何应钦，涉及昆明补充兵员和雨季空运 | 公开专题详情，列出 3 个选件影像链接；未验证媒体读取 |
| [中華民國駐印軍編制案](https://art.archives.gov.tw/tw/art/1632-15618.html) | `B5018230601/0032/583/5000` | 1943 年；驻印军暂行编制表及官兵员额 | 公开专题详情，列出 3 个选件影像链接；未验证媒体读取 |
| [西南邊疆問題處理案](https://art.archives.gov.tw/tw/art/1669.html) | `B5018230601/0035/061.8/1060.4` | 页面事件年为 1945 年；中印公路东段警备司令部滇西边疆视察计划 | 公开中印公路专题及选件说明 |
| [美國援華及救濟事項](https://art.archives.gov.tw/tw/art/1670.html) | `A303000000B/0030/452.2/0019` | 1941 年；驻西雅图领事报告美国援华救济组织协调 | 公开专题及选件说明 |
| [American Aid to China 美國援華](https://aa.archives.gov.tw/ELK/SearchDetailed?FullPath=C3260603001%2F0036%2F0001%2F001) | `C3260603001/0036/0001/001` | **目录日期 1947-01-15**；内容回顾援华、滇缅公路、铁路与空运，不能将战时主题当作目录年代 | 公开 A+ 单件目录，列出 82 页数字影像；批量下载界面有验证码，未验证逐页媒体 |

最后一件记录注明美国国家档案馆（NARA）出处 `RG 226; NND750140; NM54 entry 8; BOX 1; ARC 6037564`，台湾物件号 `T2014000200192`。这种出处关系可供跨馆核查，不能仅凭相近标题认定同一实体件。补充入口包括[中国驻印军](https://art.archives.gov.tw/tw/art/1632.html)、[中缅印航空线](https://art.archives.gov.tw/tw/art/1667-15684.html)（档号 `A303000000B/0030/042.2/0001`，事件年 1941）及[缅甸禁运限运](https://art.archives.gov.tw/tw/art/1668.html)。

档号中的民国年份与选件事件日期可能不同，例如 `0031` 不能直接覆盖《駐印軍案》选件的 1944 年日期。正文、目录日期、选件日期与编辑核查日期应分开保存。

## 元数据与影像的使用条件

“国家档案案名清单”按[政府资料开放授权条款第 1 版](https://data.gov.tw/license)提供。数据集许可适用于该公开目录，不自动覆盖 A+ 影像、第三方图片或其他全文。

官方专题页链接的[政府网站资料开放宣告](https://www.archives.gov.tw/tw/arctw/625-10226.html)采用 CC BY 4.0，并要求署名；另有特别标记的第三方图片、影音和文字等例外。当前可以记录“网站权利政策已核实”，单件影像仍应保持“逐件权利待审”。目录公开、列有扫描图、技术上能显示影像与可以重新发布，是不同判断。

演示保留官方标题、档号、全宗与出处链接。没有逐件权利和媒体证据时，不把台湾记录显示为有可复用预览图或完整数字全文。

## 生产接入下一步

1. **扩大并验证覆盖：** 有界快照不等于完整同步。生产任务需要受控的完整获取或官方增量机制、校验和、行数／重复监测、版本记录与失败回滚；不能将截断快照当成完整新版本覆盖旧索引。
2. **保留字段语义：** 原始繁体标题、全宗、完整档号和资料制作日期分开保存；确认来源后才能补档案年代、稳定单件链接或摘要。
3. **检索验收：** 对“驻印军／駐印軍”“滇缅／滇緬”“飞虎队／飛虎隊”等词验证别名规则，记录原始词、实际扩展词、扫描范围和样本数；区分案卷标题匹配与全文检索。
4. **托管发布：** 以受控构建任务更新快照，运行解析、去重、来源、日期与公开字段测试，再发布静态目录；显示更新时间及覆盖限制，保留上一可用版本。
5. **影像与合作 API：** [官方合作说明](https://www.archives.gov.tw/tw/arctw/59.html)记载对合作机构提供过查询／影像服务，本项目尚未取得接口文档或授权。取得正式条件后另建适配器及测试；不推测端点、认证方式或环境变量，也不绕过登录／验证码。
