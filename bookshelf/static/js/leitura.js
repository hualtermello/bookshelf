document.addEventListener("DOMContentLoaded", async () => {
  const paper = document.getElementById("reading-paper");
  const fill = document.getElementById("progress-fill");
  const percentLabel = document.getElementById("progress-percent");
  const counter = document.getElementById("page-counter");
  const previous = document.getElementById("previous-page");
  const next = document.getElementById("next-page");
  const status = document.getElementById("reader-status");
  const chapterList = document.getElementById("chapter-list");
  let fontSize = 100, wide = false, book = null, rendition = null, locationsReady = false;

  document.getElementById("font-smaller")?.addEventListener("click", () => {
    fontSize = Math.max(70, fontSize - 10); rendition?.themes.fontSize(`${fontSize}%`);
  });
  document.getElementById("font-larger")?.addEventListener("click", () => {
    fontSize = Math.min(180, fontSize + 10); rendition?.themes.fontSize(`${fontSize}%`);
  });
  document.getElementById("toggle-theme")?.addEventListener("click", () => {
    document.body.classList.toggle("reader-dark");
    const dark = document.body.classList.contains("reader-dark");
    rendition?.themes.select(dark ? "dark" : "light");
  });
  document.getElementById("width-toggle")?.addEventListener("click", () => {
    wide = !wide; paper.classList.toggle("reading-paper-wide", wide); rendition?.resize();
  });
  previous?.addEventListener("click", () => rendition?.prev());
  next?.addEventListener("click", () => rendition?.next());

  function updateProgress(location) {
    if (!location) return;
    const percentage = location.start?.percentage || 0;
    const pct = Math.max(0, Math.min(100, Math.round(percentage * 100)));
    if (fill) fill.style.width = `${pct}%`;
    if (percentLabel) percentLabel.textContent = `${pct}%`;
    if (counter) counter.textContent = locationsReady ? `${pct}% do livro` : 'Carregando…';
    if (previous) previous.disabled = !location.atStart;
    if (next) next.textContent = location.atEnd ? 'Fim do livro' : 'Próxima →';
    try { localStorage.setItem(`bookshelf_reader_${location.start?.href || 'progress'}`, location.start?.cfi || ''); } catch (_) {}
  }

  if (!window.BOOKSHELF_HAS_EPUB) {
    if (status) status.textContent = 'Não há arquivo EPUB associado a esta obra.';
    if (next) next.disabled = true;
    return;
  }
  if (!window.ePub) {
    if (status) status.textContent = 'Não foi possível carregar o leitor. Verifique sua conexão e recarregue a página.';
    return;
  }
  try {
    if (status) status.textContent = 'Carregando capítulos do EPUB…';
    book = ePub(window.BOOKSHELF_EPUB_URL);
    rendition = book.renderTo('epub-viewer', { width: '100%', height: '72vh', spread: 'none', flow: 'paginated' });
    rendition.themes.register('light', { body: { color: '#302b27', background: '#fffdf9', 'font-family': 'Georgia, serif', 'line-height': '1.8' } });
    rendition.themes.register('dark', { body: { color: '#eee7df', background: '#242222', 'font-family': 'Georgia, serif', 'line-height': '1.8' } });
    rendition.themes.select('light');
    rendition.on('relocated', updateProgress);
    await book.ready;
    await rendition.display();
    await book.locations.generate(1000);
    locationsReady = true;
    const toc = book.navigation?.toc || [];
    if (chapterList) {
      chapterList.innerHTML = '';
      if (!toc.length) chapterList.innerHTML = '<p class="reader-muted small">Este EPUB não possui sumário.</p>';
      toc.forEach((chapter, index) => {
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'reader-chapter';
        button.innerHTML = `<span>${String(index + 1).padStart(2, '0')}</span> ${escapeHtml(chapter.label || `Capítulo ${index + 1}`)}`;
        button.addEventListener('click', () => rendition.display(chapter.href));
        chapterList.appendChild(button);
      });
    }
    if (status) status.textContent = 'Arquivo carregado. Boa leitura!';
    updateProgress(rendition.currentLocation());
  } catch (error) {
    console.error('Erro ao abrir EPUB:', error);
    if (status) status.textContent = 'Não foi possível abrir este EPUB. O arquivo pode estar corrompido.';
    if (counter) counter.textContent = 'Erro ao abrir livro';
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  }
});
