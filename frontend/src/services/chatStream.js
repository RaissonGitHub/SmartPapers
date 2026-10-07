import { BASE_URL, mensagemDeErro, tokenCsrf } from "./authService";

export const TIMEOUT_MS = 600000;
export const CAMINHO_AGENTE = "/chat/agente/";

const API = BASE_URL.replace(/\/+$/, "");

async function erroDaResposta(resposta) {
  const padrao = `O servidor respondeu com erro ${resposta.status}. Tente novamente.`;
  const texto = await resposta.text();
  try {
    return new Error(
      mensagemDeErro({ response: { data: JSON.parse(texto) } }, padrao) ||
        padrao,
    );
  } catch {
    return new Error(padrao);
  }
}

async function lerNdjson(resposta, sinal, aoProgresso) {
  const leitor = resposta.body?.getReader();
  if (!leitor) return null;

  const decodificador = new TextDecoder();
  let buffer = "";
  let resultado = null;

  const tratar = (linha) => {
    const texto = linha.trim();
    if (!texto) return;
    let evento;
    try {
      evento = JSON.parse(texto);
    } catch {
      return;
    }
    if (evento.tipo === "etapa") aoProgresso?.(evento.texto);
    if (evento.tipo === "resultado") resultado = evento.dados;
    if (evento.tipo === "erro") throw new Error(evento.erro);
    if (evento.tipo === "cancelada") {
      throw new DOMException("Requisição cancelada.", "AbortError");
    }
  };

  try {
    for (;;) {
      const { done, value } = await leitor.read();
      if (done) break;
      buffer += decodificador.decode(value, { stream: true });
      const linhas = buffer.split("\n");
      buffer = linhas.pop() ?? "";
      for (const linha of linhas) tratar(linha);
    }
    buffer += decodificador.decode();
    tratar(buffer);
  } catch (erro) {
    if (sinal?.aborted) throw erro;
    await leitor.cancel().catch(() => {});
    throw erro;
  }

  return resultado;
}

export async function enviarComProgresso({
  corpo,
  temPdf,
  sinal,
  aoProgresso,
}) {
  const cabecalhos = {
    Accept: "application/json",
    "X-CSRFToken": await tokenCsrf(),
  };
  if (!temPdf) cabecalhos["Content-Type"] = "application/json";

  // Compõe o cancelamento do chamador com um timeout de cliente: se o
  // backend parar de responder, o fetch aborta sozinho (TimeoutError) em vez
  // de o usuário ficar pendurado até o timeout do nginx.
  const sinalTotal = sinal
    ? AbortSignal.any([sinal, AbortSignal.timeout(TIMEOUT_MS)])
    : AbortSignal.timeout(TIMEOUT_MS);

  const resposta = await fetch(`${API}${CAMINHO_AGENTE}`, {
    method: "POST",
    credentials: "include",
    headers: cabecalhos,
    body: temPdf ? corpo : JSON.stringify(corpo),
    signal: sinalTotal,
  });
  if (!resposta.ok) throw await erroDaResposta(resposta);

  const dados = await lerNdjson(resposta, sinal, aoProgresso);
  if (!dados) {
    throw new Error(
      "A resposta do servidor chegou incompleta. Tente novamente.",
    );
  }
  return dados;
}
