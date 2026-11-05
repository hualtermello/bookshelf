/**
 * BookShelf - Editor de Modelo de Livro para Gráfica (Padrão A4 - 210mm x 297mm)
 * Gerencia todas as páginas pré-textuais, miolo numerado e pós-textuais exigidas por gráficas.
 */
document.addEventListener("DOMContentLoaded", () => {
  const STORAGE_KEY = "bookshelf_modelo_grafica_a4_v1";

  const autorPadrao = window.NOME_USUARIO_LOGADO || "Autor(a) BookShelf";

  function criarEstadoInicial() {
    return {
      meta: {
        titulo: "",
        subtitulo: "",
        autor: autorPadrao,
        editora: "Editora BookShelf",
        capaImagemUrl: "",
        edicao: "1ª Edição",
        cidade: "Curitiba - PR",
        ano: "2026",
        isbn: "978-65-00-00000-0",
        cdd: "B869.3",
        sinopseContracapa: "",
        orelhaCapa: "",
        orelhaContracapa: "",
        outrasObras: "",
        coordenacaoEditorial: "Conselho Editorial BookShelf",
        revisao: "",
        diagramacao: "Padrão Gráfica A4 BookShelf (21 x 29,7 cm)",
        capaCredito: "",
        dedicatoria: "",
        agradecimentos: "",
        epigrafeTexto: "",
        epigrafeAutor: "",
        sumarioPersonalizado: "",
        prefacioTitulo: "Prefácio",
        prefacioTexto: "",
        prefacioAutor: "",
        posfacioBiografia: "",
        colofaoGrafica: "Gráfica Oficial BookShelf S.A.",
        colofaoPapelMiolo: "Papel Pólen Soft 80g/m²",
        colofaoPapelCapa: "Cartão Supremo 250g/m² com Laminação Fosca",
        colofaoTipografia: "Georgia 11,5/18 pt",
        colofaoTiragem: "1.000 exemplares",
      },
      paginasMiolo: [
        {
          id: "miolo_1",
          capituloTitulo: "Capítulo 1 — O Ponto de Partida",
          conteudo: "",
        },
        {
          id: "miolo_2",
          capituloTitulo: "",
          conteudo: "",
        },
      ],
    };
  }

  let estado = criarEstadoInicial();
  let indicePaginaAtual = 0;
  let modoTodasAsPaginas = false;
  let mostrarGuias = true;

  // Tenta carregar do servidor (MySQL/SQLite) ou do localStorage
  try {
    const scriptServidor = document.getElementById("dadosSalvosServidor");
    const jsonServidor = scriptServidor ? JSON.parse(scriptServidor.textContent) : null;
    if (jsonServidor && jsonServidor.meta) {
      estado = jsonServidor;
    } else {
      const local = localStorage.getItem(STORAGE_KEY);
      if (local) {
        const parsed = JSON.parse(local);
        if (parsed && parsed.meta) {
          estado = parsed;
        }
      }
    }
  } catch (e) {
    console.warn("Usando estado inicial do modelo de gráfica:", e);
  }

  function salvarLocal() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(estado));
    } catch (e) {
      // ignora erro de quota
    }
  }

  function mostrarToast(msg) {
    const toast = document.getElementById("graficaToast");
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = "block";
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.style.display = "none";
    }, 3500);
  }

  function gerarSumarioAutomatico() {
    const linhas = [];
    linhas.push("Prefácio .................................................................................... pág. viii");
    estado.paginasMiolo.forEach((p, idx) => {
      const numPag = idx + 1;
      if (p.capituloTitulo && p.capituloTitulo.trim()) {
        linhas.push(`${p.capituloTitulo.trim()} ............................................................ pág. ${numPag}`);
      }
    });
    linhas.push(`Sobre o Autor / Posfácio ......................................................... pág. ${estado.paginasMiolo.length + 1}`);
    return linhas.join("\n");
  }

  // Monta a lista completa de páginas na sequência exata da gráfica
  function obterDefinicaoPaginas() {
    const m = estado.meta;
    const paginas = [
      {
        codigo: "Capa",
        nome: "1ª Capa (Frente)",
        tipoFolha: "a4-sheet--capa",
        lado: "Externa",
        preenchida: Boolean(m.titulo.trim() && m.autor.trim() && m.editora.trim()),
        estiloExtra: m.capaImagemUrl ? `style="background: linear-gradient(180deg, rgba(20, 10, 15, 0.72) 0%, rgba(15, 5, 8, 0.88) 100%), url('${escaparAttr(m.capaImagemUrl)}') center / cover no-repeat;"` : '',
        render: () => `
          <div class="a4-body" style="justify-content: space-between; text-align: center; padding: 12mm 0; position: relative;">
            <div class="no-print" style="margin-bottom: 14px; background: rgba(0, 0, 0, 0.45); padding: 10px 14px; border-radius: 10px; border: 1px dashed rgba(255, 255, 255, 0.35);">
              <label class="a4-field-label" style="color: #facc15; margin-bottom: 6px;">Modelos de Capa Ilustrados (Imagens Fictícias Pré-definidas)</label>
              <div style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 8px;">
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">🌄 Aventura</button>
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">🌲 Fantasia</button>
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">💌 Romance</button>
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">🚀 Sci-Fi</button>
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">🌵 Sertão</button>
                <button type="button" class="btn-preset-capa" data-url="https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=1200&q=80" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">🏛️ Clássico</button>
                <button type="button" class="btn-preset-capa" data-url="" style="background: rgba(255,255,255,0.18); color: #fff; border: 1px solid rgba(255,255,255,0.35); border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">✕ Sem Imagem</button>
              </div>
              <input type="text" class="a4-input" data-meta="capaImagemUrl" value="${escaparAttr(m.capaImagemUrl || '')}" placeholder="Ou cole a URL de qualquer imagem fictícia para a capa do livro" style="font-size: 0.78rem; text-align: center; color: #fff; padding: 5px 10px;">
            </div>

            <div>
              <label class="a4-field-label">Autor(a) da Obra</label>
              <input type="text" class="a4-input" data-meta="autor" value="${escaparAttr(m.autor)}" placeholder="Digite o nome completo do autor(a)" style="text-align: center; font-size: 1.3rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
            </div>
            <div style="my: auto;">
              <label class="a4-field-label">Título Principal do Livro (Obrigatório)</label>
              <input type="text" class="a4-input" data-meta="titulo" value="${escaparAttr(m.titulo)}" placeholder="DIGITE O TÍTULO DO LIVRO" style="text-align: center; font-size: 2.3rem; font-weight: 700; margin-bottom: 14px;">
              <label class="a4-field-label">Subtítulo da Obra</label>
              <input type="text" class="a4-input" data-meta="subtitulo" value="${escaparAttr(m.subtitulo)}" placeholder="Digite o subtítulo da obra" style="text-align: center; font-size: 1.15rem; font-style: italic;">
            </div>
            <div>
              <label class="a4-field-label">Selo Editorial / Editora</label>
              <input type="text" class="a4-input" data-meta="editora" value="${escaparAttr(m.editora)}" placeholder="Nome da Editora" style="text-align: center; font-size: 1rem; font-weight: 600;">
            </div>
          </div>
        `,
        exportarHTML: () => `<h1>${escaparHTML(m.titulo)}</h1><h3>${escaparHTML(m.subtitulo)}</h3><p><strong>Autor:</strong> ${escaparHTML(m.autor)}</p><p><strong>Editora:</strong> ${escaparHTML(m.editora)}</p>`,
      },
      {
        codigo: "4ª Capa",
        nome: "Contracapa e Orelhas",
        tipoFolha: "a4-sheet--contracapa",
        lado: "Externa",
        preenchida: Boolean(m.sinopseContracapa.trim() && m.orelhaCapa.trim() && m.isbn.trim()),
        render: () => `
          <div class="a4-body" style="gap: 16px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
              <div>
                <label class="a4-field-label">Texto da 1ª Orelha (Apresentação da Obra)</label>
                <textarea class="a4-textarea" rows="5" data-meta="orelhaCapa" placeholder="Texto que ficará na orelha frontal do livro apresentando a história ao leitor...">${escaparHTML(m.orelhaCapa)}</textarea>
              </div>
              <div>
                <label class="a4-field-label">Texto da 2ª Orelha (Resumo do Autor)</label>
                <textarea class="a4-textarea" rows="5" data-meta="orelhaContracapa" placeholder="Breve biografia do autor para a orelha da contracapa...">${escaparHTML(m.orelhaContracapa)}</textarea>
              </div>
            </div>
            <div style="margin-top: 10px;">
              <label class="a4-field-label">Sinopse Oficial da Contracapa (4ª Capa)</label>
              <textarea class="a4-textarea" rows="8" data-meta="sinopseContracapa" placeholder="Escreva aqui a sinopse instigante que fica impressa na parte de trás do livro...">${escaparHTML(m.sinopseContracapa)}</textarea>
            </div>
            <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 14px;">
              <div style="flex: 1;">
                <label class="a4-field-label">Número do ISBN (Padrão Gráfica)</label>
                <input type="text" class="a4-input" data-meta="isbn" value="${escaparAttr(m.isbn)}" placeholder="978-65-00-00000-0">
              </div>
              <div style="background: #fff; color: #000; padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 0.78rem; text-align: center;">
                |||| |||| || ||||| |||| |||<br>
                <strong>ISBN ${escaparHTML(m.isbn || "978-65-00-00000-0")}</strong>
              </div>
            </div>
          </div>
        `,
        exportarHTML: () => `<p>${escaparHTML(m.sinopseContracapa)}</p><hr/><p><strong>Orelha da Capa:</strong> ${escaparHTML(m.orelhaCapa)}</p><p><strong>Orelha do Autor:</strong> ${escaparHTML(m.orelhaContracapa)}</p><p><strong>ISBN:</strong> ${escaparHTML(m.isbn)}</p>`,
      },
      {
        codigo: "Pág. i",
        nome: "Falsa Folha de Rosto (Olho)",
        tipoFolha: "a4-sheet--impar",
        lado: "Ímpar / Direita",
        preenchida: Boolean(m.titulo.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>PÁGINA i — FALSA FOLHA DE ROSTO (OLHO DO LIVRO)</span>
            <span>FRENTE / ÍMPAR (MARGEM INTERNA ESQUERDA 3cm)</span>
          </div>
          <div class="a4-body" style="justify-content: center; text-align: center;">
            <p class="no-print" style="font-size: 0.82rem; color: #64748b; margin-bottom: 18px;">
              Na tradição gráfica, a página i contém apenas o título da obra centralizado (chamado de "Olho" do livro).
            </p>
            <label class="a4-field-label">Título da Obra na Falsa Folha de Rosto</label>
            <input type="text" class="a4-input" data-meta="titulo" value="${escaparAttr(m.titulo)}" placeholder="Digite o título da obra" style="text-align: center; font-size: 1.9rem; font-weight: 700;">
          </div>
          <div class="a4-running-footer">
            <span>Formato A4 (210 × 297 mm)</span>
            <span>i</span>
          </div>
        `,
        exportarHTML: () => `<h1 style="text-align:center;">${escaparHTML(m.titulo)}</h1>`,
      },
      {
        codigo: "Pág. ii",
        nome: "Verso / Outras Obras do Autor",
        tipoFolha: "a4-sheet--par",
        lado: "Par / Esquerda",
        preenchida: Boolean(m.outrasObras.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>VERSO / PAR (MARGEM INTERNA DIREITA 3cm)</span>
            <span>PÁGINA ii — VERSO DA FALSA FOLHA DE ROSTO</span>
          </div>
          <div class="a4-body">
            <label class="a4-field-label">Outras Obras do Autor / Nota Editorial Preliminar</label>
            <textarea class="a4-textarea" rows="10" data-meta="outrasObras" placeholder="Liste outras publicações do autor ou insira 'Obra inédita publicada pelo selo editorial BookShelf'...">${escaparHTML(m.outrasObras)}</textarea>
          </div>
          <div class="a4-running-footer">
            <span>ii</span>
            <span>Formato A4 (210 × 297 mm)</span>
          </div>
        `,
        exportarHTML: () => `<p>${escaparHTML(m.outrasObras)}</p>`,
      },
      {
        codigo: "Pág. iii",
        nome: "Folha de Rosto Principal",
        tipoFolha: "a4-sheet--impar",
        lado: "Ímpar / Direita",
        preenchida: Boolean(m.titulo.trim() && m.autor.trim() && m.cidade.trim() && m.ano.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>PÁGINA iii — FOLHA DE ROSTO PRINCIPAL</span>
            <span>FRENTE / ÍMPAR</span>
          </div>
          <div class="a4-body" style="justify-content: space-between; text-align: center; padding: 10mm 0;">
            <div>
              <label class="a4-field-label">Nome Completo do Autor(a)</label>
              <input type="text" class="a4-input" data-meta="autor" value="${escaparAttr(m.autor)}" style="text-align: center; font-size: 1.25rem; font-weight: 600;">
            </div>
            <div>
              <label class="a4-field-label">Título Completo</label>
              <input type="text" class="a4-input" data-meta="titulo" value="${escaparAttr(m.titulo)}" style="text-align: center; font-size: 2rem; font-weight: 700; margin-bottom: 10px;">
              <label class="a4-field-label">Subtítulo</label>
              <input type="text" class="a4-input" data-meta="subtitulo" value="${escaparAttr(m.subtitulo)}" style="text-align: center; font-size: 1.1rem; font-style: italic; margin-bottom: 12px;">
              <label class="a4-field-label">Edição</label>
              <input type="text" class="a4-input" data-meta="edicao" value="${escaparAttr(m.edicao)}" style="text-align: center; width: 220px; margin: 0 auto;">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
              <div>
                <label class="a4-field-label">Editora</label>
                <input type="text" class="a4-input" data-meta="editora" value="${escaparAttr(m.editora)}" style="text-align: center;">
              </div>
              <div>
                <label class="a4-field-label">Cidade / UF</label>
                <input type="text" class="a4-input" data-meta="cidade" value="${escaparAttr(m.cidade)}" style="text-align: center;">
              </div>
              <div>
                <label class="a4-field-label">Ano</label>
                <input type="text" class="a4-input" data-meta="ano" value="${escaparAttr(m.ano)}" style="text-align: center;">
              </div>
            </div>
          </div>
          <div class="a4-running-footer">
            <span>Folha de Rosto ABNT</span>
            <span>iii</span>
          </div>
        `,
        exportarHTML: () => `<div style="text-align:center;"><p>${escaparHTML(m.autor)}</p><h1>${escaparHTML(m.titulo)}</h1><h3>${escaparHTML(m.subtitulo)}</h3><p>${escaparHTML(m.edicao)}</p><p>${escaparHTML(m.editora)} — ${escaparHTML(m.cidade)}, ${escaparHTML(m.ano)}</p></div>`,
      },
      {
        codigo: "Pág. iv",
        nome: "Expediente e Ficha Catalográfica",
        tipoFolha: "a4-sheet--par",
        lado: "Par / Esquerda",
        preenchida: Boolean(m.revisao.trim() && m.capaCredito.trim() && m.isbn.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>VERSO / PAR</span>
            <span>PÁGINA iv — CRÉDITOS E FICHA CATALOGRÁFICA</span>
          </div>
          <div class="a4-body" style="gap: 12px;">
            <p style="font-size: 0.9rem;">
              Copyright © ${escaparHTML(m.ano || "2026")} por <strong>${escaparHTML(m.autor || "Autor")}</strong>.<br>
              Todos os direitos reservados. Nenhuma parte desta publicação pode ser reproduzida sem autorização prévia.
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px;">
              <div>
                <label class="a4-field-label">Coordenação Editorial</label>
                <input type="text" class="a4-input" data-meta="coordenacaoEditorial" value="${escaparAttr(m.coordenacaoEditorial)}">
              </div>
              <div>
                <label class="a4-field-label">Revisão Ortográfica e Gramatical</label>
                <input type="text" class="a4-input" data-meta="revisao" value="${escaparAttr(m.revisao)}" placeholder="Nome do revisor(a)">
              </div>
              <div>
                <label class="a4-field-label">Projeto Gráfico e Capa</label>
                <input type="text" class="a4-input" data-meta="capaCredito" value="${escaparAttr(m.capaCredito)}" placeholder="Responsável pela arte da capa">
              </div>
              <div>
                <label class="a4-field-label">Classificação CDD (Biblioteconomia)</label>
                <input type="text" class="a4-input" data-meta="cdd" value="${escaparAttr(m.cdd)}" placeholder="Ex: B869.3">
              </div>
            </div>

            <div class="ficha-catalografica-box">
              <div style="text-align: center; font-weight: 700; margin-bottom: 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px;">
                Dados Internacionais de Catalogação na Publicação (CIP)
              </div>
              <p>
                <strong>${escaparHTML(m.autor || "Autor")}</strong><br>
                &nbsp;&nbsp;&nbsp;&nbsp;${escaparHTML(m.titulo || "Título da Obra")}: ${escaparHTML(m.subtitulo || "Subtítulo")} / ${escaparHTML(m.autor || "Autor")}. — ${escaparHTML(m.edicao || "1. ed.")} — ${escaparHTML(m.cidade || "Curitiba")}: ${escaparHTML(m.editora || "BookShelf")}, ${escaparHTML(m.ano || "2026")}.<br>
                &nbsp;&nbsp;&nbsp;&nbsp;${estado.paginasMiolo.length + 10} p. ; 21 x 29,7 cm (Formato A4).<br><br>
                &nbsp;&nbsp;&nbsp;&nbsp;ISBN: ${escaparHTML(m.isbn || "978-65-00-00000-0")}<br><br>
                &nbsp;&nbsp;&nbsp;&nbsp;1. Literatura Brasileira. I. Título.<br>
                <span style="float: right;">CDD ${escaparHTML(m.cdd || "B869.3")}</span>
              </p>
            </div>
          </div>
          <div class="a4-running-footer">
            <span>iv</span>
            <span>Ficha Catalográfica Padrão ABNT</span>
          </div>
        `,
        exportarHTML: () => `<p>Copyright © ${escaparHTML(m.ano)} ${escaparHTML(m.autor)}</p><p>Coordenação Editorial: ${escaparHTML(m.coordenacaoEditorial)} | Revisão: ${escaparHTML(m.revisao)} | Capa: ${escaparHTML(m.capaCredito)}</p><p>ISBN: ${escaparHTML(m.isbn)} | CDD: ${escaparHTML(m.cdd)}</p>`,
      },
      {
        codigo: "Pág. v",
        nome: "Dedicatória e Agradecimentos",
        tipoFolha: "a4-sheet--impar",
        lado: "Ímpar / Direita",
        preenchida: Boolean(m.dedicatoria.trim() && m.agradecimentos.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>PÁGINA v — DEDICATÓRIA E AGRADECIMENTOS</span>
            <span>FRENTE / ÍMPAR</span>
          </div>
          <div class="a4-body" style="justify-content: space-between;">
            <div>
              <label class="a4-field-label">Agradecimentos Especiais</label>
              <textarea class="a4-textarea" rows="8" data-meta="agradecimentos" placeholder="Escreva seus agradecimentos à família, leitores, professores e colaboradores...">${escaparHTML(m.agradecimentos)}</textarea>
            </div>
            <div style="width: 65%; margin-left: auto; margin-top: 40px;">
              <label class="a4-field-label">Dedicatória da Obra (Alinhada à direita conforme padrão gráfico)</label>
              <textarea class="a4-textarea" rows="5" data-meta="dedicatoria" placeholder="Dedico este livro a..." style="font-style: italic; text-align: right;">${escaparHTML(m.dedicatoria)}</textarea>
            </div>
          </div>
          <div class="a4-running-footer">
            <span>Elementos Pré-Textuais</span>
            <span>v</span>
          </div>
        `,
        exportarHTML: () => `<p><strong>Agradecimentos:</strong> ${escaparHTML(m.agradecimentos)}</p><p style="text-align:right;font-style:italic;">${escaparHTML(m.dedicatoria)}</p>`,
      },
      {
        codigo: "Pág. vi",
        nome: "Epígrafe",
        tipoFolha: "a4-sheet--par",
        lado: "Par / Esquerda",
        preenchida: Boolean(m.epigrafeTexto.trim() && m.epigrafeAutor.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>VERSO / PAR</span>
            <span>PÁGINA vi — EPÍGRAFE</span>
          </div>
          <div class="a4-body" style="justify-content: flex-end; padding-bottom: 40mm;">
            <div style="width: 70%; margin-left: auto;">
              <label class="a4-field-label">Frase / Citação da Epígrafe</label>
              <textarea class="a4-textarea" rows="4" data-meta="epigrafeTexto" placeholder="Insira uma frase ou pensamento que inspira a obra..." style="font-style: italic; text-align: right;">${escaparHTML(m.epigrafeTexto)}</textarea>
              <label class="a4-field-label" style="margin-top: 8px;">Autor da Citação</label>
              <input type="text" class="a4-input" data-meta="epigrafeAutor" value="${escaparAttr(m.epigrafeAutor)}" placeholder="— Nome do Autor da Citação" style="text-align: right; font-weight: 600;">
            </div>
          </div>
          <div class="a4-running-footer">
            <span>vi</span>
            <span>Epígrafe Editorial</span>
          </div>
        `,
        exportarHTML: () => `<blockquote style="text-align:right;"><em>"${escaparHTML(m.epigrafeTexto)}"</em><br/>— ${escaparHTML(m.epigrafeAutor)}</blockquote>`,
      },
      {
        codigo: "Pág. vii",
        nome: "Sumário",
        tipoFolha: "a4-sheet--impar",
        lado: "Ímpar / Direita",
        preenchida: Boolean((m.sumarioPersonalizado || gerarSumarioAutomatico()).trim()),
        render: () => {
          const sumarioValor = m.sumarioPersonalizado.trim() ? m.sumarioPersonalizado : gerarSumarioAutomatico();
          return `
            <div class="a4-running-header">
              <span>PÁGINA vii — SUMÁRIO DA EDIÇÃO</span>
              <span>FRENTE / ÍMPAR</span>
            </div>
            <div class="a4-body">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h2 style="font-size: 1.5rem; letter-spacing: 0.06em; text-transform: uppercase;">Sumário</h2>
                <button type="button" class="grafica-tool-btn no-print" id="btnAtualizarSumarioAuto">
                  Sincronizar Capítulos Automaticamente
                </button>
              </div>
              <label class="a4-field-label">Estrutura de Capítulos e Paginação</label>
              <textarea class="a4-textarea" rows="16" data-meta="sumarioPersonalizado" style="font-family: 'Courier New', monospace; font-size: 0.95rem; line-height: 2;">${escaparHTML(sumarioValor)}</textarea>
            </div>
            <div class="a4-running-footer">
              <span>Sumário</span>
              <span>vii</span>
            </div>
          `;
        },
        exportarHTML: () => `<pre>${escaparHTML(m.sumarioPersonalizado.trim() || gerarSumarioAutomatico())}</pre>`,
      },
      {
        codigo: "Pág. viii",
        nome: "Prefácio / Apresentação",
        tipoFolha: "a4-sheet--par",
        lado: "Par / Esquerda",
        preenchida: Boolean(m.prefacioTexto.trim() && m.prefacioAutor.trim()),
        render: () => `
          <div class="a4-running-header">
            <span>VERSO / PAR</span>
            <span>PÁGINA viii — PREFÁCIO / APRESENTAÇÃO</span>
          </div>
          <div class="a4-body" style="gap: 10px;">
            <label class="a4-field-label">Título da Seção</label>
            <input type="text" class="a4-input" data-meta="prefacioTitulo" value="${escaparAttr(m.prefacioTitulo)}" style="font-size: 1.4rem; font-weight: 700;">
            <label class="a4-field-label">Texto do Prefácio ou Apresentação ao Leitor</label>
            <textarea class="a4-textarea a4-miolo-textarea" style="min-height: 430px;" data-meta="prefacioTexto" placeholder="Escreva a apresentação ou prefácio contextualizando a obra para os leitores...">${escaparHTML(m.prefacioTexto)}</textarea>
            <div>
              <label class="a4-field-label">Assinatura do Prefaciador / Autor</label>
              <input type="text" class="a4-input" data-meta="prefacioAutor" value="${escaparAttr(m.prefacioAutor)}" placeholder="Nome de quem assina o prefácio" style="text-align: right; font-style: italic;">
            </div>
          </div>
          <div class="a4-running-footer">
            <span>viii</span>
            <span>Prefácio</span>
          </div>
        `,
        exportarHTML: () => `<h3>${escaparHTML(m.prefacioTitulo)}</h3><p>${escaparHTML(m.prefacioTexto)}</p><p style="text-align:right;"><em>${escaparHTML(m.prefacioAutor)}</em></p>`,
      },
    ];

    // Páginas numeradas do Miolo (Pág. 1, 2, 3...)
    estado.paginasMiolo.forEach((pagMiolo, idx) => {
      const numeroArabico = idx + 1;
      const ehImpar = numeroArabico % 2 === 1;
      const palavras = contarPalavras(pagMiolo.conteudo);
      paginas.push({
        codigo: `Pág. ${numeroArabico}`,
        nome: pagMiolo.capituloTitulo
          ? `Miolo ${numeroArabico}: ${pagMiolo.capituloTitulo.slice(0, 22)}`
          : `Página ${numeroArabico} do Miolo`,
        tipoFolha: ehImpar ? "a4-sheet--impar" : "a4-sheet--par",
        lado: ehImpar ? "Ímpar / Direita" : "Par / Esquerda",
        ehMiolo: true,
        indiceMiolo: idx,
        preenchida: Boolean(pagMiolo.conteudo && pagMiolo.conteudo.trim().length >= 20),
        render: () => `
          <div class="a4-running-header">
            <span>${ehImpar ? escaparHTML(m.titulo || "TÍTULO DA OBRA") : escaparHTML(m.autor || "NOME DO AUTOR")}</span>
            <span>PÁGINA ${numeroArabico} (${ehImpar ? "FRENTE / ÍMPAR" : "VERSO / PAR"})</span>
          </div>
          <div class="a4-body" style="gap: 10px;">
            <div>
              <label class="a4-field-label">Título do Capítulo (Deixe em branco se for continuação da página anterior)</label>
              <input type="text" class="a4-input" data-miolo-idx="${idx}" data-miolo-field="capituloTitulo" value="${escaparAttr(pagMiolo.capituloTitulo)}" placeholder="Ex: Capítulo ${numeroArabico} — Título do Capítulo" style="font-size: 1.35rem; font-weight: 700; margin-bottom: 6px;">
            </div>
            <div style="flex: 1; display: flex; flex-direction: column;">
              <div class="no-print" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <label class="a4-field-label" style="margin-bottom: 0;">Texto da Página ${numeroArabico} (Mancha Gráfica A4)</label>
                <span style="font-size: 0.75rem; color: #64748b;" id="contadorPalavrasMiolo_${idx}">${palavras} palavras (~350-450 recomendadas por página A4)</span>
              </div>
              <textarea class="a4-textarea a4-miolo-textarea" data-miolo-idx="${idx}" data-miolo-field="conteudo" placeholder="Escreva aqui o conteúdo literário da página ${numeroArabico} do seu livro...">${escaparHTML(pagMiolo.conteudo)}</textarea>
            </div>
          </div>
          <div class="a4-running-footer">
            <span>${ehImpar ? "Margem Interna Esquerda: 30mm" : numeroArabico}</span>
            <span>${ehImpar ? numeroArabico : "Margem Interna Direita: 30mm"}</span>
          </div>
        `,
        exportarHTML: () => `${pagMiolo.capituloTitulo ? `<h2>${escaparHTML(pagMiolo.capituloTitulo)}</h2>` : ""}<p>${escaparHTML(pagMiolo.conteudo)}</p>`,
      });
    });

    const numPosfacio = estado.paginasMiolo.length + 1;
    const numColofao = estado.paginasMiolo.length + 2;

    // Pós-textual 1: Posfácio e Sobre o Autor
    paginas.push({
      codigo: `Pág. ${numPosfacio}`,
      nome: "Posfácio e Sobre o Autor",
      tipoFolha: numPosfacio % 2 === 1 ? "a4-sheet--impar" : "a4-sheet--par",
      lado: numPosfacio % 2 === 1 ? "Ímpar / Direita" : "Par / Esquerda",
      preenchida: Boolean(m.posfacioBiografia.trim()),
      render: () => `
        <div class="a4-running-header">
          <span>ELEMENTOS PÓS-TEXTUAIS</span>
          <span>PÁGINA ${numPosfacio} — SOBRE O AUTOR E POSFÁCIO</span>
        </div>
        <div class="a4-body" style="gap: 10px;">
          <h2 style="font-size: 1.45rem; margin-bottom: 6px;">Sobre o Autor(a) e Nota Final</h2>
          <label class="a4-field-label">Biografia Completa e Posfácio da Edição</label>
          <textarea class="a4-textarea a4-miolo-textarea" data-meta="posfacioBiografia" placeholder="Escreva a trajetória literária do autor, notas finais sobre o processo de criação da obra e canais de contato...">${escaparHTML(m.posfacioBiografia)}</textarea>
        </div>
        <div class="a4-running-footer">
          <span>Sobre o Autor</span>
          <span>${numPosfacio}</span>
        </div>
      `,
      exportarHTML: () => `<h2>Sobre o Autor e Posfácio</h2><p>${escaparHTML(m.posfacioBiografia)}</p>`,
    });

    // Pós-textual 2: Colofão (Ficha Técnica de Impressão da Gráfica)
    paginas.push({
      codigo: `Pág. ${numColofao}`,
      nome: "Colofão (Ficha da Gráfica)",
      tipoFolha: numColofao % 2 === 1 ? "a4-sheet--impar" : "a4-sheet--par",
      lado: numColofao % 2 === 1 ? "Ímpar / Direita" : "Par / Esquerda",
      preenchida: Boolean(
        m.colofaoGrafica.trim() &&
          m.colofaoPapelMiolo.trim() &&
          m.colofaoTipografia.trim() &&
          m.colofaoTiragem.trim()
      ),
      render: () => `
        <div class="a4-running-header">
          <span>COLOFÃO — ESPECIFICAÇÕES TÉCNICAS PARA A GRÁFICA</span>
          <span>PÁGINA ${numColofao} (ENCERRAMENTO DO MIOLO)</span>
        </div>
        <div class="a4-body" style="justify-content: center; gap: 14px;">
          <div style="border: 1px solid #cbd5e1; padding: 24px; border-radius: 10px; background: #fafaf9;">
            <h3 style="text-align: center; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 16px; color: var(--bg-nav);">
              Colofão — Ordem de Impressão Gráfica
            </h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div>
                <label class="a4-field-label">Nome da Gráfica / Impressor</label>
                <input type="text" class="a4-input" data-meta="colofaoGrafica" value="${escaparAttr(m.colofaoGrafica)}">
              </div>
              <div>
                <label class="a4-field-label">Papel do Miolo (Gramatura)</label>
                <input type="text" class="a4-input" data-meta="colofaoPapelMiolo" value="${escaparAttr(m.colofaoPapelMiolo)}">
              </div>
              <div>
                <label class="a4-field-label">Papel da Capa e Acabamento</label>
                <input type="text" class="a4-input" data-meta="colofaoPapelCapa" value="${escaparAttr(m.colofaoPapelCapa)}">
              </div>
              <div>
                <label class="a4-field-label">Tipografia e Corpo da Fonte</label>
                <input type="text" class="a4-input" data-meta="colofaoTipografia" value="${escaparAttr(m.colofaoTipografia)}">
              </div>
              <div>
                <label class="a4-field-label">Tiragem da Edição</label>
                <input type="text" class="a4-input" data-meta="colofaoTiragem" value="${escaparAttr(m.colofaoTiragem)}">
              </div>
            </div>
            <p style="margin-top: 20px; text-align: center; font-style: italic; font-size: 0.92rem; line-height: 1.7;">
              Este livro foi composto na fonte <strong>${escaparHTML(m.colofaoTipografia)}</strong>, formato fechado <strong>A4 (210 × 297 mm)</strong>, impresso sobre <strong>${escaparHTML(m.colofaoPapelMiolo)}</strong> com capa em <strong>${escaparHTML(m.colofaoPapelCapa)}</strong> nas oficinas da <strong>${escaparHTML(m.colofaoGrafica)}</strong> em ${escaparHTML(m.cidade)}, no ano de ${escaparHTML(m.ano)}, com tiragem de ${escaparHTML(m.colofaoTiragem)}.
            </p>
          </div>
        </div>
        <div class="a4-running-footer">
          <span>Colofão Gráfico A4</span>
          <span>${numColofao}</span>
        </div>
      `,
      exportarHTML: () => `<p style="text-align:center;font-style:italic;">Este livro foi composto em ${escaparHTML(m.colofaoTipografia)}, formato A4 (210 × 297 mm), impresso em ${escaparHTML(m.colofaoPapelMiolo)} pela ${escaparHTML(m.colofaoGrafica)} (${escaparHTML(m.ano)}). Tiragem: ${escaparHTML(m.colofaoTiragem)}.</p>`,
    });

    return paginas;
  }

  function escaparHTML(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escaparAttr(str) {
    return escaparHTML(str).replace(/"/g, "&quot;");
  }

  function contarPalavras(str) {
    const limpo = String(str || "").trim();
    if (!limpo) return 0;
    return limpo.split(/\s+/).length;
  }

  function atualizarSidebarEProgresso(paginas) {
    const listaEl = document.getElementById("listaPaginasSidebar");
    const badgeTotal = document.getElementById("badgeTotalPaginas");
    const progressoLabel = document.getElementById("progressoLabel");
    const progressoFill = document.getElementById("progressoFill");

    const total = paginas.length;
    const preenchidas = paginas.filter((p) => p.preenchida).length;
    const pct = Math.round((preenchidas / total) * 100);

    if (badgeTotal) badgeTotal.textContent = `${total} págs.`;
    if (progressoLabel) {
      progressoLabel.textContent = `${preenchidas} de ${total} páginas preenchidas (${pct}%)`;
    }
    if (progressoFill) {
      progressoFill.style.width = `${pct}%`;
    }

    if (listaEl) {
      listaEl.innerHTML = paginas
        .map(
          (p, i) => `
          <li class="grafica-page-item ${!modoTodasAsPaginas && i === indicePaginaAtual ? "is-active" : ""}" data-page-index="${i}">
            <div class="grafica-page-item__left">
              <span class="grafica-page-item__num">${p.codigo}</span>
              <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escaparHTML(p.nome)}</span>
            </div>
            <span class="grafica-page-item__status ${p.preenchida ? "is-done" : "is-pending"}" title="${p.preenchida ? "Página preenchida" : "Página pendente de preenchimento"}">
              ${p.preenchida ? "✓" : "!"}
            </span>
          </li>
        `
        )
        .join("");

      listaEl.querySelectorAll(".grafica-page-item").forEach((item) => {
        item.addEventListener("click", () => {
          const idx = parseInt(item.getAttribute("data-page-index"), 10);
          indicePaginaAtual = idx;
          if (modoTodasAsPaginas) {
            const targetSheet = document.getElementById(`folha_a4_${idx}`);
            targetSheet?.scrollIntoView({ behavior: "smooth", block: "start" });
          } else {
            renderizarTudo();
          }
        });
      });
    }
  }

  function conectarEventosDosCampos() {
    const container = document.getElementById("a4SheetsContainer");
    if (!container) return;

    container.querySelectorAll("[data-meta]").forEach((el) => {
      el.addEventListener("input", (e) => {
        const chave = e.target.getAttribute("data-meta");
        estado.meta[chave] = e.target.value;
        salvarLocal();
        const paginas = obterDefinicaoPaginas();
        atualizarSidebarEProgresso(paginas);
        atualizarBarraStatusInferior(paginas);
      });
      if (el.getAttribute("data-meta") === "capaImagemUrl") {
        el.addEventListener("change", () => {
          renderizarTudo();
        });
      }
    });

    container.querySelectorAll(".btn-preset-capa").forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = btn.getAttribute("data-url");
        estado.meta.capaImagemUrl = url;
        salvarLocal();
        renderizarTudo();
        mostrarToast(url ? "Modelo de imagem fictícia de capa aplicado com sucesso!" : "Imagem de capa removida.");
      });
    });

    container.querySelectorAll("[data-miolo-idx]").forEach((el) => {
      el.addEventListener("input", (e) => {
        const idx = parseInt(e.target.getAttribute("data-miolo-idx"), 10);
        const campo = e.target.getAttribute("data-miolo-field");
        if (estado.paginasMiolo[idx]) {
          estado.paginasMiolo[idx][campo] = e.target.value;
          if (campo === "conteudo") {
            const contador = document.getElementById(`contadorPalavrasMiolo_${idx}`);
            if (contador) {
              contador.textContent = `${contarPalavras(e.target.value)} palavras (~350-450 recomendadas por página A4)`;
            }
          }
          salvarLocal();
          const paginas = obterDefinicaoPaginas();
          atualizarSidebarEProgresso(paginas);
          atualizarBarraStatusInferior(paginas);
        }
      });
    });

    const btnSyncSumario = document.getElementById("btnAtualizarSumarioAuto");
    if (btnSyncSumario) {
      btnSyncSumario.addEventListener("click", () => {
        estado.meta.sumarioPersonalizado = gerarSumarioAutomatico();
        salvarLocal();
        renderizarTudo();
        mostrarToast("Sumário atualizado com os capítulos atuais do miolo!");
      });
    }
  }

  function atualizarBarraStatusInferior(paginas) {
    const pagAtual = paginas[indicePaginaAtual] || paginas[0];
    const indicador = document.getElementById("indicadorPaginaAtual");
    const statusInf = document.getElementById("statusPreenchimentoPagina");
    const btnAnt = document.getElementById("btnPaginaAnterior");
    const btnProx = document.getElementById("btnProximaPagina");
    const btnRemoverMiolo = document.getElementById("btnRemoverPaginaMiolo");

    if (indicador && pagAtual) {
      indicador.textContent = modoTodasAsPaginas
        ? `Exibindo Todas as ${paginas.length} Folhas A4 (Modo Revisão de Gráfica)`
        : `${pagAtual.codigo} — ${pagAtual.nome} (${pagAtual.lado})`;
    }

    if (statusInf && pagAtual) {
      statusInf.textContent = pagAtual.preenchida
        ? "✓ Página preenchida conforme o modelo da gráfica"
        : "○ Preencha os campos desta página para concluir o modelo";
      statusInf.style.color = pagAtual.preenchida ? "#15803d" : "#b45309";
    }

    if (btnAnt) btnAnt.disabled = indicePaginaAtual <= 0;
    if (btnProx) btnProx.disabled = indicePaginaAtual >= paginas.length - 1;

    if (btnRemoverMiolo) {
      if (!modoTodasAsPaginas && pagAtual && pagAtual.ehMiolo && estado.paginasMiolo.length > 1) {
        btnRemoverMiolo.style.display = "inline-flex";
      } else {
        btnRemoverMiolo.style.display = "none";
      }
    }
  }

  function renderizarTudo() {
    const paginas = obterDefinicaoPaginas();
    if (indicePaginaAtual >= paginas.length) {
      indicePaginaAtual = paginas.length - 1;
    }

    const container = document.getElementById("a4SheetsContainer");
    const navInferior = document.getElementById("navPaginacaoInferior");

    if (container) {
      if (modoTodasAsPaginas) {
        container.innerHTML = paginas
          .map(
            (p, idx) => `
            <article class="a4-sheet ${p.tipoFolha} ${mostrarGuias ? "show-guides" : ""}" id="folha_a4_${idx}" ${p.estiloExtra || ""}>
              ${p.render()}
            </article>
          `
          )
          .join("");
        if (navInferior) navInferior.style.display = "none";
      } else {
        const p = paginas[indicePaginaAtual];
        container.innerHTML = `
          <article class="a4-sheet ${p.tipoFolha} ${mostrarGuias ? "show-guides" : ""}" id="folha_a4_${indicePaginaAtual}" ${p.estiloExtra || ""}>
            ${p.render()}
          </article>
        `;
        if (navInferior) navInferior.style.display = "flex";
      }
    }

    atualizarSidebarEProgresso(paginas);
    atualizarBarraStatusInferior(paginas);
    conectarEventosDosCampos();
  }

  // Botões de navegação Anterior / Próxima
  document.getElementById("btnPaginaAnterior")?.addEventListener("click", () => {
    if (indicePaginaAtual > 0) {
      indicePaginaAtual--;
      renderizarTudo();
      window.scrollTo({ top: 140, behavior: "smooth" });
    }
  });

  document.getElementById("btnProximaPagina")?.addEventListener("click", () => {
    const paginas = obterDefinicaoPaginas();
    if (indicePaginaAtual < paginas.length - 1) {
      indicePaginaAtual++;
      renderizarTudo();
      window.scrollTo({ top: 140, behavior: "smooth" });
    }
  });

  // Adicionar nova página de miolo ou novo capítulo
  document.getElementById("btnAddPaginaMiolo")?.addEventListener("click", () => {
    const novoNum = estado.paginasMiolo.length + 1;
    estado.paginasMiolo.push({
      id: `miolo_${Date.now()}`,
      capituloTitulo: "",
      conteudo: "",
    });
    salvarLocal();
    // Índice da página recém-criada (8 pré-textuais + índice no miolo)
    indicePaginaAtual = 8 + (novoNum - 1);
    renderizarTudo();
    mostrarToast(`Página ${novoNum} do miolo adicionada ao modelo A4!`);
  });

  document.getElementById("btnAddNovoCapitulo")?.addEventListener("click", () => {
    const novoNum = estado.paginasMiolo.length + 1;
    const totalCaps =
      estado.paginasMiolo.filter((p) => p.capituloTitulo && p.capituloTitulo.trim()).length + 1;
    estado.paginasMiolo.push({
      id: `miolo_${Date.now()}`,
      capituloTitulo: `Capítulo ${totalCaps} — Novo Capítulo`,
      conteudo: "",
    });
    salvarLocal();
    indicePaginaAtual = 8 + (novoNum - 1);
    renderizarTudo();
    mostrarToast(`Capítulo ${totalCaps} adicionado na Página ${novoNum} do miolo!`);
  });

  document.getElementById("btnRemoverPaginaMiolo")?.addEventListener("click", () => {
    const paginas = obterDefinicaoPaginas();
    const atual = paginas[indicePaginaAtual];
    if (atual && atual.ehMiolo && estado.paginasMiolo.length > 1) {
      estado.paginasMiolo.splice(atual.indiceMiolo, 1);
      salvarLocal();
      renderizarTudo();
      mostrarToast("Página removida do miolo.");
    }
  });

  // Inserir travessão literário (—) no campo focado
  document.getElementById("btnInserirTravessao")?.addEventListener("click", () => {
    const ativo = document.activeElement;
    if (ativo && (ativo.tagName === "TEXTAREA" || ativo.tagName === "INPUT")) {
      const ini = ativo.selectionStart || 0;
      const fim = ativo.selectionEnd || 0;
      const val = ativo.value;
      ativo.value = val.slice(0, ini) + "— " + val.slice(fim);
      ativo.dispatchEvent(new Event("input", { bubbles: true }));
      ativo.focus();
      ativo.setSelectionRange(ini + 2, ini + 2);
    } else {
      mostrarToast("Clique primeiro dentro de um campo de texto da página para inserir o travessão (—).");
    }
  });

  // Alternar Modo Página a Página vs Todas as Páginas
  const btnToggleView = document.getElementById("btnToggleViewMode");
  btnToggleView?.addEventListener("click", () => {
    modoTodasAsPaginas = !modoTodasAsPaginas;
    btnToggleView.textContent = modoTodasAsPaginas
      ? "Voltar ao Modo Página por Página"
      : "Ver Todas as Páginas (Modo Gráfica)";
    renderizarTudo();
  });

  // Mostrar / ocultar marcas de corte e sangria
  const chkGuias = document.getElementById("chkMostrarGuias");
  chkGuias?.addEventListener("change", (e) => {
    mostrarGuias = e.target.checked;
    document.querySelectorAll(".a4-sheet").forEach((s) => {
      s.classList.toggle("show-guides", mostrarGuias);
    });
  });

  // Botão Preencher Exemplo Guia (preenche todas as páginas para demonstração/base)
  document.getElementById("btnPreencherExemplo")?.addEventListener("click", () => {
    estado.meta = {
      titulo: "As Crônicas do Horizonte Vermelho",
      subtitulo: "Memórias e ventos de uma jornada literária",
      autor: autorPadrao,
      editora: "Editora BookShelf",
      capaImagemUrl: "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=1200&q=80",
      edicao: "1ª Edição",
      cidade: "Curitiba - PR",
      ano: "2026",
      isbn: "978-65-89123-45-6",
      cdd: "B869.3",
      sinopseContracapa:
        "Em 'As Crônicas do Horizonte Vermelho', acompanhamos uma narrativa envolvente sobre memória, coragem e descoberta. Uma edição preparada integralmente no padrão editorial de gráfica A4 do BookShelf.",
      orelhaCapa:
        "Esta obra reúne capítulos cuidadosamente diagramados que convidam o leitor a mergulhar nos mistérios das colinas avermelhadas.",
      orelhaContracapa: `${autorPadrao} é escritor(a) e membro da comunidade literária BookShelf, dedicando-se à criação de romances e contos brasileiros.`,
      outrasObras: "Obras publicadas pelo selo BookShelf:\n— Cadernos do Crepúsculo (Contos)\n— As Crônicas do Horizonte Vermelho (Romance)",
      coordenacaoEditorial: "Conselho Editorial BookShelf",
      revisao: "Equipe de Revisão Literária BookShelf",
      diagramacao: "Padrão Gráfica A4 BookShelf (21 x 29,7 cm)",
      capaCredito: "Estúdio Gráfico BookShelf",
      dedicatoria: "Dedico esta obra a todos os leitores e sonhadores que acreditam no poder transformador dos livros.",
      agradecimentos:
        "Agradeço à minha família, aos professores e aos leitores da plataforma BookShelf pelo apoio constante em cada capítulo escrito.",
      epigrafeTexto: "Um livro é um sonho que você segura em suas mãos.",
      epigrafeAutor: "Neil Gaiman",
      sumarioPersonalizado: "",
      prefacioTitulo: "Prefácio da Primeira Edição",
      prefacioTexto:
        "Abrir as páginas de um livro recém-saído da gráfica é sempre um ritual de encantamento. Esta obra nasceu do desejo de compartilhar histórias que atravessam o tempo, respeitando cada detalhe da arte editorial — desde a falsa folha de rosto até o colofão.",
      prefacioAutor: autorPadrao,
      posfacioBiografia: `${autorPadrao} escreveu esta obra utilizando o Modelo Oficial para Gráfica do BookShelf. Apaixonado(a) pela literatura clássica e contemporânea, busca aproximar novos leitores da experiência completa do livro impresso e digital.`,
      colofaoGrafica: "Gráfica Oficial BookShelf S.A.",
      colofaoPapelMiolo: "Papel Pólen Soft 80g/m²",
      colofaoPapelCapa: "Cartão Supremo 250g/m² com Laminação Fosca",
      colofaoTipografia: "Georgia 11,5/18 pt",
      colofaoTiragem: "1.000 exemplares",
    };

    estado.paginasMiolo = [
      {
        id: "miolo_1",
        capituloTitulo: "Capítulo 1 — O Despertar na Serra",
        conteudo:
          "O sol despontava lentamente sobre as montanhas quando as primeiras badaladas ecoaram pelo vale silencioso. Na varanda da antiga biblioteca, as folhas datilografadas repousavam sobre a mesa de carvalho, aguardando a última revisão antes de seguirem para as prensas da gráfica.\n— Hoje concluiremos cada página desta história — murmurou o autor, observando a luz dourada tocar o papel.",
      },
      {
        id: "miolo_2",
        capituloTitulo: "Capítulo 2 — Os Caminhos de Papel e Tinta",
        conteudo:
          "Ao longo das semanas seguintes, cada capítulo ganhou forma e ritmo. As margens espelhadas garantiam que, quando as folhas fossem dobradas, costuradas e coladas na lombada, nenhuma palavra se perdesse no centro do livro. Era a união perfeita entre a imaginação literária e o ofício gráfico.",
      },
    ];
    estado.meta.sumarioPersonalizado = gerarSumarioAutomatico();
    salvarLocal();
    renderizarTudo();
    mostrarToast("Todas as páginas foram preenchidas com o modelo guia! Você pode editar qualquer campo.");
  });

  function montarPayloadServidor() {
    const paginasDefinicao = obterDefinicaoPaginas();
    return {
      meta: estado.meta,
      paginasMiolo: estado.paginasMiolo,
      paginas: paginasDefinicao.map((p) => ({
        codigo: p.codigo,
        titulo_exibicao: `${p.codigo} — ${p.nome}`,
        html_formatado: p.exportarHTML(),
      })),
    };
  }

  // Salvar no servidor (MySQL / SQLite) + navegador
  document.getElementById("btnSalvarModelo")?.addEventListener("click", async () => {
    salvarLocal();
    try {
      const resp = await fetch("/api/modelo-grafica/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(montarPayloadServidor()),
      });
      const data = await resp.json();
      mostrarToast(data.mensagem || "Modelo salvo com sucesso!");
    } catch (e) {
      mostrarToast("Salvo localmente neste navegador!");
    }
  });

  // Imprimir / Gerar PDF A4 para Gráfica (garante que todas as páginas estejam renderizadas na hora da impressão)
  document.getElementById("btnImprimirGrafica")?.addEventListener("click", () => {
    const paginas = obterDefinicaoPaginas();
    const pendentes = paginas.filter((p) => !p.preenchida);
    if (pendentes.length > 0) {
      const confirmar = window.confirm(
        `Atenção: Ainda há ${pendentes.length} página(s) com campos em branco (${pendentes
          .map((p) => p.codigo)
          .join(", ")}).\n\nDeseja gerar a impressão A4 mesmo assim?`
      );
      if (!confirmar) return;
    }

    const modoAnterior = modoTodasAsPaginas;
    modoTodasAsPaginas = true;
    renderizarTudo();
    setTimeout(() => {
      window.print();
      modoTodasAsPaginas = modoAnterior;
      renderizarTudo();
    }, 150);
  });

  // Validar todas as páginas e Publicar Livro na Biblioteca BookShelf
  document.getElementById("btnPublicarModelo")?.addEventListener("click", async () => {
    const paginas = obterDefinicaoPaginas();
    const pendentes = paginas.filter((p) => !p.preenchida);

    if (pendentes.length > 0) {
      const primeiraPendenteIdx = paginas.findIndex((p) => !p.preenchida);
      indicePaginaAtual = primeiraPendenteIdx >= 0 ? primeiraPendenteIdx : 0;
      modoTodasAsPaginas = false;
      renderizarTudo();
      mostrarToast(
        `Preencha todas as páginas antes de enviar! Faltam ${pendentes.length} página(s) (ex: ${pendentes[0].codigo} - ${pendentes[0].nome}).`
      );
      return;
    }

    try {
      const resp = await fetch("/api/modelo-grafica/publicar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(montarPayloadServidor()),
      });
      const data = await resp.json();
      if (data.ok) {
        mostrarToast(data.mensagem || "Livro publicado com sucesso!");
        if (data.url_leitura) {
          setTimeout(() => {
            window.location.href = data.url_leitura;
          }, 1200);
        }
      } else {
        mostrarToast(data.erro || "Erro ao publicar o livro.");
      }
    } catch (e) {
      mostrarToast("Erro de conexão ao tentar publicar a obra.");
    }
  });

  // Renderização inicial
  renderizarTudo();
});
