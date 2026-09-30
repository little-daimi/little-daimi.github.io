# undefined / imiab

基于 **Hexo 8** 的个人博客，使用仓库内原创主题 **NOISE**。以留白阅读区、实验杂志式整体背景和清晰的文章索引构成界面；桌面与手机均可阅读。

## 运行

使用 Node.js 24（见 `.nvmrc`）：

```sh
npm ci
npm run server
```

打开 http://localhost:4000 。构建静态文件：

```sh
npm run clean
npm run build
npm run check
```

产物位于 `public/`，不提交到 Git。`npm run check` 使用 Python 3 标准库检查所有站内链接、目录锚点、搜索覆盖、Atom 格式及参考图未被发布，也在 CI 中运行。项目无需外部字体、前端框架、图片 CDN 或搜索服务。

## 写文章

```sh
npm run new -- "my-post"
```

编辑 `source/_posts/my-post.md` 的标题、日期、摘要 `description`、分类及标签。文件名建议使用英文以保持 URL 稳定，文章地址为 `/posts/my-post/`。`disableNunjucks: true` 避免代码中的模板语法被 Hexo 执行。图片放入 `source/images/`，使用 `/images/文件名` 引用。

## 设计与功能

- 纸白 `#fbfaf7` 与墨黑 `#191a18` 构成阅读底色；电光蓝 `#1838ed`、青色和少量洋红用于页边拼贴，正文中心不叠加纹理。
- 原创 SVG 页边 `edge-left.svg`、`edge-right.svg` 位于 `themes/noise/source/images/`。右侧保留电路图、青色网点、白色曲线及洋红色标；左侧使用同一套元素重新构图，完全移除电线杆。首页取消大幅封面，直接展示文章。五张参考 PNG 保留在本地项目根目录，不提交 Git，也不复制到构建产物中。
- 装饰区域使用无叙事的字形、符号和叠印，不使用口号或虚构的人物自述。装饰层对屏幕阅读器隐藏，导航、搜索和文章信息保留清晰标签。
- 首页与分页、年度归档、标签索引、分类、关于页、404 页面。
- 本地全文搜索：按标题、标签、正文匹配；`Ctrl/Cmd + K` 打开、`Esc` 关闭。仅在搜索时获取 `search.json`。
- 文章目录、目录定位、阅读进度、代码高亮与复制、相邻文章。
- RSS（`atom.xml`）、站点地图（`sitemap.xml`）、canonical 与 Open Graph 元数据。
- 响应式布局、键盘焦点、跳到正文、减少动态效果偏好及打印样式。
- 页顶外观切换：跟随系统 / 浅色 / 深色。手动选择保存在浏览器本地，首次绘制前应用；正文、代码高亮和 SVG 装饰同步适配。

构图与网络参考见 [设计记录](docs/design-notes.md)。

## 旧站迁移

来源：https://www.cnblogs.com/undefined 。已迁移 **14 篇可发现的公开文章、24 张图片、86 个代码块**，保留原始标题、发布时间、更新时间和原文链接。两组重复发布记录按各自 URL 独立保留。

通过首页分页、RSS、月份归档、sitemap 和相邻文章链接核对覆盖。旧站侧栏计数比公开随笔索引多一条，公开信息不能确认其原因；具体证据、推导标签说明与文件清单见 [迁移报告](migration/report.md)。

原始页面和元数据保存在 `migration/cache/`，迁移脚本不会参与 Hexo 构建。需要复跑时：

```sh
python3 -m pip install -r migration/requirements.txt
python3 tools/migrate-cnblogs.py --offline --verify-render
```

`--offline` 使用已保存来源，`--refresh` 才重新抓取。脚本只重建 `cnblogs-*.md` 迁移文章，不覆盖后续新写的其他文章。

## 修改主题与发布

- `_config.yml`：站点信息、公开 URL、分页、RSS 和 sitemap。
- `themes/noise/layout/`：EJS 页面与组件。
- `themes/noise/source/css/noise.css`：基础排版与阅读样式。
- `themes/noise/source/css/fragments.css`：整体背景、杂志版式、文章层级与响应式构图。
- `themes/noise/source/js/noise.js`：搜索、代码复制与阅读辅助。
- `themes/noise/scripts/helpers.js`：摘要、阅读时间、全文搜索索引生成。
- `themes/noise/scripts/feed.js`：保留代码换行的 Atom 订阅生成。
- `source/about/index.md`：关于页正文；顶部 `awards` 列表维护时间线，每条填写 `date`（如 `2025-12`；仅知年份时填 `2026`）、`name`、`result`，页面自动按年月倒序分组。
- `themes/noise/layout/_partial/awards.ejs`：奖项时间线展示，不展示队伍信息。
- `source/friends/index.md`：友链列表，维护名称、地址、简介、方向、头像（`avatar`）和站点预览图。`themes/noise/source/images/friends/` 保存本地头像和预览图，页面不依赖第三方截图服务。

正式站点地址为 `https://imi-imiab.com`，源码沿用公开仓库 `little-daimi/little-daimi.github.io`。`main` 保存 Markdown、主题和配置，`publish` 只保存通过检查的静态网页。推送 `main` 后，GitHub Actions 自动构建并更新 `publish`；服务器每分钟检查该分支并发布新版本。

源站监听 80 端口；域名在 Cloudflare 中指向服务器 `191.223.210.85` 并开启代理，HTTPS 使用 Cloudflare 的 Flexible 回源方式。

修改文章、关于页或主题后，在仓库根目录提交并推送：

```sh
git add source/ themes/
git commit -m "Update blog content"
git push origin main
```

配置文件或工具也有修改时，将相应文件一起加入提交。也可以在 GitHub 网页直接编辑 `source/_posts/*.md` 并提交到 `main`，同样会触发发布。通过仓库 Actions 页查看构建结果；构建完成后通常一分钟内同步到网站。构建或同步失败时线上继续使用上次成功版本。

远程文件都位于 `/etc/daimi/`：`current` 固定指向 `state/current`；`state/releases/` 保存最近三版静态网站；`state/repo/` 为发布分支缓存；`site.conf`、`bin/`、`systemd/`、`nginx/` 和 `logs/` 分别保存同步配置、脚本、服务配置、Nginx 配置和日志。同步任务使用独立的 `daimi-sync` 用户，仅能写入 `state/`，服务器无需 Node.js，也不执行下载仓库中的代码。

`deploy/bin/daimi-sync`、`deploy/site.conf` 与 `deploy/systemd/` 保存同步任务的配置来源；远程通过 `daimi-sync.timer` 每分钟触发 `daimi-sync.service`。检查同步状态：

```sh
ssh blog 'systemctl status daimi-sync.timer --no-pager'
ssh blog 'journalctl -u daimi-sync.service -n 20 --no-pager'
```

原来的 `tools/deploy-blog.sh` 保留为手工应急工具。自动同步启用时，它会拒绝直接发布，避免绕过 Git 覆盖网站。确有需要时先在服务器停止 `daimi-sync.timer` 和 `daimi-sync.service`，再运行手工脚本；重新启动定时器后网站恢复为 GitHub `publish` 分支的版本。

Nginx 配置源文件为 `deploy/nginx/imi-imiab.com.conf`。配置文件的修改需同步到远程 `/etc/daimi/nginx/imi-imiab.com.conf`，并在 `nginx -t` 通过后 reload；普通文章更新不需要 reload。

日志轮转配置为 `deploy/logrotate/daimi`，远程保存为 `/etc/daimi/logrotate.conf` 并由 `/etc/logrotate.d/daimi` 引用；每天轮转，保留 14 份。

`.github/workflows/pages.yml` 的 `build` 作业构建和检查网页，`publish` 作业更新静态分支；原有 GitHub Pages 部署继续保留。服务器从公开 Git 仓库读取，不需要在 GitHub 保存服务器 SSH 私钥。
