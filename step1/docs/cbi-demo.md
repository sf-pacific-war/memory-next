# WWII Pacific War：CBI 参考核查与演示指南

核对日期：2026-10-12 UTC。网站品牌统一为 **WWII Pacific War**，中文副标题为“二战太平洋战场”。本次交付保留原来的跨馆检索，新增独立的 **CBI 演示** 页面。

## 数据从哪里来

[CBI Theater 首页](https://cbi-theater.com/menu/cbi_home.html)只是识别题材和材料的参考入口。**不下载、不缓存、不展示该站图片、PDF、音频或视频**；清单仅解析公开 HTML 的标题、链接和媒体 URL 引用，不保留文章正文。页面上的照片、封面预览由档案机构直接提供。

当前演示分为四层，不能混为“全部已经核实”：

| 层次 | 已有内容 | 可以说明什么 |
| --- | --- | --- |
| 参考清单 | 首页 351 个内部页面地址；更深层页面和媒体引用继续按链接发现 | 哪些入口已读、哪些失败、哪些图片或文档仅有 URL，不能证明每个 URL 是独立史料 |
| 人工交叉核查 | 20 条对照，来自 10 个提供方；4 条同一作品、15 条主题相关、1 条待确认 | 出处与判断依据可复核；目前没有宣称同一张图片或同一件实物的 `exact_item` |
| API／公开数据集样本 | 41 条候选：美国国会图书馆（LoC）19、日本国立国会图书馆（NDL）14、欧洲数字文化遗产平台（Europeana）3、美国国家档案馆（NARA）5 | 包含原有 31 条和 10 条新增唯一记录；旧记录保留原获取时间，不伪装为本次重新获取 |
| 接入证据 | 9 个原计划平台、10 种方式的状态报告，另有 4 项公开网页查找 | 区分 API 成功、缺凭据、待审批、固定数据集和网页目录；不是全部平台已接入实时统一搜索 |

最新页数、图片引用数、失败地址、运行边界见 [实时生成的覆盖记录](../data/cbi/coverage.md)。它是有边界的链接清单，不是网站完整备份；图片引用包括标志、装饰图、重复使用的扫描件，不能直接把数量称作“照片／文物数量”。不含未链接材料、CSS 背景、脚本动态资源或 OCR 识别出的内容。

## 本地演示

在本应用目录运行：

```sh
python3 tools/serve.py
```

打开：

- [English demo](http://127.0.0.1:8000/cbi-demo.html?lang=en)
- [中文演示](http://127.0.0.1:8000/cbi-demo.html?lang=zh-CN)

只预览已保存数据不需要 API key。预览图仍需联网访问原档案机构；不可达时显示“档案预览暂不可用”。首页的 31 条目录样本与 CBI 演示的 41 条研究样本独立，不会把未核实的新候选自动加入原检索样本。

建议用 5–7 分钟演示：

1. **飞虎队照片**：打开 NARA 的 P-40 照片（NAID 535531），展示机构原件链接、编号、获取出处与公开图集的权利说明。明确该图是相关材料，尚未证明与 CBI 参考页是同图。
2. **同一作品与版本**：对照美国互联网档案馆（Internet Archive）的《中国袖珍指南》《缅甸袖珍指南》，再看 LoC《印度袖珍指南》。后者为 1944 年修订版，作品对应与版本完全相同是两种结论。
3. **实物与影片**：打开史密森尼学会（Smithsonian Institution）的血幅／飞行队臂章，或英国帝国战争博物馆（IWM）的影片目录。相同物件类型不是同一件实物；某些影片尚未数字化。
4. **跨馆候选**：在档案记录区域输入 `Ledo` 或 `Burma`，切换 LoC／NDL／Europeana／NARA，展开“完整元数据与出处”。展示查询词、真实获取时间、原始描述和权利说明。
5. **检查覆盖与缺口**：在参考清单选择“同一作品”可见 4 条；切换“图片引用”查看未核实条目。页面对应关系不会传递给其中每张图片。标题关键词相似只产生“关键词线索”。
6. **接入证据**：展示来源状态与实际查询日志，包括两次 LoC 超时和 4 条被排除的植物／动物学误命中；公开网页目录与 API 授权分别列出。

人工证据表见 [20 条档案对照](cbi-archival-matches.md)。补充平台查找见 [TNA、JACAR、台湾与 DPLA 网页核查](cbi-platform-web-checks.md)。

## 可复现命令

以下命令均从本应用目录执行。在原工作目录中它叫 `step1-discovery/`，在 `memory-next` PR 中叫 `step1/`。

只重新生成网页数据，不联网：

```sh
python3 tools/build_cbi_demo.py
python3 tools/serve.py
```

查看 API 获取计划，不请求网络、不写数据：

```sh
python3 tools/fetch_cbi_archives.py
```

显式刷新三个 API 的小样本，并保留 NARA 既有公开数据集记录：

```sh
python3 tools/fetch_cbi_archives.py --live --env-file .env.europeana
python3 tools/build_cbi_demo.py
```

每个平台 3 个固定主题、每次默认 3 条、同一轮请求至少间隔 5 秒，无自动翻页；429 后停止该平台。当前 9 个新请求中 7 个成功、2 个 LoC 请求超时。工具会保存可用部分并用退出码 `1` 明示错误，不能把该退出码解释为“没有史料”。未设置 Europeana key 时会明确报告缺凭据。已有更晚的元数据会保留；没有刷新过的记录不改变其获取时间。

统一测试一个关键词：

```sh
python3 tools/check_archives.py --live --query 'China Burma India' --rows 3 --env-file .env.europeana --format table
python3 tools/check_archives.py --live --query 'Flying Tigers' --rows 3 --env-file .env.europeana --format table
python3 tools/access_nara.py --live --rows 3
```

前两条可能因缺 key／待审批／方式不支持关键词而返回 `2`，逐来源表仍有效。NARA 最后一条验证固定公开数据分片，不是关键词搜索。

继续建立 CBI **HTML 元数据**清单（不会请求 CBI 媒体）：

```sh
python3 tools/inventory_cbi.py --resume --max-pages 2000 --max-depth 8 --delay 1
python3 tools/build_cbi_demo.py
```

`--max-pages` 为累计上限，不是本轮追加量。工具保留未访问队列，遵守 robots、限定同站 HTML、检查重定向、请求大小与超时；不执行脚本。页面失败保留状态，恢复时不自动反复请求失败地址。首次运行可去掉 `--resume`；它会重新开始清单，因此已有研究阶段建议使用恢复模式。

## 文件与开放路径

| 文件／路径 | 用途 |
| --- | --- |
| `site/cbi-demo.html` → `/cbi-demo.html` | 双语演示页面 |
| `site/data/cbi-demo.json` → `/data/cbi-demo.json` | 从下面的元数据生成的公共演示快照 |
| `data/cbi/menu.json` | 首页目录地址与标签 |
| `data/cbi/inventory.json`、`coverage.md` | 页面读取状态、媒体引用、未访问队列、覆盖说明 |
| `data/cbi/verified-matches.json` | 人工对照证据、身份判断、原馆链接与权利说明 |
| `data/cbi/archive-records.json` | 官方 API 候选、原有数据集记录、成功／失败查询和排除依据 |
| `data/cbi/access-report.json`、`nara-access-report.json` | 本轮接入实测 |
| `data/cbi/platform-web-checks.json` | 四个补充平台的公开网页查找证据 |

本地 HTTP 服务仍只开放 `site/`，`data/cbi/` 的原始工作文件与 `.env.europeana` 不经 HTTP 开放。源文件会随 PR 作为可审查的元数据研究产物保存；不包含真实 key。

## 测试与下一步

```sh
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

本次 **181 项 Python 测试、20 项前端逻辑测试**通过。新增覆盖包括：CBI 图片不能进入预览、同一作品判断不传递给图片、未爬到的人工核对条目仍进入清单、模糊标题匹配不升级成同件、刷新保留较新元数据、凭据回显不写入文件，以及无网络的元数据解析／爬取边界测试。浏览器另核对品牌、英文／中文、筛选保留、真实原馆图片、移动布局和原有检索。

下一步按证据推进：

1. 恢复清单至剩余链接，并明确网络失败、深度边界、未链接材料；在呈现“全站核查”前完成覆盖审计。
2. 优先给报刊／指南补卷期、版本、页码，给照片补作者、日期、档案编号与画面比对，给实物补 accession／序号。每个判断保存依据，不能用关键词相似代替单件核实。
3. 为已确定来源逐件核对媒体可用性与权利，将有依据的机构缩略图接入；家庭提供的照片和 LIFE 材料需找到持有机构／权利说明，找不到时保留参考入口。
4. 需要实时查询时，补 DPLA／NARA Catalog key、TNA IP 授权及 JACAR／台湾正式数据接入，配置云端凭据、缓存、限流与来源故障提示。
5. 将经过人工批准的候选纳入正式检索索引；保留 reference→archival record→media→rights 的可追溯关系，再发布托管云试点。
