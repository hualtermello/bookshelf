/**
 * BookShelf - Script Unificado
 * Gerencia a alternância de login/cadastro, carrosséis de literaturas, rastreadores de páginas e navegação.
 */
document.addEventListener("DOMContentLoaded", () => {
  
  // 0. Alternância de Telas (Login / Cadastro)
  const authContainer = document.getElementById("authContainer");
  const btnIrParaCadastro = document.getElementById("btnIrParaCadastro");
  const btnVoltarLogin = document.getElementById("btnVoltarLogin");
  const telaLogin = document.getElementById("telaLogin");
  const telaCadastro = document.getElementById("telaCadastro");
  const formCadastro = document.getElementById("formCadastro");

  if (btnIrParaCadastro && btnVoltarLogin && authContainer) {
    const abrirCadastro = () => {
      authContainer.classList.add("auth-container--show-register");
      telaCadastro.removeAttribute("inert");
      telaLogin.setAttribute("inert", "");
    };

    const abrirLogin = () => {
      authContainer.classList.remove("auth-container--show-register");
      telaLogin.removeAttribute("inert"); // <-- CORRIGIDO AQUI
      telaCadastro.setAttribute("inert", "");
    };

    btnIrParaCadastro.addEventListener("click", abrirCadastro);
    btnVoltarLogin.addEventListener("click", abrirLogin);

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("modo") === "cadastro" || window.location.pathname === "/cadastro") {
      abrirCadastro();
    }
  }

  if (formCadastro) {
    formCadastro.addEventListener("submit", (e) => {
      const senha = document.getElementById("cadastroSenha");
      const confirmaSenha = document.getElementById("cadastroConfirmaSenha");
      if (senha && confirmaSenha && senha.value !== confirmaSenha.value) {
        e.preventDefault();
        confirmaSenha.setCustomValidity("As senhas não coincidem.");
        confirmaSenha.reportValidity();
      } else if (confirmaSenha) {
        confirmaSenha.setCustomValidity("");
      }
    });

    const confirmaInput = document.getElementById("cadastroConfirmaSenha");
    if (confirmaInput) {
      confirmaInput.addEventListener("input", () => confirmaInput.setCustomValidity(""));
    }
  }

  // 1. Controle dos Carrosséis
  const carousels = document.querySelectorAll(".carousel");
  carousels.forEach((carousel) => {
    const track =
      carousel.querySelector(".carousel__track") ||
      carousel.querySelector(".book-collection");
    const prevBtn = carousel.querySelector(".carousel__nav-btn--prev");
    const nextBtn = carousel.querySelector(".carousel__nav-btn--next");

    if (track && prevBtn && nextBtn) {
      const getScrollDistance = () => {
        const firstCard = track.querySelector(".book-card");
        if (firstCard) {
          const cardWidth = firstCard.getBoundingClientRect().width;
          const cardGap = parseFloat(window.getComputedStyle(track).gap) || 14;
          return (cardWidth + cardGap) * (window.innerWidth >= 768 ? 3 : 1);
        }
        return 300;
      };

      prevBtn.addEventListener("click", () => {
        track.scrollBy({ left: -getScrollDistance(), behavior: "smooth" });
      });

      nextBtn.addEventListener("click", () => {
        track.scrollBy({ left: getScrollDistance(), behavior: "smooth" });
      });
    }
  });

  // 2. Rastreadores de Páginas e Indicador Dinâmico de Conclusão (100%)
  const rangeInputs = document.querySelectorAll(".book-card__range");
  rangeInputs.forEach((input) => {
    const card = input.closest(".book-card");
    const countOutput = card?.querySelector(".book-card__count");
    const maxPages = parseInt(input.max, 10) || 300;

    const updateCompletionState = (currentVal) => {
      if (card) {
        if (parseInt(currentVal, 10) >= maxPages) {
          card.classList.add("is-completed");
        } else {
          card.classList.remove("is-completed");
        }
      }
    };

    // Aplica o estado inicial ao carregar a página
    updateCompletionState(input.value);

    input.addEventListener("input", (e) => {
      const val = e.target.value;
      if (countOutput) {
        countOutput.textContent = `${val} / ${maxPages} pág.`;
      }
      updateCompletionState(val);
    });
  });

  // 3. Redirecionamento para o Perfil
  const userProfileToggle = document.getElementById("userProfileToggle");
  if (userProfileToggle) {
    userProfileToggle.addEventListener("click", (e) => {
      e.preventDefault();
      window.location.href = "/perfil";
    });
  }
});
