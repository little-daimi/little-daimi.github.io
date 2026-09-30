# 博客园文章迁移报告

迁移时间：2026-09-29T14:13:08.344114+00:00

来源：https://www.cnblogs.com/undefined

## 迁移结果

- 已发现公开文章：14 篇；成功迁移：14 篇。
- 正文代码块：86 个；逐块检查原始代码文本完全保留。
- 正文图片引用：28 次；去重图片：24 张；成功本地化：24 张。
- 文章失败：0；图片失败：0。
- Markdown 渲染比对：passed。
- 保留原始标题、发布时间、更新时间、段落、标题层级、代码语言和来源链接。代码未执行。
- 原站所有已迁移文章未提供分类与标签；根据标题及明确的正文领域补充导航分类。每篇 front matter 的 taxonomy_source 与本报告标明推导依据，original_categories/original_tags 保留原始空值。
- 重复发布的文章保留独立 URL、日期和标题，不自动合并，不删除原站内容。

## 全量覆盖核对

- 首页 2 页：13 篇。
- RSS/Atom：13 篇。
- 月份归档 8 个：13 篇；月份列表标注合计 13 篇。
- 公开 sitemap：14 篇。额外发现 /articles/18827559，已迁移。
- 检查每篇的上一篇/下一篇链接，未遗漏可发现的公开内容。
- 侧栏统计原文：随笔 - 14 文章 - 1 评论 - 5 阅读 - 3924
- 统计中的“随笔 14”比公开随笔索引 13 多 1。所有公开索引及逐月归档均只暴露 13 篇随笔，公开 sitemap 另包含 1 篇文章，共 14 篇。无法据公开页面确认统计差异的原因；可能存在非公开内容或统计滞后，本次不声称迁移了不可发现/私有/草稿内容。

## 可重复执行

```sh
python3 -m pip install -r migration/requirements.txt
python3 tools/migrate-cnblogs.py --offline  # 由已保存源文件重新生成
python3 tools/migrate-cnblogs.py --offline --verify-render  # npm install 后校验渲染结果
python3 tools/migrate-cnblogs.py            # 复用缓存，补齐缺失
python3 tools/migrate-cnblogs.py --refresh  # 重新获取公开源站
```

脚本仅写入 source/_posts/cnblogs-<id>.md、source/images/posts 与 migration，保留其他新文章。缓存中保存原始 HTML、元数据 JSON、RSS、sitemap 和月份归档，以便审计。迁移需 requests、beautifulsoup4、markdownify；Hexo 构建不依赖 Python。

## 文章清单

| 原始日期 | 标题 | 分类 | 代码块 | 图片引用 |
| --- | --- | --- | ---: | ---: |
| 2026-03-18 12:16 | [protobuf-c 自动逆向脚本开发小记...](https://www.cnblogs.com/undefined/p/19733408) | Reverse | 1 | 0 |
| 2026-03-17 14:03 | [[pwn] protobuf学习与逆向](https://www.cnblogs.com/undefined/p/19729318) | Reverse | 14 | 3 |
| 2025-12-31 21:44 | [二0二午](https://www.cnblogs.com/undefined/p/19428486) | Life | 0 | 3 |
| 2025-12-31 19:55 | [2025年终总结](https://www.cnblogs.com/undefined/p/19428317) | Life | 0 | 3 |
| 2025-11-22 00:21 | [RCTF pwn方向题解（缺bbox）](https://www.cnblogs.com/undefined/p/19254887) | Pwn | 8 | 0 |
| 2025-10-11 21:16 | [securityCTF 2025 pwn方向题解](https://www.cnblogs.com/undefined/p/19135998) | Pwn | 7 | 4 |
| 2025-08-18 16:18 | [Lilctf PWN方向全全全全题解！](https://www.cnblogs.com/undefined/p/19044898) | Pwn | 8 | 6 |
| 2025-05-13 23:05 | [BUUCTF WEB入门题小记](https://www.cnblogs.com/undefined/p/18875060) | Web | 7 | 0 |
| 2025-05-09 01:11 | [mini-L2025 PWN方向全题解](https://www.cnblogs.com/undefined/p/18867406) | Pwn | 12 | 0 |
| 2025-05-02 22:35 | [ACTF 部分题的非预期解法（全都是非预期）](https://www.cnblogs.com/undefined/p/18857873) | Pwn | 1 | 0 |
| 2025-04-15 21:29 | [SQCTF pwn方向部分wp](https://www.cnblogs.com/undefined/p/18827574) | Pwn | 9 | 1 |
| 2025-04-15 21:24 | [SQCTF-2025 pwn部分wp](https://www.cnblogs.com/undefined/articles/18827559) | Pwn | 9 | 1 |
| 2025-04-08 19:43 | [XYCTF 2025 pwn方向部分题解](https://www.cnblogs.com/undefined/p/18815248) | Pwn | 9 | 7 |
| 2025-03-11 16:53 | [testBlog](https://www.cnblogs.com/undefined/p/18765503) | Notes | 1 | 0 |

## 同文不同发布记录

- cnblogs-19428486、cnblogs-19428317：正文文字哈希相同，按原文独立保留。
- cnblogs-18827574、cnblogs-18827559：正文文字哈希相同，按原文独立保留。

## 失败项

无。
