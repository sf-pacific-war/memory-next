# 内部研究资料与公开专题

公开网站的第二个入口为 **专题浏览 / Topics**。使用步骤、数据维护与演示路径见 [专题浏览指南](topics.md)。旧 `/cbi-demo.html` 地址仅用于兼容跳转。

内部参考清单、匹配证据、访问报告与未处理队列保存在 `data/cbi/`。它们不随网站发布，也不用于声称每张图片或每件实物已经核实。

```sh
# 生成内部核查报告，不联网、不写入 site/
python3 tools/build_cbi_demo.py
# 生成网站共享目录
python3 tools/build_site_data.py
```

内部报告输出为 `data/cbi/review-report.json`，由 Git 忽略。公开构建器只允许原馆记录字段、经过整理的专题和编辑导读进入 `site/data/catalog.json`。不下载、缓存或展示参考站媒体。台湾档案管理局（Taiwan NAA）的公开 CSV 快照位于 `data/taiwan-discovery.json`，独立于 CBI 对照清单；经审阅后进入共享目录。其接入、覆盖限制与官方专题阅读链接见[台湾来源说明](taiwan-archives.md)，不能将新增目录记录算成已确认的 CBI 同图／同物。
