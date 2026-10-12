# WWII Pacific War：CBI 参考页与档案馆记录交叉核查

核查日期：**2026-10-12 UTC**（美国太平洋时间 2026-10-11）。本文件对应 [`data/cbi/verified-matches.json`](../data/cbi/verified-matches.json)，记录原始来源链接、馆藏编号、依据、使用条件及下一步。

本轮整理 **20 条人工核查记录，涉及 10 个档案／馆藏平台**：4 条可以确认同一作品或同一期报纸，15 条仅为相关主题候选，1 条仍待验证。**没有任何记录被标为“已核实同图／同一实物”。** 这些数字指人工挑选的交叉核查条目，不代表全站核查完成，也不等于 10 个自动 API 接口已经接通。

[CBI Theater 网站](https://cbi-theater.com/menu/cbi_home.html)仅作为主题、标题和书目线索。演示页不抓取、不显示该站图片，不复制文章全文。六张可显示的预览分别来自美国国家档案馆（National Archives and Records Administration，NARA）和互联网档案馆（Internet Archive，IA）的原站。

## 匹配状态的含义

| JSON 状态 | 含义 | 可以怎样介绍 |
| --- | --- | --- |
| `same_work` | 两端书目／章节／日期支持同一作品或报刊期次，版次或实物仍可能不同 | “找到了同一作品的另一份馆藏记录”；不要说“找到了相同原件” |
| `exact_item` | 需要图像构图、编号、来源链等足以证明同图或同物的证据 | 本轮没有使用此状态 |
| `related` | 单位、事件、人物、地点或主题相关 | “可补充这个主题的档案候选” |
| `unverified` | 仅有线索，关键出版印记、正文或原件尚未对照 | “下一步需要人工核验” |

## 可用于演示的条目

下表“依据与下一步”是研究者说明；档案标题仍保留原始语言。完整访问限制和权利说明见 JSON 中的 `access_note`、`rights_note`。

| 编号 | CBI 参考线索 | 档案记录与平台 | 材料 | 匹配状态 | 依据与下一步 |
| --- | --- | --- | --- | --- | --- |
| 001 | [Flying Tigers in Burma](https://cbi-theater.com/flyingtigers/index.html) | [A Chinese soldier guards a line of American P-40 fighter planes](https://catalog.archives.gov/id/535531)<br>美国国家档案馆（NARA）<br>`NAID 535531; 208-AA-12X-21` | 照片 | 相关主题候选 | NARA 官方图集确认这是约 1942 年在中国的飞虎队 P-40 战斗机照片；与 CBI 页同属飞虎队主题，尚未确认同图。 演示使用 NARA 记录及说明；核对摄影者、日期与画面构图后，才能声称与 CBI 参考页是同一张照片。 |
| 002 | [The Ledo Road](https://cbi-theater.com/ledoroad/index.html) | [U.S.-built Army trucks on a mountain supply road (original caption: Ledo supply road)](https://catalog.archives.gov/id/535540)<br>美国国家档案馆（NARA）<br>`NAID 535540; 208-AA-45L-1` | 照片 | 相关主题候选 | NARA 以 208-AA-45L-1 及历史上的雷多公路说明收录此运输照片。它是相关后勤素材，尚非 CBI 同图；原始地点说明仍需地理核实。 演示使用 NARA 记录及说明；核对摄影者、日期与画面构图后，才能声称与 CBI 参考页是同一张照片。 |
| 003 | [First Convoy to China](https://cbi-theater.com/destination_china/index.html) | [American and Chinese soldiers place allied flags on a jeep before the first convoy to China](https://catalog.archives.gov/id/535573)<br>美国国家档案馆（NARA）<br>`NAID 535573; 208-AA-338A-1` | 照片 | 相关主题候选 | NARA 标注摄影者 John Gutman 及日期 1945 年 2 月 6 日，内容与雷多至昆明首批车队有关；可互证事件，尚不能证明是 CBI 页所用照片。 演示使用 NARA 记录及说明；核对摄影者、日期与画面构图后，才能声称与 CBI 参考页是同一张照片。 |
| 004 | [The War Ends in Europe](https://cbi-theater.com/VE_Day_LIFE051445/index.html) | [Troops in Burma read the proclamation of victory in Europe](https://catalog.archives.gov/id/531341)<br>美国国家档案馆（NARA）<br>`NAID 531341; 111-SC-262229` | 照片 | 相关主题候选 | NARA 将 Yarnell 摄于缅甸的照片标为 1945 年 5 月 9 日，可展示中缅印战区对欧战胜利的反应；并未确认是 CBI 所转载 LIFE 文章中的照片。 演示使用 NARA 记录及说明；核对摄影者、日期与画面构图后，才能声称与 CBI 参考页是同一张照片。 |
| 005 | [Pocket Guide to China](https://cbi-theater.com/booklet/guide-to-china.html) | [Pocket Guide To China](https://archive.org/details/PocketGuideToChina1943)<br>互联网档案馆（Internet Archive）<br>`PocketGuideToChina1943; ark:/13960/t2h71pv46` | 书册 | 同一作品／报刊期次（非同一实物） | CBI 转录与 IA 目录均指向陆军勤务部指南；IA 标为 1943 年，署名特别勤务处，章节顺序相合。确认同一作品，未确认同一本实物或完全相同版次。 核对版权页、印记及页数后，再确认是否完全同版。 |
| 006 | [Pocket Guide to Burma](https://cbi-theater.com/booklet/guide-to-burma.html) | [A Pocket Guide To Burma](https://archive.org/details/APocketGuideToBurma)<br>互联网档案馆（Internet Archive）<br>`APocketGuideToBurma; ark:/13960/t5k95zz7z` | 书册 | 同一作品／报刊期次（非同一实物） | 两端均为陆军勤务部缅甸袖珍指南；IA 标为 1943 年，习俗、健康与词汇等章节与 CBI 转录对应。未认定为同一本实物。 对照版次、插图和分页，完成版本层级核验。 |
| 007 | [Pocket Guide to India](https://cbi-theater.com/booklet/guide-to-india.html) | [A pocket guide to India](https://www.loc.gov/item/48043776/)<br>美国国会图书馆（LoC）<br>`LCCN 48043776; DS406 .U6 1944` | 书册 | 同一作品／报刊期次（非同一实物） | LoC 收录 1944 年版本，并说明初版于 1943 年；扫描标题页标为 1944 年 4 月修订版，CBI 则署名早期特别勤务处。可认定同一作品，不能直接认定同版。 与 1944 年 4 月修订版核对 CBI 原件印记后，再合并版本。 |
| 008 | [Maps of the CBI Theater](https://cbi-theater.com/maps/index.html) | [Mileage chart for the China-Burma-India theater of war](https://www.loc.gov/resource/afc2001001.86254.pm0004001/?sp=2)<br>美国国会图书馆（LoC）<br>`AFC/2001/001/86254; resource afc2001001.86254.pm0004001` | 地图 | 相关主题候选 | LoC 明确记录 Charles E. Kavenagh 藏集中的中缅印战区里程图，是地图主题的可用线索；尚未与 CBI 参考页任何地图建立同图关系。 核对图名、图幅号、比例尺与版次，并保留藏集和资源编号。 |
| 009 | [Merrill's Marauders in Burma](https://cbi-theater.com/marauders/index.html) | [William Munro Graham Collection](https://www.loc.gov/item/afc2001001.82964/)<br>美国国会图书馆（LoC）<br>`AFC/2001/001/82964` | 个人叙述／回忆 | 相关主题候选 | LoC 记载 Graham 曾在麦支队和第 475 步兵团服役，并提供个人藏集数字页面；可补充个人视角，未声称与 CBI 页回忆录相同。 选定具体日记或照片页，核对作者和日期，再核实展览使用条件。 |
| 010 | [The Hump: Aluminum Trail](https://cbi-theater.com/aluminum_trail/index.html) | [Frank H. Gray Collection](https://www.loc.gov/item/afc2001001.21936/)<br>美国国会图书馆（LoC）<br>`AFC/2001/001/21936` | 个人叙述／回忆 | 相关主题候选 | LoC 服役说明明确写明 Gray 驾驶 C-47 飞越印度至中国的驼峰航线；这是相关亲历资料，并不证明 CBI 的 Aluminum Trail 页面使用了此藏集。 核实录音与转录稿可用性，引用前选定带时间戳的段落。 |
| 011 | [CBI Blood Chits](https://cbi-theater.com/bloodchit/index.html) | [blood chit](https://americanhistory.si.edu/collections/object/nmah_1102530)<br>史密森学会（Smithsonian）<br>`nmah_1102530; catalogue 1991.0840.007` | 器物 | 相关主题候选 | 美国国家历史博物馆收录一件棉布血幅，编号 1991.0840.007；器物类型相同，可作比较，但尚无序号或来源证据证明与 CBI 页某件实物相同。 对照文字语言、序号、尺寸与来源；若需要，再申请图片许可。 |
| 012 | [Flying Tigers in Burma](https://cbi-theater.com/flyingtigers/index.html) | [patch (Fourteenth Air Force)](https://americanhistory.si.edu/collections/object/nmah_1983471)<br>史密森学会（Smithsonian）<br>`nmah_1983471` | 器物 | 相关主题候选 | 博物馆将其识别为第十四航空队蓝色圆形臂章，并区分 1943 年成立的该队与早期美国志愿航空队。它是相关徽章，未认定为 AVG 原件或 CBI 页同物。 区分 AVG 与第十四航空队，核对登记号及来源后再确定是否同物。 |
| 013 | [Flying Tigers in Burma](https://cbi-theater.com/flyingtigers/index.html) | [Hiding in Plane Sight](https://airandspace.si.edu/stories/editorial/hiding-plane-sight)<br>史密森学会（Smithsonian）<br>`NASM editorial; archival photograph SI 90-13683` | 文章 | 相关主题候选 | 博物馆文章介绍飞虎队木制 P-40 诱饵机，并列出档案照片号 SI 90-13683；这是有来源的研究线索，未认定为 CBI 同图或同文。 先将 SI 90-13683 对应到档案图片记录并核查使用条件，再显示预览。 |
| 014 | [CBI Blood Chits](https://cbi-theater.com/bloodchit/index.html) | [Office of Strategic Services Blood Chit](https://www.cia.gov/legacy/museum/artifact/office-of-strategic-services-blood-chit/)<br>美国中央情报局博物馆（CIA）<br>`public museum page: office-of-strategic-services-blood-chit` | 器物 | 相关主题候选 | CIA 博物馆说明这件 20×21 厘米丝质求救血幅供 OSS 在中缅印战区使用；页面未提供馆藏登记号，也未与 CBI 参考页具体实物建立同物关系。 核查博物馆媒体使用条款，并对照文字、图案和来源后，再考虑使用图片。 |
| 015 | [The Ledo Road](https://cbi-theater.com/ledoroad/index.html) | [THE STILWELL ROAD [Main Title]](https://film.iwmcollections.org.uk/record/2992)<br>帝国战争博物馆（IWM）<br>`Film number USA 14; IWM film record 2992` | 影片 | 相关主题候选 | IWM 收录以修筑雷多／史迪威公路和援华运输为主题的美国战时影片；可补充 CBI 公路页面，不应与 Ledo Lifeline 小册子合并为同一作品。 使用 IWM 影片编号核查可播放副本及公开演示片段许可。 |
| 016 | [The Hump: Aluminum Trail](https://cbi-theater.com/aluminum_trail/index.html) | [THE GEN NO 16 [Main Title]](https://film.iwmcollections.org.uk/record/503)<br>帝国战争博物馆（IWM）<br>`Film number GEN 16; IWM film record 503` | 影片 | 相关主题候选 | IWM 对 1945 年 7 月新闻片的说明包括 Dakota 飞越喜马拉雅、昆明卸货及儿童返印；与驼峰主题相关，未认定与 CBI 文章有直接同源关系。 核实相关片卷与时间点；若公开演示影片片段，再确认适用许可。 |
| 017 | [CBI Roundup — January 11, 1945](https://cbi-theater.com/roundup/roundup011145.html) | [Control of theater newspaper "CBI Roundup" — attached issue dated January 11, 1945](https://cgsc.contentdm.oclc.org/digital/collection/p4013coll8/id/2298/)<br>艾克·斯凯尔顿联合兵种研究图书馆（CARL）<br>`CARL p4013coll8/2298; call number N13669; Part 2, pages 14–19` | 报刊 | 同一作品／报刊期次（非同一实物） | CARL 目录明确说明该卷附有 1945 年 1 月 11 日 CBI Roundup 样报；CBI 转录标示同日第三卷第 18 期。元数据支持同一期作品，仍需逐页对照扫描件。 打开第二部分 PDF，核对报头、页码与头条，确认整期内容是否完整一致。 |
| 018 | [Inside Wartime China](https://cbi-theater.com/wartime/index.html) | [Inside Wartime China published by the Chinese Ministry of Information, 1943](https://archives.library.rice.edu/repositories/2/archival_objects/92597)<br>莱斯大学伍德森研究中心（Rice University）<br>`Lowe Family Papers MS 0588; Box 4, Folder 12; archival object 92597` | 书册 | 尚未核实 | 莱斯大学检索目录提供同名册子的出版机关与年份；CBI 菜单虽同名，但未核对 CBI 版权页或莱斯藏本影像，因此作品／版本相同性仍待验证。 先核对 CBI 印记，再向馆方确认目录与扫描件信息；不可将目录开放说成全文在线。 |
| 019 | [Clearing the Burma Road](https://cbi-theater.com/yank-burmaroad/burmaroad.html) | [ああ滇緬公路 : ビルマ従軍](https://ndlsearch.ndl.go.jp/books/R100000002-I000001663142)<br>日本国立国会图书馆（NDL）<br>`NDL R100000002-I000001663142; call number GB554-1548` | 书册 | 相关主题候选 | 既有 NDL 元数据为兴龙会编辑委员会编纂的 1983 年战友出版物；NDL 公开书目亦有记录。它可补充日方缅甸战争视角，与 YANK 战时文章不是同一作品。 补全书目和相关目录，并将 1983 年出版日期与战争事件日期分别记录。 |
| 020 | [Japan Threatens Burma Road](https://cbi-theater.com/life120841/life120841.html) | [La discussion des Trois Amis : le Pacifique ; offensive Rommel ; route de Birmanie ; Japonais à Java](https://www.europeana.eu/item/2051908/data_euscreenXL_ina_PHD85008112)<br>欧洲数字文化遗产平台（Europeana）<br>`Europeana /2051908/data_euscreenXL_ina_PHD85008112; INA PHD85008112` | 音频 | 相关主题候选 | 既有 Europeana API 快照标明这是标题涉及滇缅公路的法国 INA 音频。它是跨语言主题候选，日期与可播放内容尚未核实，不能认定与 LIFE 文章同文同源。 解析 INA 原馆记录，核实录制日期和播放条件，再审查媒体使用许可。 |

## 预览与使用条件

以下六个预览 URL 均从档案机构本身的记录／官方图集链接获得；2026-10-12 UTC 以 `HEAD` 请求检查，均返回 **HTTP 200、image/jpeg**。这里只保存远程 URL 和来源说明，不把参考网站媒体转存到项目。

| 条目 | 预览来源 | 使用依据 |
| --- | --- | --- |
| 001：飞虎队 P-40 | [NARA 官方图集](https://www.archives.gov/research/military/ww2/photos) | 图集说明所选照片属于公有领域，无使用限制；保留 NAID 535531 与 208-AA-12X-21 |
| 002–004：运输车队、首批车队、缅甸欧战胜利消息 | [NARA 官方图集](https://www.archives.gov/research/african-americans/ww2-pictures)及[原站图片链接清单](https://www.archives.gov/files/research/african-americans/ww2-pictures/) | 官方图集将所选照片标为公有领域；原始说明仍需要历史和地理核查 |
| 005：中国袖珍指南 | [IA 原始条目](https://archive.org/details/PocketGuideToChina1943) | 条目显示 Public Domain Mark 1.0；保留扫描与馆藏来源 |
| 006：缅甸袖珍指南 | [IA 原始条目](https://archive.org/details/APocketGuideToBurma) | 条目显示 Public Domain Mark 1.0；保留扫描与馆藏来源 |

需要保留的区别：

- 美国国会图书馆（Library of Congress，LoC）的《印度袖珍指南》扫描版明确为 1944 年 4 月修订版；CBI 转录不应直接与该版合并。
- 美国国会图书馆（LoC）退伍军人历史项目（Veterans History Project，VHP）的口述史、个人照片、日记可能由捐赠者保留版权；可在线读目录并不等于可任意复制。
- 史密森学会（Smithsonian Institution）的血幅与臂章条目标为 Usage Conditions Apply，因此演示只展示目录信息与链接；尚不嵌入其图片。
- 帝国战争博物馆（Imperial War Museums，IWM）的 `USA 14` 影片记录明确标为未数字化、媒体目前不可用；`GEN 16` 列有数字媒体，但片段使用仍依 IWM 条件。
- 欧洲数字文化遗产平台（Europeana）的目录元数据 CC0 与 INA 音频的 In Copyright 是两件事；本轮不显示／播放该音频。
- 莱斯大学伍德森研究中心（Woodson Research Center, Rice University）的记录表示馆藏开放研究且异地存放，没有证据证明全文可以在线获取。没有联系馆方或发送任何消息。

## 平台覆盖与本轮限制

| 平台 | 本轮用到的证据 | 本轮没有证明的能力 |
| --- | --- | --- |
| 美国国家档案馆（NARA） | 官方图集的原始说明、NAID、本地编号、公有领域说明；4 个预览可达 | 不表示搜索 API 已通过，也不表示 CBI 使用同一图片 |
| 互联网档案馆（Internet Archive） | 两本扫描书的原始条目、作者、年份、章节和版权标记 | 未做整本扫描与 CBI 转录逐页比对 |
| 美国国会图书馆（LoC） | 扫描书资源页、地图和 VHP 官方索引记录 | 本环境部分直接条目请求返回 403；索引可读不等于每个终端均能实时访问 |
| 史密森学会（Smithsonian Institution） | 两件器物及一篇博物馆文章的官方索引内容 | 部分直接页面返回 403／520；没有验证 EDAN API 接入或图片许可 |
| 美国中央情报局博物馆（CIA Museum） | 可直接读取的血幅公开记录 | 页面未暴露实物登记号，未建立图片许可 |
| 帝国战争博物馆（IWM） | 两个官方影片目录记录、影片编号与访问说明 | 目录开放不代表影片全部可播放或可截取 |
| 艾克·斯凯尔顿联合兵种研究图书馆（CARL） | 官方索引明确指出卷内附有 1945-01-11 报纸 | 直接查看器本轮超时；未下载 PDF 逐页确认 |
| 莱斯大学伍德森研究中心（Rice University） | 官方索引中的 MS 0588、箱 4／夹 12 书目 | 没有全文，版次仍待核验 |
| 日本国立国会图书馆（NDL） | 既有 API 快照与 NDL 官方发表书目相互印证 | 本轮未读到书籍全文；没有封面许可 |
| 欧洲数字文化遗产平台（Europeana） | 2026-10-10 成功取得的 API 元数据快照，包含 INA 标识符和权利信息 | 本轮特定条目页和 INA 提供者页未渲染；音频访问仍未核实 |

英国国家档案馆（The National Archives，TNA）、美国数字公共图书馆（Digital Public Library of America，DPLA）、日本亚洲历史资料中心（Japan Center for Asian Historical Records，JACAR）及台湾档案管理局（National Archives Administration，archives.gov.tw）未在这份人工清单中确认具体同物记录。不要把“没有加入这 20 条”理解为其无相关馆藏；接口与凭据状态另见项目访问测试文档。

## 本地复核命令

先统计状态，确认没有把相关候选误算为相同照片或器物：

```bash
# 在本应用目录执行（memory-next 仓库中的 step1/）
python3 - <<'PY'
import json
from collections import Counter
from urllib.parse import urlparse
data = json.load(open('data/cbi/verified-matches.json'))
records = data['records']
print('Records:', len(records))
print('Match status:', dict(Counter(r['match_status'] for r in records)))
print('Providers:', len({r['source'] for r in records}))
for record in records:
    preview = record.get('thumbnail_url')
    if preview:
        assert urlparse(preview).hostname in {'www.archives.gov', 'archive.org'}
        print(record['id'], record['source'], preview)
PY
```

预期：20 条；`same_work=4`、`related=15`、`unverified=1`；10 个来源；6 个机构原站预览。

联网检查预览 URL，不请求 CBI 图片，也不下载图片文件：

```bash
# 在本应用目录执行（memory-next 仓库中的 step1/）
python3 - <<'PY'
import json
import urllib.request
data = json.load(open('data/cbi/verified-matches.json'))
for record in data['records']:
    url = record.get('thumbnail_url')
    if not url:
        continue
    try:
        request = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(request, timeout=20) as response:
            print(record['id'], response.status, response.headers.get('Content-Type'))
    except Exception as error:
        print(record['id'], type(error).__name__, str(error))
PY
```

网络检查失败表示当前请求不可达，不能直接推断档案已删除、作品无版权或馆藏不存在。页面可能要求 JavaScript，或对自动请求限流；保留失败时间、错误类型和原链接。

## 下一步：从 demo 到生产系统

1. **完成参考页队列。** 以菜单清单为页面级索引；为每页单独登记实际文章、图像、地图、器物数量，再追踪到页内具体项目。菜单链接数不是实物总数。
2. **提高匹配证据。** 报刊按刊名＋日期＋卷期＋页码，图像按摄影者＋拍摄日期＋底片号＋构图，器物按序号＋尺寸＋材质＋来源链核对。保持“同一作品”“同一版本”“同一件实物”分层。
3. **落实机构接入。** 用现有平台脚本验证查询；只有稳定成功的 API／开放数据路线加入定时刷新。公开网页能访问的机构先作为带来源的人工目录，不假装是自动连接器。
4. **建立逐项权利记录。** 保存元数据许可、媒体许可、署名与获取时间；允许目录展示的记录可以没有预览。生产图片只能从机构允许的来源显示或缓存。
5. **保存可复核依据。** 存原始 JSON 元数据、查询参数、来源时间、版本与人工决定；对失效链接、版次冲突和地名错误显示明确状态。
6. **策展审核后发布。** 优先演示 001 飞虎队照片、003 首批车队照片、005–007 三国袖珍指南、017 报纸期次；再演示 008 地图、011 血幅、015 未数字化影片，以说明不同材料与访问状态。
