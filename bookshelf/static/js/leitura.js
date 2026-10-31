document.addEventListener("DOMContentLoaded", async () => {
  const paper = document.getElementById("reading-paper");
  const viewer = document.getElementById("epub-viewer");
  const fill = document.getElementById("progress-fill");
  const percentLabel = document.getElementById("progress-percent");
  const counter = document.getElementById("page-counter");
  const previous = document.getElementById("previous-page");
  const next = document.getElementById("next-page");
  const status = document.getElementById("reader-status");
  const chapterList = document.getElementById("chapter-list");

  let fontSize = 100;
  let wide = false;
  let book = null;
  let rendition = null;
  let locationsReady = false;
  let fallbackChapters = null;
  let fallbackIndex = 0;

  const storageKey = `bookshelf_reader_book_${window.BOOKSHELF_BOOK_ID || "default"}`;

  function normalizeHref(href) {
    if (!href) return "";
    return String(href)
      .split("#")[0]
      .split("?")[0]
      .replace(/\\/g, "/")
      .replace(/^(\.\.\/|\.\/)+/, "")
      .replace(/^\/+/, "")
      .replace(/^OEBPS\//i, "")
      .trim();
  }

  function refreshRenditionLayout() {
    if (!rendition) return;
    try {
      const contentsList = rendition.getContents ? rendition.getContents() : [];
      contentsList.forEach((c) => {
        if (typeof c.resizeCheck === "function") {
          c.resizeCheck();
        } else if (typeof c.expand === "function") {
          c.expand();
        }
      });
    } catch (_) {}
    setTimeout(() => {
      try {
        const contentsList = rendition.getContents ? rendition.getContents() : [];
        contentsList.forEach((c) => c.resizeCheck?.());
        if (rendition.currentLocation) {
          updateProgress(rendition.currentLocation());
        }
      } catch (_) {}
    }, 120);
  }

  function applyFontSize() {
    if (rendition) {
      rendition.themes.fontSize(`${fontSize}%`);
      refreshRenditionLayout();
    }
    if (paper) {
      paper.style.setProperty("--reader-font-size", `${Math.round((18 * fontSize) / 100)}px`);
    }
  }

  document.getElementById("font-smaller")?.addEventListener("click", () => {
    fontSize = Math.max(70, fontSize - 10);
    applyFontSize();
  });

  document.getElementById("font-larger")?.addEventListener("click", () => {
    fontSize = Math.min(180, fontSize + 10);
    applyFontSize();
  });

  document.getElementById("toggle-theme")?.addEventListener("click", () => {
    document.body.classList.toggle("reader-dark");
    const dark = document.body.classList.contains("reader-dark");
    rendition?.themes.select(dark ? "dark" : "light");
  });

  document.getElementById("width-toggle")?.addEventListener("click", () => {
    wide = !wide;
    paper?.classList.toggle("reading-paper-wide", wide);
    if (rendition && viewer) {
      const h = Math.max(520, viewer.clientHeight || Math.round(window.innerHeight * 0.68));
      rendition.resize(viewer.clientWidth || "100%", h);
      refreshRenditionLayout();
    }
  });

  previous?.addEventListener("click", () => {
    if (fallbackChapters) {
      if (fallbackIndex > 0) renderFallbackChapter(fallbackIndex - 1);
    } else {
      rendition?.prev();
    }
  });

  next?.addEventListener("click", () => {
    if (fallbackChapters) {
      if (fallbackIndex < fallbackChapters.length - 1) renderFallbackChapter(fallbackIndex + 1);
    } else {
      rendition?.next();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") previous?.click();
    if (e.key === "ArrowRight") next?.click();
  });

  function saveServerProgress(pct) {
    if (!window.BOOKSHELF_PROGRESS_URL) return;
    fetch(window.BOOKSHELF_PROGRESS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ progresso: pct })
    }).catch(() => {});
  }

  function highlightActiveChapter(hrefOrIndex) {
    if (!chapterList) return;
    const buttons = chapterList.querySelectorAll(".reader-chapter");
    const targetNorm = typeof hrefOrIndex === "string" ? normalizeHref(hrefOrIndex).toLowerCase() : "";
    buttons.forEach((btn, idx) => {
      const btnHref = normalizeHref(btn.getAttribute("data-href") || "").toLowerCase();
      const isMatch =
        typeof hrefOrIndex === "number"
          ? idx === hrefOrIndex
          : Boolean(targetNorm && btnHref && targetNorm === btnHref);
      btn.classList.toggle("active", isMatch);
    });
  }

  function updateProgress(location) {
    if (!location || !location.start) return;

    const totalSpine = book?.spine?.spineItems?.length || 1;
    const currentIdx = location.start.index ?? 0;
    const displayedPage = location.start.displayed?.page || 1;
    const displayedTotal = location.start.displayed?.total || 1;

    let percentage = null;
    if (locationsReady && book?.locations?.total > 0 && location.start.cfi) {
      try {
        const cfiPct = book.locations.percentageFromCfi(location.start.cfi);
        if (typeof cfiPct === "number" && !Number.isNaN(cfiPct) && cfiPct > 0) {
          percentage = cfiPct;
        }
      } catch (_) {}
    }

    if (percentage === null) {
      percentage = (currentIdx + displayedPage / Math.max(1, displayedTotal)) / Math.max(1, totalSpine);
    }

    if (location.atEnd) {
      percentage = 1;
    } else if (location.atStart && currentIdx === 0 && displayedPage === 1) {
      percentage = 0;
    }

    const pct = Math.max(0, Math.min(100, Math.round((percentage || 0) * 100)));
    if (fill) fill.style.width = `${pct}%`;
    if (percentLabel) percentLabel.textContent = `${pct}%`;

    const displayed = location.start.displayed;
    if (counter) {
      if (displayed && displayed.total) {
        counter.textContent = `Página ${displayed.page} de ${displayed.total} • Seção ${currentIdx + 1}/${totalSpine} (${pct}%)`;
      } else {
        counter.textContent = `Seção ${currentIdx + 1}/${totalSpine} (${pct}%)`;
      }
    }

    const isAtStart = Boolean(location.atStart) || (currentIdx === 0 && displayedPage <= 1);
    const isAtEnd = Boolean(location.atEnd) || (currentIdx >= totalSpine - 1 && displayedPage >= displayedTotal);

    if (previous) previous.disabled = isAtStart;
    if (next) {
      next.disabled = isAtEnd;
      next.textContent = isAtEnd ? "Fim do livro" : "Próxima →";
    }

    highlightActiveChapter(location.start.href || currentIdx);

    try {
      if (location.start.cfi) {
        localStorage.setItem(storageKey, location.start.cfi);
      }
    } catch (_) {}

    saveServerProgress(pct);
  }

  function renderFallbackChapter(index) {
    if (!fallbackChapters || !fallbackChapters.length || !viewer) return;
    fallbackIndex = Math.max(0, Math.min(fallbackChapters.length - 1, index));
    const chapter = fallbackChapters[fallbackIndex];
    viewer.innerHTML = `<article class="epub-fallback-content">${chapter.html}</article>`;
    viewer.scrollTop = 0;

    const pct = Math.round(((fallbackIndex + 1) / fallbackChapters.length) * 100);
    if (fill) fill.style.width = `${pct}%`;
    if (percentLabel) percentLabel.textContent = `${pct}%`;
    if (counter) {
      counter.textContent = `Capítulo ${fallbackIndex + 1} de ${fallbackChapters.length} (${pct}%)`;
    }
    if (previous) previous.disabled = fallbackIndex === 0;
    if (next) {
      next.disabled = fallbackIndex >= fallbackChapters.length - 1;
      next.textContent = fallbackIndex >= fallbackChapters.length - 1 ? "Fim do livro" : "Próxima →";
    }
    highlightActiveChapter(fallbackIndex);
    saveServerProgress(pct);
  }

  async function loadServerFallback() {
    if (!window.BOOKSHELF_CHAPTERS_URL) {
      throw new Error("URL de capítulos indisponível.");
    }
    const resp = await fetch(window.BOOKSHELF_CHAPTERS_URL);
    if (!resp.ok) {
      throw new Error(`Erro ao carregar capítulos (${resp.status})`);
    }
    const data = await resp.json();
    if (!data.capitulos || !data.capitulos.length) {
      throw new Error("Nenhum capítulo legível encontrado no EPUB.");
    }
    fallbackChapters = data.capitulos;
    if (viewer) {
      viewer.classList.add("epub-viewer-scrollable");
    }
    if (chapterList) {
      chapterList.innerHTML = "";
      fallbackChapters.forEach((chapter, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "reader-chapter";
        button.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span> ${escapeHtml(chapter.titulo || `Capítulo ${index + 1}`)}`;
        button.addEventListener("click", () => renderFallbackChapter(index));
        chapterList.appendChild(button);
      });
    }
    if (status) status.textContent = "Arquivo carregado. Boa leitura!";
    renderFallbackChapter(0);
  }

  if (!window.BOOKSHELF_HAS_EPUB) {
    if (status) status.textContent = "Não há arquivo EPUB associado a esta obra.";
    if (counter) counter.textContent = "Indisponível";
    if (next) next.disabled = true;
    return;
  }

  if (!window.ePub || !window.JSZip) {
    try {
      await loadServerFallback();
    } catch (err) {
      console.error("Erro no leitor fallback:", err);
      if (status) status.textContent = "Não foi possível carregar o leitor. Recarregue a página.";
      if (counter) counter.textContent = "Erro ao abrir livro";
    }
    return;
  }

  try {
    if (status) status.textContent = "Carregando capítulos do EPUB…";

    const response = await fetch(window.BOOKSHELF_EPUB_URL);
    if (!response.ok) {
      throw new Error(`Falha ao baixar EPUB (HTTP ${response.status})`);
    }
    const epubData = await response.arrayBuffer();

    book = window.ePub();
    await book.open(epubData, "binary");
    await book.ready;

    // Garantir que todas as seções do spine (inclusive Capa e Sumário com linear="no")
    // sejam navegáveis em sequência pelo leitor e pelos botões Anterior/Próxima.
    const spineItems = book.spine?.spineItems || [];
    spineItems.forEach((item, idx) => {
      item.index = idx;
      item.linear = true;
      item.prev = () => (idx > 0 ? spineItems[idx - 1] : undefined);
      item.next = () => (idx < spineItems.length - 1 ? spineItems[idx + 1] : undefined);
      const norm = normalizeHref(item.href);
      if (norm && book.spine.spineByHref) {
        book.spine.spineByHref[norm] = idx;
        book.spine.spineByHref[`../${norm}`] = idx;
        book.spine.spineByHref[`OEBPS/${norm}`] = idx;
        const base = norm.split("/").pop();
        if (base && !(base in book.spine.spineByHref)) {
          book.spine.spineByHref[base] = idx;
        }
      }
    });

    if (book.spine && typeof book.spine.get === "function") {
      const origGet = book.spine.get.bind(book.spine);
      book.spine.get = function (target) {
        if (target === undefined || target === null) {
          return spineItems[0] || null;
        }
        if (typeof target === "number") {
          return spineItems[target] || null;
        }
        if (typeof target === "string" && !this.epubcfi?.isCfiString(target) && !target.startsWith("#")) {
          const clean = target.split("#")[0];
          const norm = normalizeHref(clean);
          const byHref = this.spineByHref || {};
          if (clean in byHref) return spineItems[byHref[clean]] || null;
          if (norm in byHref) return spineItems[byHref[norm]] || null;
          const found = spineItems.find((s) => normalizeHref(s.href).toLowerCase() === norm.toLowerCase());
          if (found) return found;
        }
        return origGet(target);
      };
    }

    const viewerHeight = Math.max(520, viewer?.clientHeight || Math.round(window.innerHeight * 0.68));
    rendition = book.renderTo("epub-viewer", {
      width: "100%",
      height: viewerHeight,
      spread: "none",
      flow: "paginated",
      allowScriptedContent: true
    });

    rendition.hooks.content.register((contents) => {
      try {
        contents.addStylesheetRules({
          "img, svg": {
            "max-width": "100% !important",
            "max-height": "86vh !important",
            "height": "auto !important",
            "object-fit": "contain"
          }
        });
        const doc = contents.document;
        if (doc?.fonts?.ready) {
          doc.fonts.ready.then(() => {
            contents.resizeCheck?.();
            if (rendition?.currentLocation) {
              updateProgress(rendition.currentLocation());
            }
          });
        }
        doc?.querySelectorAll("img").forEach((img) => {
          if (!img.complete) {
            img.addEventListener("load", () => {
              contents.resizeCheck?.();
              if (rendition?.currentLocation) {
                updateProgress(rendition.currentLocation());
              }
            });
          }
        });
      } catch (_) {}
    });

    rendition.themes.register("light", {
      body: {
        color: "#302b27",
        background: "#fffdf9",
        "font-family": "Georgia, serif",
        "line-height": "1.8"
      }
    });
    rendition.themes.register("dark", {
      body: {
        color: "#eee7df",
        background: "#242222",
        "font-family": "Georgia, serif",
        "line-height": "1.8"
      }
    });
    rendition.themes.select(document.body.classList.contains("reader-dark") ? "dark" : "light");
    rendition.on("relocated", updateProgress);

    let savedCfi = null;
    try {
      savedCfi = localStorage.getItem(storageKey);
    } catch (_) {}

    if (savedCfi) {
      try {
        await rendition.display(savedCfi);
      } catch (_) {
        await rendition.display(0);
      }
    } else {
      await rendition.display(0);
    }

    // Construir o sumário na ordem real de leitura (spine), associando os títulos do TOC
    const rawToc = book.navigation?.toc || [];
    const tocLabelByHref = {};
    const collectTocLabels = (items) => {
      items.forEach((t) => {
        const k = normalizeHref(t.href).toLowerCase();
        if (k && t.label && !tocLabelByHref[k]) {
          tocLabelByHref[k] = t.label.trim();
        }
        if (t.subitems?.length) collectTocLabels(t.subitems);
      });
    };
    collectTocLabels(rawToc);

    const fallbackNames = {
      "capa.xhtml": "Capa",
      "dlivros.xhtml": "Apresentação",
      "rosto.xhtml": "Folha de Rosto",
      "dedicatoria.xhtml": "Dedicatória",
      "sumario.xhtml": "Sumário",
      "epigrafe.xhtml": "Epígrafe",
      "creditos.xhtml": "Créditos",
      "ficha.xhtml": "Ficha Catalográfica",
      "sobre.xhtml": "Sobre a autora",
      "livros.xhtml": "Obras da autora"
    };

    const toc = spineItems.length
      ? spineItems.map((item, idx) => {
          const norm = normalizeHref(item.href);
          const lower = norm.toLowerCase();
          const base = lower.split("/").pop() || "";
          const label =
            tocLabelByHref[lower] ||
            fallbackNames[base] ||
            `Seção ${idx + 1}`;
          return { label, href: item.href, index: idx };
        })
      : rawToc;

    if (chapterList) {
      chapterList.innerHTML = "";
      if (!toc.length) {
        chapterList.innerHTML = '<p class="reader-muted small">Este EPUB não possui sumário.</p>';
      }
      toc.forEach((chapter, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "reader-chapter";
        button.setAttribute("data-href", chapter.href || "");
        button.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span> ${escapeHtml(chapter.label?.trim() || `Capítulo ${index + 1}`)}`;
        button.addEventListener("click", () => {
          rendition.display(chapter.href || chapter.index);
        });
        chapterList.appendChild(button);
      });
    }

    if (status) status.textContent = "Arquivo carregado. Boa leitura!";
    refreshRenditionLayout();
    updateProgress(rendition.currentLocation());

    book.locations
      .generate(1000)
      .then(() => {
        locationsReady = true;
        updateProgress(rendition.currentLocation());
      })
      .catch((err) => {
        console.warn("Aviso ao gerar páginas do EPUB:", err);
      });
  } catch (error) {
    console.warn("Tentando leitor alternativo após erro no epub.js:", error);
    try {
      await loadServerFallback();
    } catch (fallbackError) {
      console.error("Erro ao abrir EPUB:", fallbackError);
      if (status) status.textContent = "Não foi possível abrir este EPUB. O arquivo pode estar corrompido.";
      if (counter) counter.textContent = "Erro ao abrir livro";
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
    ));
  }
});
