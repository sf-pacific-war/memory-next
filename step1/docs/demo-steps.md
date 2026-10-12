# Step 1：统一发现演示步骤

当前应用提供 **资料发现 / Discover**、**专题浏览 / Topics**、**数据来源 / Sources**。共享目录包含 **55 条去重记录、10 个来源机构、10 个双语专题**，可检索照片、地图、文献、影片与实物记录。搜索在浏览器中的已收录元数据上执行；不实时查询全部外馆，也不需要模型 API、数据库或登录。

## 本地运行

从应用目录执行；`memory-next` 仓库中的目录名为 `step1/`，原工作目录为 `step1-discovery/`：

```sh
python3 tools/serve.py
```

浏览 `http://127.0.0.1:8000/`。端口被占用时使用 `python3 tools/serve.py --port 8001`。启动时离线构建公开目录；只开放 `site/`，不开放凭据或内部源文件。已有样本无需 key 即可预览。

## 演示路径

1. 在“资料发现”搜索 `飞虎队` 或 `Flying Tigers`，查看跨机构结果、关键词扩展与编辑专题标签。
2. 组合来源、资料类型、目录日期与访问状态筛选；打开详情，核对原始描述、编辑导读、原馆链接与权利信息。
3. 切换到“专题浏览”，选择驼峰航线、雷多公路、战时报刊或文物。专题阅读不受此前搜索条件限制。
4. 点击专题关键词或“在资料发现中检索这个专题”，返回对应关键词或完整专题集合。
5. 切换 English／中文；界面和编辑导读随语言切换，原始档案标题与描述保留原文。
6. 在“数据来源”区分 API 元数据、公开数据集和人工整理的原馆记录。检查窄屏布局、无结果恢复与浏览器后退。

专题链接示例：`http://127.0.0.1:8000/topics.html?lang=zh-CN&browse=hump-airlift`。搜索链接示例：`http://127.0.0.1:8000/?lang=zh-CN&q=飞虎队`。本地地址仅能在运行应用的环境访问；公开部署参见 [Firebase Hosting](firebase-hosting.md)。

## 当前目录来源

| 机构 | 公开记录数 | 收录方式 |
| --- | ---: | --- |
| 美国国会图书馆（Library of Congress，LoC） | 22 | 19 条 API 元数据；3 条人工整理记录 |
| 欧洲数字文化遗产平台（Europeana） | 3 | API 元数据，保留实际提供机构与媒体权利 |
| 美国国家档案馆（National Archives and Records Administration，NARA） | 9 | 5 条 RG 493 公开数据集记录；4 条人工整理的官方照片记录 |
| 互联网档案馆（Internet Archive） | 2 | 人工整理的扫描书记录 |
| 史密森学会（Smithsonian Institution） | 3 | 人工整理的文物与文章入口 |
| 美国中央情报局博物馆（CIA Museum） | 1 | 人工整理的文物记录 |
| 帝国战争博物馆（Imperial War Museums，IWM） | 2 | 人工整理的影片目录 |
| 艾克·斯凯尔顿联合兵种研究图书馆（CARL） | 1 | 人工整理的报刊档案线索 |
| 莱斯大学伍德森研究中心（Rice University） | 1 | 人工整理的查找指南 |
| 台湾档案管理局（Taiwan NAA） | 11 | 官方公开 CSV 的案卷标题目录；全宗、档号保留，历史日期未知 |

目录链接不代表全文开放；未数字化影片与尚未确认的媒体访问状态保留在详情中。日期字段来自机构元数据，编辑核查时间与检索获取时间分别记录，不将它们当作历史事件日期。台湾 CSV 的资料产制日期同样不作为历史日期；默认链接进入 A+ 检索。两个已核实的驻印军专题页另标为原馆专题阅读，不冒充每条 CSV 的单件详情或扫描图。不同机构的相似对象不自动合并为同一实物。

## 真实接入测试与更新

接入探针仅返回状态和计数，不会修改网页。统一检查器包含 **8 个平台、9 条路径**；其中 5 条是支持关键词的 API 路径，另有台湾档案管理局（Taiwan NAA）的有界 CSV 匹配。API 是否发出请求取决于凭据与审批；台湾 CSV 无需 key。日本亚洲历史资料中心（JACAR）和帝国战争博物馆（IWM）为网页入口。

```sh
# 无网络：查看配置与访问条件
python3 tools/check_archives.py

# 明确发出有限外馆请求；缺条件的路径报告跳过原因
python3 tools/check_archives.py --live --query 'Flying Tigers' --rows 3 --env-file .env.europeana --format table

# 无需 key 的来源访问检查
python3 tools/access_loc.py --live --query 'Burma Road' --rows 3
python3 tools/access_nara.py --live --rows 3
python3 tools/access_taiwan.py --live --query '驻印军' --rows 3
```

美国国家档案馆（NARA）的固定数据集没有关键词参数；其 Catalog API 是另一条需要凭据的路径。没有 `.env.europeana` 时，去掉文件参数即可检查其他来源。真实 key 只保存在被 Git 忽略的本地配置或进程环境变量，不写入聊天、网页或提交。

需要更新可保存的元数据时，显式运行：

```sh
python3 tools/fetch_public_metadata.py --source loc --rows 20
python3 tools/fetch_nara_metadata.py
python3 tools/fetch_europeana_metadata.py --env-file .env.europeana --query '"Burma Road"' --rows 3 --output data/europeana-discovery-candidates.json
# 台湾 CSV：先导出候选，不覆盖已审阅的演示快照
python3 tools/fetch_taiwan_metadata.py --live --query '驻印军' --rows 20 --output data/taiwan-discovery-candidates.json
python3 tools/build_site_data.py
```

`fetch_*.py` 命令会实际请求外馆并写入指定输出；失败时保留既有快照。台湾候选文件不会自动发布，审阅后才替换 `data/taiwan-discovery.json` 并重建。其部分 CSV 样本不代表全馆覆盖，见[台湾来源说明](taiwan-archives.md)。每个来源低频串行，无自动翻页或重试。主题候选与编辑导读位于 `data/topics.json`；内部核查数据不进入网站。预览只采用允许的档案机构域名，不下载或复用参考站媒体。

## 验收与测试

```sh
python3 -B -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
```

测试使用本地数据、合成凭据与模拟响应，不访问外馆。HTTP 隔离测试会短暂绑定本机端口；Node.js 只用于开发测试，浏览网站无需安装 npm 包。

验收时确认：同一档案不重复显示，搜索和专题记录一致，图像加载失败时有占位提示，编辑导读与原馆描述分开，来源与权利信息可见，凭据与内部研究文件不能从网站访问。自动化测试通过不代表外馆接口或媒体持续可用。

相关说明：[专题浏览](topics.md)、[关键词命令](archive-search-commands.md)、[逐平台接入](archive-access.md)、[验证记录](archive-access-validation.md)、[生产整合计划](archive-access-production-plan.md)。
