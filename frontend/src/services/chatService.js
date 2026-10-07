import api, { mensagemDeErro } from "./authService";
import { CAMINHO_AGENTE, TIMEOUT_MS, enviarComProgresso } from "./chatStream";

const erroComum = (erro, padrao) => {
  if (erro?.name === "AbortError" || erro?.name === "TimeoutError") throw erro;
  throw new Error(mensagemDeErro(erro, padrao), { cause: erro });
};

const normalizarErro = (erro, padrao) => {
  if (erro?.name === "AbortError") throw erro;
  if (erro?.name === "TimeoutError" || erro?.code === "ECONNABORTED") {
    throw new Error(
      "A resposta está demorando mais que o esperado. Tente novamente.",
      { cause: erro },
    );
  }
  if (erro?.code === "ERR_NETWORK") {
    throw new Error("Conexão com o servidor perdida. Tente novamente.", {
      cause: erro,
    });
  }
  throw new Error(mensagemDeErro(erro, padrao), { cause: erro });
};

function montarCorpo({
  mensagem,
  sessao_id = null,
  ano_inicio = 0,
  ano_fim = 0,
  area = "",
  pdf = null,
  requisicao = null,
  provider = null,
  modelo = null,
  api_key = null,
  requisicao_id = null,
  editar = false,
  stream = false,
}) {
  const extras = [];
  const adicionar = (chave, valor) => {
    if (valor === null || valor === undefined || valor === "") return;
    extras.push([chave, valor]);
  };
  adicionar("requisicao", requisicao);
  adicionar("sessao_id", sessao_id);
  adicionar("requisicao_id", requisicao_id);
  adicionar("ano_inicio", ano_inicio);
  adicionar("ano_fim", ano_fim);
  adicionar("area", area);
  adicionar("provider", provider);
  adicionar("modelo", modelo);
  adicionar("api_key", api_key);
  if (editar) extras.push(["editar", true]);
  if (stream) extras.push(["stream", true]);

  if (pdf) {
    const form = new FormData();
    form.append("mensagem", mensagem);
    for (const [chave, valor] of extras) form.append(chave, String(valor));
    form.append("pdf", pdf);
    return form;
  }

  return { mensagem, ...Object.fromEntries(extras) };
}

export async function enviarMensagem({
  mensagem,
  sessao_id = null,
  ano_inicio = 0,
  ano_fim = 0,
  area = "",
  pdf = null,
  requisicao = null,
  provider = null,
  modelo = null,
  api_key = null,
  requisicao_id = null,
  editar = false,
  signal = null,
  aoProgresso = null,
}) {
  const config = { timeout: TIMEOUT_MS };
  if (signal) config.signal = signal;
  const parametros = {
    mensagem,
    sessao_id,
    ano_inicio,
    ano_fim,
    area,
    pdf,
    requisicao,
    provider,
    modelo,
    api_key,
    requisicao_id,
    editar,
  };
  try {
    if (aoProgresso) {
      return await enviarComProgresso({
        corpo: montarCorpo({ ...parametros, stream: true }),
        temPdf: Boolean(pdf),
        sinal: signal,
        aoProgresso,
      });
    }

    const { data } = await api.post(
      CAMINHO_AGENTE,
      montarCorpo(parametros),
      config,
    );
    return data;
  } catch (erro) {
    if (erro?.name === "AbortError") throw erro;
    normalizarErro(erro, "Erro ao processar sua mensagem.");
  }
}

export async function cancelarRequisicao(requisicao_id) {
  try {
    const { data } = await api.post("/chat/cancelar/", { requisicao_id });
    return data;
  } catch (erro) {
    erroComum(erro, "Erro ao cancelar a requisição.");
  }
}

export async function listarModelos(apiKey) {
  try {
    const { data } = await api.post("/chat/modelos/", { api_key: apiKey });
    return data?.modelos ?? [];
  } catch (erro) {
    erroComum(erro, "Erro ao listar os modelos.");
  }
}

export async function listarAreas() {
  try {
    const { data } = await api.get("/chat/areas/");
    return {
      areas: Array.isArray(data?.areas) ? data.areas : [],
      anoMinimo: data?.ano_minimo ?? 0,
      anoMaximo: data?.ano_maximo ?? 0,
    };
  } catch (erro) {
    erroComum(erro, "Erro ao carregar áreas.");
  }
}

export async function listarSessoes() {
  try {
    const { data } = await api.get("/chat/sessoes/");
    return Array.isArray(data) ? data : (data?.results ?? []);
  } catch (erro) {
    erroComum(erro, "Erro ao carregar sessões.");
  }
}

export async function obterSessao(id) {
  try {
    const { data } = await api.get(`/chat/sessoes/${id}/`);
    return data;
  } catch (erro) {
    erroComum(erro, "Erro ao carregar a sessão.");
  }
}

export async function excluirSessao(id) {
  try {
    await api.delete(`/chat/sessoes/${id}/`);
  } catch (erro) {
    erroComum(erro, "Erro ao excluir a sessão.");
  }
}
