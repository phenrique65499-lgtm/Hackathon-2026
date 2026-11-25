(() => {
  const $ = (id) => document.getElementById(id);

  function elemento(tag, classe, texto) {
    const node = document.createElement(tag);
    if (classe) node.className = classe;
    if (texto !== undefined) node.textContent = texto;
    return node;
  }

  function desenhar(alunos) {
    const lista = $("listaProblema");
    lista.replaceChildren();
    $("semProblema").hidden = alunos.length > 0;
    alunos.forEach((aluno) => {
      const item = elemento("article", "student-card is-problem");
      const info = elemento("div", "student-info");
      info.append(elemento("h3", "student-name", aluno.nome));
      info.append(elemento("span", "student-id", aluno.turma));
      const status = elemento("div", "student-status");
      status.append(elemento("span", "status-label problem", "Aluno problema!"));
      const acoes = elemento("div", "student-actions");
      const zerar = elemento("button", "button secondary", "Zerar atrasos");
      zerar.type = "button";
      zerar.disabled = !$("senhaSecretaria").value.trim();
      zerar.addEventListener("click", () => zerarAtrasos(aluno.id));
      acoes.append(zerar);
      item.append(info, status, acoes);
      lista.append(item);
    });
  }

  async function zerarAtrasos(alunoId) {
    $("avisoSecretaria").hidden = true;
    const senha = $("senhaSecretaria").value;
    try {
      const resposta = await fetch(`/api/secretaria/zerar/${alunoId}`, {
        method: "POST",
        headers: { "X-SENHA": senha },
      });
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => ({}));
        throw new Error(typeof dados.detail === "string" ? dados.detail : "Não foi possível zerar os atrasos.");
      }
      await atualizar();
    } catch (erro) {
      $("avisoSecretaria").textContent = erro.message;
      $("avisoSecretaria").hidden = false;
    }
  }

  async function atualizar() {
    try {
      const resposta = await fetch("/api/secretaria/problema");
      if (!resposta.ok) throw new Error("Não foi possível carregar a lista.");
      const dados = await resposta.json();
      desenhar(dados.alunos);
      $("avisoSecretaria").hidden = true;
    } catch (erro) {
      $("avisoSecretaria").textContent = erro.message;
      $("avisoSecretaria").hidden = false;
    }
  }

  $("senhaSecretaria").addEventListener("input", () => {
    document.querySelectorAll("#listaProblema button").forEach((botao) => {
      botao.disabled = !$("senhaSecretaria").value.trim();
    });
  });

  atualizar();
  window.setInterval(atualizar, 2000);
})();
