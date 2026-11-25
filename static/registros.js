(() => {
  const $ = (id) => document.getElementById(id);
  let pin = sessionStorage.getItem("pinProfessor") || "";

  async function chamarApi(url, metodo = "GET", pinAtual = pin) {
    const resposta = await fetch(url, {
      method: metodo,
      headers: { "X-PIN": pinAtual },
    });
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      throw new Error(typeof dados.detail === "string" ? dados.detail : "Não foi possível carregar os registros.");
    }
    return dados;
  }

  function mostrarLogin(mensagem = "") {
    $("painelRegistros").hidden = true;
    $("loginRegistros").hidden = false;
    $("erroRegistros").textContent = mensagem;
    $("erroRegistros").hidden = !mensagem;
  }

  function mostrarEventos(eventos) {
    const lista = $("eventos");
    lista.replaceChildren();
    $("semEventos").hidden = eventos.length > 0;
    eventos.forEach((evento) => {
      const item = document.createElement("li");
      item.className = evento.cls || "";
      const hora = document.createElement("time");
      hora.textContent = evento.hora;
      item.append(hora, document.createTextNode(` ${evento.texto}`));
      lista.append(item);
    });
    $("painelRegistros").hidden = false;
    $("loginRegistros").hidden = true;
    $("avisoRegistros").hidden = true;
  }

  async function atualizar() {
    try {
      const dados = await chamarApi("/api/professor/eventos");
      mostrarEventos(dados.eventos);
    } catch (erro) {
      if (erro.message === "PIN do professor incorreto.") {
        pin = "";
        sessionStorage.removeItem("pinProfessor");
        mostrarLogin("PIN inválido. Digite novamente.");
      } else {
        $("avisoRegistros").textContent = erro.message;
        $("avisoRegistros").hidden = false;
      }
    }
  }

  $("formLoginRegistros").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const pinDigitado = $("pinRegistros").value;
    try {
      await chamarApi("/api/professor/validar", "POST", pinDigitado);
      pin = pinDigitado;
      sessionStorage.setItem("pinProfessor", pin);
      await atualizar();
    } catch (erro) {
      mostrarLogin(erro.message);
    }
  });

  $("sairRegistros").addEventListener("click", () => {
    pin = "";
    sessionStorage.removeItem("pinProfessor");
    window.location.href = "/";
  });

  if (pin) atualizar();
  else mostrarLogin();
  window.setInterval(() => {
    if (pin) atualizar();
  }, 2000);
})();
