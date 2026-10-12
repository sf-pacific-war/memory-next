# 档案平台中英文名称对照

核对日期：2026-10-12（UTC）。Step 1 中文文档中的平台名称统一采用 **中文名（英文品牌或缩写）**，英文全称在下表列明。命令、URL、文件名、环境变量及 `source` 值保留代码原值，不翻译。

| 中文名称 | 英文全称／品牌 | 中文文档用法 | 当前代码入口／状态 |
| --- | --- | --- | --- |
| 美国国会图书馆 | [Library of Congress](https://www.loc.gov/) | 美国国会图书馆（LoC） | `loc`；已有独立检查脚本及网页样本 |
| 欧洲数字文化遗产平台 | [Europeana](https://www.europeana.eu/en) | 欧洲数字文化遗产平台（Europeana） | `europeana`；已有检查脚本及网页样本 |
| 美国国家档案与文件管理局，本文常称美国国家档案馆 | [National Archives and Records Administration](https://www.archives.gov/) | 美国国家档案馆（NARA） | `nara` 为公开数据集；`nara_catalog` 为实时目录 API，分别验收 |
| 美国数字公共图书馆 | [Digital Public Library of America](https://dp.la/) | 美国数字公共图书馆（DPLA） | `dpla`；脚本已有，待配置 key 后实测 |
| 英国国家档案馆 | [The National Archives](https://www.nationalarchives.gov.uk/) | 英国国家档案馆（TNA） | `tna`；其 Discovery 目录接口待出口 IP 审批后实测 |
| 日本亚洲历史资料中心 | [Japan Center for Asian Historical Records](https://www.jacar.go.jp/english/) | 日本亚洲历史资料中心（JACAR） | `jacar`；当前仅网页入口 |
| 帝国战争博物馆 | [Imperial War Museums](https://www.iwm.org.uk/) | 帝国战争博物馆（IWM） | `iwm`；当前仅网页入口 |
| 国家发展委员会档案管理局（台湾） | [National Archives Administration, National Development Council](https://www.archives.gov.tw/tw/arctw/274.html) | 台湾档案管理局（Taiwan NAA） | `taiwan`；无凭据的有界 CSV 检查／检索；`Taiwan NAA` 为网页快照来源 |
| 中国第二历史档案馆 | Second Historical Archives of China | 中国第二历史档案馆（SHAC） | 网页来源 `SHAC`；3 条官方展览选件，独立 HTML 检查器 |
| 云南省档案馆 | Yunnan Provincial Archives | 云南省档案馆（Yunnan Provincial Archives） | 网页来源 `Yunnan Archives`；1 条馆藏指南，独立 HTML 检查器 |

“欧洲数字文化遗产平台”是本项目对 Europeana 的说明性中文称谓，不表示它是某一单独的实体档案馆。其他平台也可能提供图书、出版物或聚合目录，不能仅因出现在来源清单中就把所有记录称为战时原始档案。

## 机构名与服务名分开

- **英国国家档案馆（TNA）**是机构；**英国国家档案馆发现目录（Discovery）**是其目录检索服务。
- **美国国家档案馆（NARA）**的公开数据集与实时目录接口（Catalog API）是两条访问路径，凭据和保存规则不能互相套用。
- **台湾档案管理局（Taiwan NAA）**的国家档案资讯网（A+）、机关档案目录查询网（NEAR）与档案资源整合查询平台（ACROSS）是不同入口。区别、英文名及依据见 [台湾来源说明](taiwan-archives.md)。

## 文档维护规则

中文标题、正文、表格、链接文字和命令前的说明采用上表的并列名称，不仅写缩写。例如写“美国国家档案馆（NARA）公开数据集”，读者无需先记住 `NARA` 的含义。

可执行命令与机器标识保持原样。例如 `python3 tools/access_nara.py --live`、`NARA_API_KEY`、`--source nara_catalog` 与网页 `source=NARA` 不能替换为中文。原馆档案标题与原始描述同样保留原文。

当前统一检查器为 **8 个平台、9 条路径**，包括台湾档案管理局（Taiwan NAA）的有界 CSV 路径。清单包括尚不能机器检索的路径；注册到检查清单不等于接通 API。当前网页为 12 个来源机构、59 条记录；只有经导入并重建公开目录的记录才会进入搜索。

相关文档：[逐来源接入检查](archive-access.md)、[关键词与命令](archive-search-commands.md)、[验证记录](archive-access-validation.md)、[生产接入计划](archive-access-production-plan.md)。

大陆精选入口的独立命令为 `python3 tools/check_mainland_sources.py --live --source all`；机构保管方与官方网页发布方分别注明，未接通全馆 API。见[大陆来源说明](mainland-archives.md)。
