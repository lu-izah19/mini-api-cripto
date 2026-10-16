async function buscarDados() {
  try {
    const resposta = await fetch("/monitoramento");
    const dados = await resposta.json();
    console.log(dados);
    document.getElementById("chave").textContent = dados.chave.total;
    document.getElementById("disco").textContent = dados.disco.legivel;
    document.getElementById("operacoes").textContent = dados.operacoes.total;
    document.getElementById("tempoNoAr").textContent = dados.tempo.legivel;
    document.getElementById("status").textContent = "conectado";
    document.getElementById("ultimaAtualizacao").textContent =
      new Date().toLocaleTimeString("pt-BR");
  } catch (erro) {
    document.getElementById("status").textContent = "sem conexão";
    document.getElementById("chave").textContent = "--";
    document.getElementById("disco").textContent = "--";
    document.getElementById("operacoes").textContent = "--";
    document.getElementById("tempoNoAr").textContent = "--";
  }
}

buscarDados();
setInterval(buscarDados, 10000);
