(() => {
  const $ = (id) => document.getElementById(id);
  let estado = null;
  let baseRelogio = null;
  let pinProfessor = "";
  let professorAutenticado = false;

  function atualizarVisibilidadeAlunos() {
    $("secaoAlunos").hidden = !professorAutenticado;
  }

  function mostrarAviso(mensagem, erro = false) {
    const aviso = $("aviso");
    aviso.textContent = mensagem || "";
    aviso.classList.toggle("error", erro);
    aviso.classList.toggle("success", Boolean(mensagem) && !erro);
  }

  async function chamarApi(url, { metodo = "GET", corpo, autenticada = false } = {}) {
    const cabecalhos = {};
    if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
    if (autenticada) cabecalhos["X-PIN"] = pinProfessor;
    const resposta = await fetch(url, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
    let dados;
    try {
      dados = await resposta.json();
    } catch {
      dados = {};
    }
    if (!resposta.ok) {
      throw new Error(typeof dados.detail === "string" ? dados.detail : "Não foi possível concluir a ação.");
    }
    return dados;
  }

  async function atualizar() {
    try {
      if (!professorAutenticado) {
        estado = null;
        baseRelogio = null;
        $("modo").textContent = "Entre com o PIN do professor";
        $("controlesDemo").hidden = true;
        atualizarVisibilidadeAlunos();
        return;
      }
      estado = await chamarApi("/api/estado", { autenticada: true });
      baseRelogio = { agora: estado.agora, local: performance.now() };
      $("modo").textContent = estado.demo ? "Modo simulação" : "Modo produção";
      $("modo").classList.toggle("production", !estado.demo);
      $("controlesDemo").hidden = !estado.demo;
      preencherTurmas();
      desenharAlunos();
      atualizarVisibilidadeAlunos();
      $("atualizado").textContent = `Limite: ${formatarTempo(estado.limite)}`;
    } catch (erro) {
      if (erro.message === "PIN do professor incorreto.") {
        pinProfessor = "";
        professorAutenticado = false;
        sessionStorage.removeItem("pinProfessor");
        $("acoesProfessor").hidden = true;
        $("formLogin").hidden = false;
        $("pin").value = "";
        atualizarVisibilidadeAlunos();
        $("modo").textContent = "Autenticação necessária";
        mostrarAviso("Sessão expirada. Entre novamente com o PIN do professor.", true);
        return;
      }
      mostrarAviso(`Não foi possível conectar ao servidor: ${erro.message}`, true);
      $("modo").textContent = "Sem conexão";
    }
  }

  function agora() {
    if (!baseRelogio) return 0;
    return baseRelogio.agora + (performance.now() - baseRelogio.local) / 1000;
  }

  function formatarTempo(segundos) {
    const total = Math.max(0, Math.floor(segundos));
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  }

  function elemento(tag, classe, texto) {
    const node = document.createElement(tag);
    if (classe) node.className = classe;
    if (texto !== undefined) node.textContent = texto;
    return node;
  }

  function preencherTurmas() {
    const seletor = $("turma");
    const selecionada = seletor.value;
    seletor.replaceChildren(...estado.turmas.map((turma) => {
      const opcao = elemento("option", "", turma);
      opcao.value = turma;
      return opcao;
    }));
    if (estado.turmas.includes(selecionada)) seletor.value = selecionada;
    else if (estado.turmas.length) seletor.value = estado.turmas[0];
  }

  function desenharAlunos() {
    const lista = $("listaAlunos");
    const turma = $("turma").value;
    const alunos = estado.alunos.filter((aluno) => aluno.turma === turma);
    lista.replaceChildren();
    $("turmaTitulo").textContent = turma || "Turmas";
    if (!alunos.length) {
      lista.append(elemento("p", "empty", "Nenhum aluno configurado nesta turma."));
      return;
    }

    alunos.forEach((aluno) => {
      const fora = aluno.saida !== null;
      const problema = aluno.estouros >= estado.max;
      const item = elemento("article", `student-card${fora ? " is-out" : ""}${problema ? " is-problem" : ""}`);
      const info = elemento("div", "student-info");
      const nome = elemento("h3", "student-name", aluno.nome);
      const id = elemento("span", "student-id", `ID ${aluno.id}`);
      info.append(nome, id);

      const status = elemento("div", "student-status");
      const textoStatus = fora
        ? `Fora há ${formatarTempo(agora() - aluno.saida)}`
        : problema
          ? (aluno.liberado ? "Problema — 1 saída liberada" : "Aluno problema — bloqueado")
          : "Na sala";
      status.append(elemento("span", `status-label${fora ? " out" : problema ? " problem" : ""}`, textoStatus));
      status.append(elemento("span", "strikes", `Atrasos: ${aluno.estouros}/${estado.max}`));

      const acoes = elemento("div", "student-actions");
      const tocar = elemento("button", "button primary", fora ? "Registrar retorno" : "Registrar saída");
      tocar.type = "button";
      tocar.addEventListener("click", () =>
        executarAcao(`/api/digital/${aluno.id}`, { autenticada: true }));
      acoes.append(tocar);

      if (estado.demo && professorAutenticado && !problema) {
        const simular = elemento("button", "button secondary", "Simular 3/3 atrasos");
        simular.type = "button";
        simular.addEventListener("click", () =>
          executarAcao(`/api/demo/estouro/${aluno.id}`, { autenticada: true }));
        acoes.append(simular);
      }

      if (professorAutenticado && problema) {
        const liberar = elemento("button", "button secondary", "Liberar 1 saída");
        liberar.type = "button";
        liberar.addEventListener("click", () =>
          executarAcao(`/api/professor/liberar/${aluno.id}`, { autenticada: true }));
        acoes.append(liberar);
      }

      item.append(info, status, acoes);
      lista.append(item);
    });
  }

  async function executarAcao(url, opcoes = {}) {
    mostrarAviso("");
    try {
      await chamarApi(url, { metodo: "POST", ...opcoes });
      await atualizar();
    } catch (erro) {
      mostrarAviso(erro.message, true);
    }
  }

  $("formLogin").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    pinProfessor = $("pin").value;
    try {
      await chamarApi("/api/professor/validar", {
        metodo: "POST",
        autenticada: true,
      });
      sessionStorage.setItem("pinProfessor", pinProfessor);
      professorAutenticado = true;
      $("acoesProfessor").hidden = false;
      $("formLogin").hidden = true;
      $("erroLogin").hidden = true;
      atualizarVisibilidadeAlunos();
      await atualizar();
    } catch (erro) {
      pinProfessor = "";
      professorAutenticado = false;
      $("erroLogin").textContent = erro.message;
      $("erroLogin").hidden = false;
    }
  });

  $("sairProfessor").addEventListener("click", () => {
    pinProfessor = "";
    professorAutenticado = false;
    sessionStorage.removeItem("pinProfessor");
    $("pin").value = "";
    $("acoesProfessor").hidden = true;
    $("formLogin").hidden = false;
    atualizarVisibilidadeAlunos();
    atualizar();
  });

  $("turma").addEventListener("change", desenharAlunos);
  $("reiniciar").addEventListener("click", async () => {
    if (!window.confirm("Reiniciar a simulação e apagar os registros de teste?")) return;
    await executarAcao("/api/demo/reiniciar", { autenticada: true });
  });

  pinProfessor = sessionStorage.getItem("pinProfessor") || "";
  atualizar();
  if (pinProfessor) {
    chamarApi("/api/professor/validar", { metodo: "POST", autenticada: true })
      .then(() => {
        professorAutenticado = true;
        $("acoesProfessor").hidden = false;
        $("formLogin").hidden = true;
        return atualizar();
      })
      .catch(() => {
        pinProfessor = "";
        professorAutenticado = false;
        sessionStorage.removeItem("pinProfessor");
        if (estado) desenharAlunos();
      });
  }
  window.setInterval(atualizar, 2000);
  window.setInterval(() => {
    if (estado && professorAutenticado) desenharAlunos();
  }, 500);
  atualizarVisibilidadeAlunos();
})();
