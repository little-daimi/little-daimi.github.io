"use strict";

const { stripHTML, unescapeHTML } = require("hexo-util");

// XML 1.0 permits tabs and line breaks, but not other control characters.
const xmlText = (value) =>
  String(value == null ? "" : value).replace(
    /[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}]/gu,
    "",
  );
const escapeXML = (value) =>
  xmlText(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
      })[character],
  );
const cdata = (value) =>
  "<![CDATA[" + xmlText(value).replace(/\]\]>/g, "]]]]><![CDATA[>") + "]]>";
const asDate = (value) => {
  const date =
    value == null
      ? new Date(NaN)
      : new Date(Number.isFinite(Number(value)) ? Number(value) : value);
  return Number.isFinite(date.getTime()) ? date : null;
};

hexo.extend.generator.register("noise-atom", function (locals) {
  const config = hexo.config;
  if (!config.feed) return [];

  const feed = config.feed;
  const feedPath = String(feed.path || "atom.xml").replace(/^\/+/, "");
  const site = new URL(config.url);
  // Support both Hexo's explicit root and a subdirectory in the site URL.
  if (config.root && config.root !== "/") site.pathname = config.root;
  site.pathname = site.pathname.replace(/\/?$/, "/");
  site.search = "";
  site.hash = "";
  const siteURL = site.href;
  const rootPath = site.pathname;

  const absoluteURL = (value, articleURL = siteURL) => {
    const link = unescapeHTML(String(value));
    if (/^[a-z][a-z\d+.-]*:/i.test(link) || link.startsWith("//")) {
      return new URL(link, siteURL).href;
    }
    if (link.startsWith("/")) {
      return rootPath !== "/" && !link.startsWith(rootPath)
        ? new URL(link.replace(/^\/+/, ""), siteURL).href
        : new URL(link, siteURL).href;
    }
    return new URL(link, articleURL).href;
  };
  const pageURL = (value) =>
    absoluteURL(String(value || "").replace(/^\/+/, ""));

  const contentHTML = (value, articleURL) =>
    String(value || "")
      // Hexo's line-number column is presentation, not article content.
      .replace(
        /<td\b[^>]*\bclass\s*=\s*(["'])[^"']*\bgutter\b[^"']*\1[^>]*>[\s\S]*?<\/td>/gi,
        "",
      )
      .replace(
        /<pre\b([^>]*)>([\s\S]*?)<\/pre>/gi,
        (_, attributes, code) =>
          "<pre" +
          attributes +
          ">" +
          code.replace(/<br\s*\/?\s*>/gi, "\n") +
          "</pre>",
      )
      .replace(
        /\b(href|src|poster)\s*=\s*(["'])(.*?)\2/gi,
        (_, attribute, quote, value) => {
          try {
            return (
              attribute + '="' + escapeXML(absoluteURL(value, articleURL)) + '"'
            );
          } catch {
            return attribute + "=" + quote + value + quote;
          }
        },
      );

  const posts = locals.posts
    .sort("-date")
    .toArray()
    .filter((post) => post.feed !== false);
  const configuredLimit = Number(feed.limit == null ? 20 : feed.limit);
  const selected =
    configuredLimit > 0 ? posts.slice(0, Math.floor(configuredLimit)) : posts;
  let latest = new Date(0);
  const entries = selected.map((post) => {
    const published = asDate(post.date) || new Date(0);
    const updated = asDate(post.updated) || published;
    if (updated > latest) latest = updated;
    if (published > latest) latest = published;
    const link = pageURL(post.path);
    const author = post.author || config.author || config.title;
    const authorName = typeof author === "object" ? author.name : author;
    const taxonomy = ["categories", "tags"].flatMap((kind) =>
      post[kind]
        ? post[kind].map(
            (item) =>
              '<category term="' +
              escapeXML(item.name) +
              '" scheme="' +
              escapeXML(pageURL(item.path)) +
              '"/>',
          )
        : [],
    );
    const summary = post.description || post.excerpt;
    return [
      "<entry>",
      '<title type="text">' + escapeXML(post.title) + "</title>",
      "<id>" + escapeXML(link) + "</id>",
      '<link rel="alternate" type="text/html" href="' + escapeXML(link) + '"/>',
      "<author><name>" + escapeXML(authorName) + "</name></author>",
      "<published>" + published.toISOString() + "</published>",
      "<updated>" + updated.toISOString() + "</updated>",
      ...taxonomy,
      ...(summary
        ? [
            '<summary type="text">' +
              escapeXML(unescapeHTML(stripHTML(summary))) +
              "</summary>",
          ]
        : []),
      '<content type="html" xml:base="' +
        escapeXML(link) +
        '">' +
        cdata(contentHTML(post.content, link)) +
        "</content>",
      "</entry>",
    ].join("\n");
  });

  return {
    path: feedPath,
    data: [
      '<?xml version="1.0" encoding="utf-8"?>',
      '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="' +
        escapeXML(config.language || "zh-CN") +
        '">',
      '<title type="text">' + escapeXML(config.title) + "</title>",
      '<subtitle type="text">' +
        escapeXML(config.subtitle || config.description) +
        "</subtitle>",
      "<id>" + escapeXML(siteURL) + "</id>",
      '<link rel="alternate" type="text/html" href="' +
        escapeXML(siteURL) +
        '"/>',
      '<link rel="self" type="application/atom+xml" href="' +
        escapeXML(pageURL(feedPath)) +
        '"/>',
      "<author><name>" +
        escapeXML(config.author || config.title) +
        "</name></author>",
      "<updated>" + latest.toISOString() + "</updated>",
      '<generator uri="https://hexo.io/">Hexo · NOISE</generator>',
      ...entries,
      "</feed>",
      "",
    ].join("\n"),
  };
});
