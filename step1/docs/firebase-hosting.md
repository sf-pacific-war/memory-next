# Firebase Hosting 部署

本应用使用 Firebase Hosting 托管 `site/` 静态文件。项目为 **FTCBI-Digital-Web**，项目 ID `project-864074c6-a2ba-4b47-a1f`，项目编号 `827712857886`。项目映射保存在 `.firebaserc`；路由、缓存、响应头和构建钩子保存在 `firebase.json`。

## 当前公开版本

- [资料发现](https://project-864074c6-a2ba-4b47-a1f.web.app/)
- [专题浏览](https://project-864074c6-a2ba-4b47-a1f.web.app/topics.html)
- [数据来源](https://project-864074c6-a2ba-4b47-a1f.web.app/sources.html)
- 发布于 **2026-10-12 UTC**。首次访问默认 English，可主动切换并保存中文选择。
- 公开目录为 **55 条记录、10 个专题、10 个来源机构**。
- 资料发现与专题卡片的标题／预览直接打开原始出处；“Record notes / 记录说明”提供元数据与获取信息。元数据获取时间仅在有效时间戳存在时显示。
- 18 个线上文件与本地发布产物的 SHA-256 一致；页面、双语检索、JavaScript 模块 MIME、响应头及私有路径 404 均已验证。

顶部临时演示横幅显示实际样本数、机构数与来源更新时间；可关闭，同一标签页会话跨页面保持关闭。横幅开关位于 `site/demo-banner.mjs`；永久页面布局没有统计条。

## 发布内容

发布目录只有 `site/`：三个页面、旧地址兼容跳转、脚本、样式、图标和统一目录 JSON。凭据、`tools/`、`docs/` 及根目录 `data/` 不发布。内部参考清单、对照报告和访问日志不发布；预览由档案机构提供。目录搜索在浏览器执行，不运行云端 Python 服务。

`cleanUrls` 关闭，以保留 `.html` 页面地址；没有 SPA 全路径重写。未找到的路径返回 404。未指纹化文件每次使用前重新验证缓存，`.mjs` 明确使用 JavaScript MIME 类型。

## 本机工具与登录

需要 Python 3.9+ 和兼容 Firebase CLI 的 Node.js。部署配置使用 Firebase CLI **15.33.0** 验证；无需为应用安装前端框架或 Firebase SDK。以下命令在本应用目录执行：

```sh
npm install -g firebase-tools@15.33.0
firebase login
firebase projects:list
```

登录应使用能够管理上述项目的 Google 账户，按 Google 页面完成授权；授权码与令牌不提交到代码或聊天。若 Google Cloud 项目还没有启用 Firebase，先在 Firebase Console 中选择该现有项目并完成服务条款确认；不要另建一个同名项目。

## 本地验证

```sh
python3 tools/build_site_data.py
firebase emulators:start --only hosting --project project-864074c6-a2ba-4b47-a1f
```

打开 `http://127.0.0.1:5105/`、`/sources.html` 和 `/topics.html`。结束时按 Ctrl+C。

## 发布

先确认当前项目的 Hosting 站点和现有内容；不要覆盖不属于本应用的站点。发布命令仅针对 Hosting：

```sh
firebase hosting:sites:list --project project-864074c6-a2ba-4b47-a1f
firebase deploy --only hosting --project project-864074c6-a2ba-4b47-a1f
```

`predeploy` 自动离线重建统一目录 `site/data/catalog.json`，不刷新外馆数据。后续发布使用 CLI 返回的 Hosting URL 验收；当前站点地址保持不变。

验收：三个页面可访问，中英文和筛选可用；统一目录的记录及专题数量与本地一致；`.mjs` 响应类型正确；凭据、工具、原始研究文件和不存在的路径不可访问。既有版本可在 Firebase Console 的 Hosting 发布历史中回滚。

## 运行与费用

Firebase Hosting 提供托管 HTTPS 与 CDN。该应用只使用静态 Hosting，不需要 App Hosting、Cloud Run、数据库或云函数。实际免费额度和超额费用以项目计费方案及官方规则为准；在 Firebase Console 中查看存储和传输用量。

官方文档：[快速开始](https://firebase.google.com/docs/hosting/quickstart)、[Hosting 配置](https://firebase.google.com/docs/hosting/full-config)、[用量与价格](https://firebase.google.com/docs/hosting/usage-quotas-pricing)。
