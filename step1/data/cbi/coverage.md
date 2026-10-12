# CBI Theater 参考网站盘点 / Reference inventory

来源：[China–Burma–India Theater](https://cbi-theater.com/menu/cbi_home.html)。更新时间：2026-10-12T00:51:26+00:00。

CBI Theater 仅作为查找线索。此工具只请求 HTML 与 robots.txt；不请求、下载或显示该站照片、扫描件、PDF 或其他媒体。
保存的图片 URL、alt/title 和链接文字仅用于溯源；页面正文不保存。图片数量可能包括图标、装饰图片和重复扫描的不同 URL，不能视为已识别的历史物件数量。
照片/文章/实物与官方档案的逐件对应尚未核实；本盘点不能证明来源相同、开放授权或可重用。Demo 预览只能使用另外实际获取的档案平台记录。

| 指标 / Metric | 数量 / Count |
| --- | ---: |
| 首页独立内部页面链接 | 351 |
| 首页链接已请求 / 成功 | 351 / 349 |
| 全部页面已请求 / 成功 | 1200 / 1192 |
| 已发现页面 URL / 尚未请求 | 2693 / 1493 |
| 独立图片 URL（未请求媒体） | 12335 |
| PDF URL（未请求文件） | 93 |
| 多个页面引用的相同媒体 URL | 832 |
| 对外档案平台链接出现次数 | 11 |
| 已验证的逐件档案对应 | 0 |

运行状态：`page_limit`。完整抓取：`false`。
本次限制：最多 1200 个页面、深度 6、请求间隔至少 1.0 秒。
若达到限制、网络失败或中断，`inventory.json` 的 `unvisited_urls`、`frontier` 和各页面 `status` 保留缺口。失败页面不会在恢复抓取时被自动重试。

robots.txt：`not_present`（HTTP 404）。404 表示未提供规则，不代表版权许可。

## 重现与继续

```bash
cd /Users/jingxugao/Documents/sf-pacific-war-harness/step1-discovery
python3 tools/inventory_cbi.py --max-pages 1200 --max-depth 6 --delay 1
# 继续已有队列（例如扩大页面上限）
python3 tools/inventory_cbi.py --resume --max-pages 3000 --max-depth 6 --delay 1
python3 -m unittest discover -s tests -p 'test_inventory_cbi.py'
```

当前包含 14 项离线单元测试，覆盖链接解析、HTML 跳转、robots 限制、媒体排除、请求限速及中断后继续。

下一步：继续未请求 HTML 页面；按题名、人物、日期与官方档案 ID 逐项比对；将候选、确认和无法确认分开；在档案平台授权允许时才使用其官方预览。

数据结构：`menu.json` 为首页目录；`inventory.json` 的 `pages` 为页面访问状态/链接/图片 URL，`assets` 为去重媒体引用，`frontier` 为可恢复队列。所有 URL 只是线索，不能据此声称媒体可访问。
