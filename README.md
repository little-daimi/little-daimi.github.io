# undefined · imiab 的博客

地址：https://little-daimi.github.io/

Hexo 8 + NexT Pisces，中文界面，支持深色模式、站内搜索、代码复制、文章目录、标签分类、RSS 和 sitemap。旧文章入口：https://www.cnblogs.com/undefined 。

## 本地使用

建议 Node.js 24（`.nvmrc` 已配置）。

```bash
npm ci
npm run server
```

打开 http://localhost:4000 。

## 写文章与发布

```bash
npm run new -- "my-post"
```

编辑 `source/_posts/my-post.md`，在 front matter 中修改 `title`、`date`、`categories` 和 `tags`。文件名用英文可保持链接简洁；标题可以用中文。在正文中用 `<!-- more -->` 分隔首页摘要。图片放在 `source/images/`，通过 `/images/文件名` 引用。

```bash
npm run build
git add .
git commit -m "Publish new post"
git push origin main
```

GitHub Actions 自动构建并部署，无需本地生成部署分支或配置 SSH 私钥到 Actions。`public/` 不提交。

## 常用配置

- `_config.yml`：站点标题、作者、网址、文章链接、搜索、RSS。
- `_config.next.yml`：主题、导航、社交链接、目录与代码块。
- `source/about/index.md`：关于页面。
- `.github/workflows/pages.yml`：自动部署。

Pages 的发布来源应为 **GitHub Actions**。自定义域名需要同步修改 `_config.yml` 的 `url`、Pages 设置和 DNS。

仅配置新站，尚未迁移博客园历史文章。
