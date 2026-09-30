"use strict";
const { stripHTML } = require("hexo-util");
const plain = (value) =>
  stripHTML(
    (value || "")
      .replace(/<td\b[^>]*class="gutter"[^>]*>[\s\S]*?<\/td>/gi, "")
      .replace(/<br\s*\/?>|<\/(?:p|h[1-6]|li|tr|pre)>/gi, " "),
  )
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, " ")
    .trim();
hexo.extend.helper.register("noise_summary", function (post, length = 120) {
  const text = plain(post.description || post.excerpt || post.content);
  return text.length > length
    ? text.slice(0, length).replace(/[,，。;；\s]+$/, "") + "…"
    : text;
});
hexo.extend.helper.register("noise_reading_time", function (content) {
  const text = plain(content);
  const chinese = (text.match(/[\u3400-\u9fff]/g) || []).length;
  const words = text
    .replace(/[\u3400-\u9fff]/g, "")
    .split(/\s+/)
    .filter(Boolean).length;
  return Math.max(1, Math.ceil(chinese / 400 + words / 200));
});
hexo.extend.generator.register("noise-search", function (locals) {
  return {
    path: "search.json",
    data: JSON.stringify(
      locals.posts.sort("-date").map((post) => ({
        title: post.title,
        url: hexo.config.root + post.path,
        date: post.date.format("YYYY.MM.DD"),
        tags: post.tags.map((tag) => tag.name),
        text: plain(post.content),
      })),
    ),
  };
});

hexo.extend.filter.register("after_post_render", function (data) {
  data.content = data.content.replace(/<img\b([^>]*?)>/gi, (tag, attributes) =>
    /\bloading\s*=/.test(attributes)
      ? tag
      : "<img" + attributes + ' loading="lazy" decoding="async">',
  );
  return data;
});
