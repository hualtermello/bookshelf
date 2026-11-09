/**
 * BookShelf - Script do Perfil
 * Gerencia o sistema de abas dinâmicas, editor de texto, chat, publicação e formulário de contato.
 */
document.addEventListener("DOMContentLoaded", () => {
  function sanitizeHTML(str) {
    const temp = document.createElement("div");
    temp.textContent = str;
    return temp.innerHTML;
  }

  // 1. Sistema de Abas Dinâmicas no Main
  
  const tabButtons = document.querySelectorAll(".profile-controls__btn[data-tab]");
  const dynamicContainer = document.getElementById("dynamicMainContainer");
  const initialShelfHTML = dynamicContainer ? dynamicContainer.innerHTML : "";

  window.selecionarAbaPerfil = function(tabKey) {
    const btn = document.querySelector(`.profile-controls__btn[data-tab="${tabKey}"]`);
    if (btn) {
      btn.click();
    }
  };

  window.preencherPerfilMocado = function(nome, bio, generos, interesses, autores) {
    const fNome = document.getElementById('inputPerfilNome');
    const fBio = document.getElementById('inputPerfilBio');
    const fGeneros = document.getElementById('inputPerfilGeneros');
    const fInteresses = document.getElementById('inputPerfilInteresses');
    const fAutores = document.getElementById('inputPerfilAutores');

    if (fNome) fNome.value = nome;
    if (fBio) fBio.value = bio;
    if (fGeneros) fGeneros.value = generos;
    if (fInteresses) fInteresses.value = interesses;
    if (fAutores) fAutores.value = autores;

    const formEl = document.getElementById('formPerfilPreferencias');
    if (formEl) {
      formEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      formEl.style.transition = 'all 0.3s ease';
      formEl.style.boxShadow = '0 0 0 4px rgba(94, 11, 21, 0.25)';
      setTimeout(() => {
        formEl.style.boxShadow = '0 4px 16px rgba(0,0,0,0.04)';
      }, 1500);
    }
  };

  window.adicionarChipGenero = function(genero) {
    const inputGeneros = document.getElementById('inputPerfilGeneros');
    if (!inputGeneros) return;
    let atual = inputGeneros.value.trim();
    if (!atual) {
      inputGeneros.value = genero;
    } else {
      const lista = atual.split(',').map(s => s.trim().toLowerCase());
      if (!lista.includes(genero.toLowerCase())) {
        inputGeneros.value = atual + ', ' + genero;
      }
    }
  };

  function alternarAbaAtiva(tabKey) {
    tabButtons.forEach((b) => {
      if (b.getAttribute("data-tab") === tabKey) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });

    const paneAlvo = document.getElementById(`tabPane-${tabKey}`);
    const todosPanes = document.querySelectorAll(".profile-tab-pane");

    if (paneAlvo && todosPanes.length > 0) {
      todosPanes.forEach((p) => (p.style.display = "none"));
      paneAlvo.style.display = "block";
      initDynamicTabLogic(tabKey);
    } else if (dynamicContainer && tabContents[tabKey]) {
      dynamicContainer.innerHTML = tabContents[tabKey];
      initDynamicTabLogic(tabKey);
    }
  }

  const tabContents = {
    shelf: initialShelfHTML || `
      <section class="board-container" style="box-shadow: none; padding: 0;">
        <h2 class="board-container__title">suas literaturas salvas</h2>
        <div class="carousel">
          <button class="carousel__nav-btn carousel__nav-btn--prev" aria-label="Anterior">&lt;</button>
          <div class="carousel__track">
            <article class="book-card">
              <div class="book-card__cover"><div class="cover-grid"></div></div>
              <header class="book-card__header"><h3 class="book-card__title">Dom Casmurro</h3></header>
              <div class="book-card__tracker">
                <input type="range" class="book-card__range" min="0" max="250" value="80">
                <output class="book-card__count">80 / 250 pág.</output>
              </div>
              <footer class="book-card__actions">
                <div class="book-card__actions-buttons">
                  <button type="button" class="book-card__action-btn book-card__action-btn--like is-active" title="Curtido! ❤️" aria-label="Curtir" onclick="toggleBookLike(this, event)">
                    <svg viewBox="0 0 24 24" class="book-card__icon-heart"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.72-8.72 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                  </button>
                  <button type="button" class="book-card__action-btn book-card__action-btn--fav is-active" title="Salvo nos favoritos! ⭐" aria-label="Favoritar" onclick="toggleBookFav(this, event)">
                    <svg viewBox="0 0 24 24" class="book-card__icon-fav">
                      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"></path>
                      <polygon points="12,7 13.1,9.3 15.6,9.6 13.8,11.3 14.3,13.7 12,12.5 9.7,13.7 10.2,11.3 8.4,9.6 10.9,9.3" class="fav-star"></polygon>
                    </svg>
                  </button>
                </div>
                <div class="book-card__reading-time" title="Você passou 1h 50m lendo este livro" onclick="mostrarTempoLeitura('Dom Casmurro', '1h 50m', event)">
                  <svg viewBox="0 0 24 24" class="book-card__icon-clock"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                  <span class="book-card__reading-time-val">1h 50m</span>
                </div>
              </footer>
            </article>
          </div>
          <button class="carousel__nav-btn carousel__nav-btn--next" aria-label="Próximo">&gt;</button>
        </div>
      </section>
    `,
    draft: `
      <div class="text-editor" style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
          <div class="text-editor__toolbar">
            <button type="button" class="perfil-controles__btn" data-command="bold" style="padding: 9px 18px; font-size: 0.85rem;">Negrito</button>
            <button type="button" class="perfil-controles__btn" data-command="italic" style="padding: 9px 18px; font-size: 0.85rem;">Itálico</button>
            <button type="button" class="perfil-controles__btn" data-command="underline" style="padding: 9px 18px; font-size: 0.85rem;">Sublinhado</button>
          </div>
          <a href="/modelo-grafica" class="formulario-contato__btn" style="text-decoration: none; background: var(--bg-nav); color: #fff; padding: 10px 22px; border-radius: 999px; font-size: 0.88rem; font-weight: 700;">
            Abrir Modelo Completo para Gráfica (Páginas A4) &rarr;
          </a>
        </div>
        <div contenteditable="true" class="text-editor__textarea" style="border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; min-height: 220px; outline: none; background: #fff; color: #252b42;">Comece a escrever seu rascunho literário aqui...</div>
      </div>
    `,
    chat: `
      <div class="social-chat" style="display: flex; flex-direction: column; gap: 16px;">
        <div class="social-chat__input-group">
          <input type="text" id="chatInput" class="social-chat__input" placeholder="O que você está pensando sobre sua leitura atual?">
          <button type="button" id="chatSubmit" class="formulario-contato__btn" style="padding: 12px 24px;">Enviar</button>
        </div>
        <div class="social-chat__feed" id="chatFeed" style="display: flex; flex-direction: column; gap: 14px; margin-top: 8px;">
          <div class="social-chat__post" style="background: #f8fafc; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0;">
            <strong style="color: var(--bg-nav); display: block; margin-bottom: 6px;">Leitor Ávido</strong>
            <p style="color: #252b42; font-size: 0.95rem;">Terminei o capítulo 3. Incrível como a narrativa prende a atenção!</p>
          </div>
        </div>
      </div>
    `,
    publish: `
      <div class="publish-section" style="display: flex; flex-direction: column; gap: 18px;">
        <h3 style="font-size: 1.15rem; color: var(--bg-nav);">Revisão Ortográfica e Publicação</h3>
        <button type="button" id="startValidationBtn" class="formulario-contato__btn" style="align-self: flex-start;">Iniciar Validação</button>
        <div class="progress-container" style="display: none; width: 100%; background: #e2e8f0; border-radius: 999px; height: 16px; overflow: hidden;">
          <div id="progressBar" style="width: 0%; height: 100%; background: var(--accent-blue); transition: width 0.1s linear;"></div>
        </div>
        <p id="validationStatus" style="font-size: 0.92rem; color: #64748b;"></p>
        <div id="publishActions" style="display: none; flex-direction: column; gap: 16px; margin-top: 10px;">
          <form action="/perfil/publicar" method="POST" enctype="multipart/form-data" style="display: flex; flex-direction: column; gap: 14px;">
            <input type="text" name="titulo" class="footer-global__input" placeholder="Título da Obra" required>
            <input type="file" name="arquivo" class="footer-global__input" accept=".epub" required>
            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 4px;">
              <button type="submit" class="formulario-contato__btn" style="background: #15803d; color: #fff; border: none; padding: 12px 24px; border-radius: 999px; cursor: pointer;">Publicar como eBook</button>
              <a href="/modelo-grafica" class="formulario-contato__btn" style="background: var(--bg-nav); color: #fff; border: none; padding: 12px 24px; border-radius: 999px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center;">Preparar para Impressão (Modelo Gráfica A4)</a>
            </div>
          </form>
        </div>
      </div>
    `,
  };

  function initDynamicTabLogic(tabKey) {
    if (tabKey === "shelf" && dynamicContainer) {
      const rangeInputs = dynamicContainer.querySelectorAll(".book-card__range");
      rangeInputs.forEach((input) => {
        const card = input.closest(".book-card");
        const countOutput = card?.querySelector(".book-card__count");
        const maxPages = parseInt(input.max, 10) || 300;
        input.addEventListener("input", (e) => {
          const val = e.target.value;
          if (countOutput) {
            countOutput.textContent = `${val} / ${maxPages} pág.`;
          }
        });
      });
    } else if (tabKey === "draft") {
      document.querySelectorAll(".text-editor__toolbar button").forEach((b) => {
        b.addEventListener("click", () =>
          document.execCommand(b.getAttribute("data-command"), false, null),
        );
      });
    } else if (tabKey === "chat") {
      const chatSubmit = document.getElementById("chatSubmit");
      const chatInput = document.getElementById("chatInput");
      const chatFeed = document.getElementById("chatFeed");
      if (chatSubmit && chatInput && chatFeed) {
        chatSubmit.addEventListener("click", () => {
          const text = chatInput.value.trim();
          if (text) {
            const sanitized = sanitizeHTML(text);
            const postHTML = `<div class="social-chat__post" style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;"><strong style="color: #3b82f6; display: block; margin-bottom: 4px;">Leitor Ávido</strong><p style="color: #252b42; font-size: 0.95rem;">${sanitized}</p></div>`;
            chatFeed.insertAdjacentHTML("afterbegin", postHTML);
            chatInput.value = "";
          }
        });
      }
    } else if (tabKey === "publish") {
      const startBtn = document.getElementById("startValidationBtn");
      const progressBar = document.getElementById("progressBar");
      const progressContainer = startBtn?.parentElement.querySelector(
        ".progress-container",
      );
      const statusText = document.getElementById("validationStatus");
      const publishActions = document.getElementById("publishActions");

      if (
        startBtn &&
        progressBar &&
        progressContainer &&
        statusText &&
        publishActions
      ) {
        startBtn.addEventListener("click", () => {
          startBtn.disabled = true;
          progressContainer.style.display = "block";
          statusText.textContent =
            "Analisando ortografia e estrutura literária...";
          let progress = 0;
          const interval = setInterval(() => {
            progress += 2;
            progressBar.style.width = `${progress}%`;
            if (progress >= 100) {
              clearInterval(interval);
              statusText.textContent = "Validação concluída com sucesso!";
              publishActions.style.display = "flex";
            }
          }, 30);
        });
      }
    }
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabKey = btn.getAttribute("data-tab");
      alternarAbaAtiva(tabKey);
    });
  });

  // Verifica se há aba solicitada via query string (ex: ?tab=suggestions)
  try {
    const params = new URLSearchParams(window.location.search);
    const paramTab = params.get("tab");
    if (paramTab) {
      alternarAbaAtiva(paramTab);
    }
  } catch (e) {}

  // 2. Validação do Formulário de Contato
  const contactForm =
    document.querySelector(".formulario-contato form") ||
    document.querySelector(".footer-global__contact-form");
  if (contactForm) {
    contactForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const inputs = contactForm.querySelectorAll(
        ".formulario-contato__campo, .footer-global__input, .footer-global__textarea",
      );
      let isValid = true;
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      inputs.forEach((input) => {
        const val = input.value.trim();
        if (!val || (input.type === "email" && !emailRegex.test(val))) {
          isValid = false;
          input.style.borderColor = "#ef4444";
        } else {
          input.style.borderColor = "#10b981";
        }
      });

      if (isValid) {
        alert("Mensagem enviada com sucesso!");
        contactForm.reset();
        inputs.forEach((input) => (input.style.borderColor = ""));
      } else {
        alert("Por favor, preencha todos os campos corretamente.");
      }
    });
  }

  // 3. Botão para voltar à Home
  const homeToggleBtn = document.getElementById("homeToggleBtn");
  if (homeToggleBtn) {
    homeToggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      window.location.href = "/index";
    });
  }
});

// Interações dos Cards de Livro: Like (Coração), Favoritar (Coração Favorito) e Relógio
window.toggleBookLike = function(btn, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const wasActive = btn.classList.contains("is-active");
  btn.classList.toggle("is-active");
  if (!wasActive) {
    btn.setAttribute("title", "Curtido! ❤️");
  } else {
    btn.setAttribute("title", "Curtir (Like)");
  }
};

window.toggleBookFav = function(btn, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const wasActive = btn.classList.contains("is-active");
  btn.classList.toggle("is-active");
  if (!wasActive) {
    btn.setAttribute("title", "Salvo nos favoritos! ⭐");
  } else {
    btn.setAttribute("title", "Favoritar este livro");
  }
};

window.mostrarTempoLeitura = function(titulo, tempo, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  // Remove toast anterior se houver
  const oldToast = document.querySelector(".book-reading-toast");
  if (oldToast) oldToast.remove();

  const toast = document.createElement("div");
  toast.className = "book-reading-toast";
  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #38bdf8;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
      <span>Tempo de Leitura Registrado</span>
    </div>
    <div style="font-size: 0.88rem; color: #f1f5f9; line-height: 1.4;">
      Você já dedicou <strong style="color: #FDE68A;">${tempo}</strong> à leitura de <em>${titulo}</em> no BookShelf.
    </div>
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("book-reading-toast--fade");
    setTimeout(() => toast.remove(), 350);
  }, 3200);
};
