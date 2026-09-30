(() => {
  "use strict";
  const script = document.currentScript;
  const dialog = document.querySelector("#search-dialog");
  const input = document.querySelector("#search-input");
  const results = document.querySelector("#search-results");
  const status = document.querySelector("#search-status");
  let posts;
  let loading;
  let previousFocus;
  let searchTimer;

  async function loadIndex() {
    if (posts) return posts;
    if (!loading) {
      status.textContent = "正在翻开记录…";
      loading = fetch(script.dataset.search)
        .then((response) => {
          if (!response.ok) throw new Error("Search index unavailable");
          return response.json();
        })
        .then((data) => (posts = data))
        .catch((error) => {
          loading = null;
          throw error;
        });
    }
    return loading;
  }

  function highlighted(element, text, terms) {
    const lower = text.toLocaleLowerCase();
    let cursor = 0;
    while (cursor < text.length) {
      let next = -1;
      let term = "";
      for (const candidate of terms) {
        const index = lower.indexOf(candidate, cursor);
        if (index >= 0 && (next < 0 || index < next)) {
          next = index;
          term = candidate;
        }
      }
      if (next < 0) {
        element.append(document.createTextNode(text.slice(cursor)));
        break;
      }
      element.append(document.createTextNode(text.slice(cursor, next)));
      const mark = document.createElement("mark");
      mark.textContent = text.slice(next, next + term.length);
      element.append(mark);
      cursor = next + term.length;
    }
  }

  async function search() {
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) {
      status.textContent = "输入关键词，搜索全部文章。";
      return;
    }
    let data;
    try {
      data = await loadIndex();
    } catch {
      status.textContent = "暂时无法加载搜索。请检查网络后重新输入关键词。";
      return;
    }
    if (input.value.trim() !== query) return;
    const terms = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const matches = data
      .map((post) => {
        const title = post.title.toLocaleLowerCase();
        const tags = post.tags.join(" ").toLocaleLowerCase();
        const body = post.text.toLocaleLowerCase();
        const searchable = title + " " + tags + " " + body;
        const score = terms.every((term) => searchable.includes(term))
          ? terms.reduce(
              (sum, term) =>
                sum +
                (title.includes(term) ? 10 : 0) +
                (tags.includes(term) ? 5 : 0) +
                (body.includes(term) ? 1 : 0),
              0,
            )
          : 0;
        return { post, score };
      })
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score);
    status.textContent = matches.length
      ? `找到 ${matches.length} 篇相关记录${matches.length > 30 ? "，显示前 30 篇" : ""}。`
      : "没有找到相关记录，换一个关键词试试。";
    const fragment = document.createDocumentFragment();
    for (const { post } of matches.slice(0, 30)) {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = post.url;
      const date = document.createElement("small");
      date.textContent =
        post.date + (post.tags.length ? " / " + post.tags.join(" · ") : "");
      const title = document.createElement("h3");
      highlighted(title, post.title, terms);
      const excerpt = document.createElement("p");
      const positions = terms
        .map((term) => post.text.toLocaleLowerCase().indexOf(term))
        .filter((index) => index >= 0);
      const start = positions.length
        ? Math.max(0, Math.min(...positions) - 35)
        : 0;
      highlighted(
        excerpt,
        (start ? "…" : "") +
          post.text.slice(start, start + 145) +
          (post.text.length > start + 145 ? "…" : ""),
        terms,
      );
      link.append(date, title, excerpt);
      li.append(link);
      fragment.append(li);
    }
    results.replaceChildren(fragment);
  }

  function openSearch() {
    if (dialog.open) return;
    previousFocus = document.activeElement;
    dialog.showModal();
    input.focus();
    if (input.value.trim()) search();
  }
  document
    .querySelectorAll("[data-search-open]")
    .forEach((button) => button.addEventListener("click", openSearch));
  document
    .querySelector("[data-search-close]")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => previousFocus?.focus());
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      dialog.close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dialog.open) {
      event.preventDefault();
      dialog.close();
      return;
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearch();
    }
  });
  input.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(search, 120);
  });

  document
    .querySelectorAll(".prose figure.highlight, .prose pre")
    .forEach((block) => {
      if (block.matches("pre") && block.closest("figure.highlight")) return;
      const button = document.createElement("button");
      button.className = "code-copy";
      button.type = "button";
      button.textContent = "复制代码";
      button.setAttribute("aria-label", "复制代码");
      button.addEventListener("click", async () => {
        const code =
          block.querySelector("td.code pre") ||
          block.querySelector("code") ||
          block;
        const lines = [...code.querySelectorAll(":scope > .line")];
        const text = lines.length
          ? lines.map((line) => line.textContent).join("\n") + "\n"
          : code === block
            ? [...block.childNodes]
                .filter((node) => node !== button)
                .map((node) => node.textContent)
                .join("")
            : code.textContent;
        try {
          if (navigator.clipboard && window.isSecureContext)
            await navigator.clipboard.writeText(text);
          else {
            const area = document.createElement("textarea");
            area.value = text;
            area.style.position = "fixed";
            area.style.opacity = "0";
            document.body.append(area);
            area.select();
            const copied = document.execCommand("copy");
            area.remove();
            button.focus();
            if (!copied) throw new Error("Copy failed");
          }
          button.textContent = "已复制 ✓";
        } catch {
          button.textContent = "请手动选择复制";
        }
        setTimeout(() => {
          button.textContent = "复制代码";
        }, 2200);
      });
      block.append(button);
    });

  const progress = document.querySelector(".reading-progress");
  const article = document.querySelector("#post-content");
  if (progress && article) {
    const updateProgress = () => {
      const rect = article.getBoundingClientRect();
      const available = Math.max(1, rect.height - window.innerHeight);
      progress.style.width =
        Math.min(100, Math.max(0, (-rect.top / available) * 100)) + "%";
    };
    document.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
    updateProgress();
    const links = [...document.querySelectorAll(".toc-link")];
    const sections = links
      .map((link) =>
        document.getElementById(decodeURIComponent(link.hash.slice(1))),
      )
      .filter(Boolean);
    if ("IntersectionObserver" in window && sections.length) {
      const observer = new IntersectionObserver(
        (entries) => {
          const visible = entries.filter((entry) => entry.isIntersecting);
          if (!visible.length) return;
          const current = visible[0].target.id;
          links.forEach((link) => {
            const active = decodeURIComponent(link.hash.slice(1)) === current;
            link.classList.toggle("active", active);
            if (active) link.setAttribute("aria-current", "location");
            else link.removeAttribute("aria-current");
          });
        },
        { rootMargin: "-5% 0px -75% 0px", threshold: 0 },
      );
      sections.forEach((section) => observer.observe(section));
    }
  }
})();
