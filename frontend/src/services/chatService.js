import api, { mensagemDeErro } from "./authService";

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
  requisicao_id = null,
  editar = false,
  signal = null,
}) {
  const config = { timeout: 600000 };
  if (signal) config.signal = signal;
  try {
    if (pdf) {
      const form = new FormData();
      form.append("mensagem", mensagem);
      if (requisicao) form.append("requisicao", requisicao);
      if (sessao_id) form.append("sessao_id", sessao_id);
      if (requisicao_id) form.append("requisicao_id", requisicao_id);
      if (editar) form.append("editar", "true");
      if (ano_inicio) form.append("ano_inicio", String(ano_inicio));
      if (ano_fim) form.append("ano_fim", String(ano_fim));
      if (area) form.append("area", area);
      if (provider) form.append("provider", provider);
      if (modelo) form.append("modelo", modelo);
      form.append("pdf", pdf);
      const { data } = await api.post("/chat/agente/", form, config);
      return data;
    }

    const body = { mensagem };
    if (requisicao) body.requisicao = requisicao;
    if (sessao_id) body.sessao_id = sessao_id;
    if (requisicao_id) body.requisicao_id = requisicao_id;
    if (editar) body.editar = true;
    if (ano_inicio) body.ano_inicio = ano_inicio;
    if (ano_fim) body.ano_fim = ano_fim;
    if (area) body.area = area;
    if (provider) body.provider = provider;
    if (modelo) body.modelo = modelo;
    const { data } = await api.post("/chat/agente/", body, config);
    return data;
  } catch (erro) {
    if (erro?.code === "ERR_CANCELED") throw erro;
    const punicao =
      erro?.code === "ECONNABORTED"
        ? "A resposta está demorando mais que o esperado. Tente novamente."
        : erro?.code === "ERR_NETWORK" || erro?.code === "ERR_CANCELED"
          ? "Conexão com o servidor perdida. Tente novamente."
          : null;
    if (punicao) {
      throw new Error(punicao, { cause: erro });
    }
    throw new Error(mensagemDeErro(erro, "Erro ao processar sua mensagem."), {
      cause: erro,
    });
  }
}

export async function criarSessao(signal = null) {
  const config = { timeout: 15000 };
  if (signal) config.signal = signal;
  try {
    const { data } = await api.post("/chat/sessoes/", {}, config);
    return data;
  } catch (erro) {
    if (erro?.code === "ERR_CANCELED") throw erro;
    throw new Error(mensagemDeErro(erro, "Erro ao criar a sessão."), {
      cause: erro,
    });
  }
}

export async function cancelarRequisicao(requisicao_id) {
  try {
    const { data } = await api.post("/chat/cancelar/", { requisicao_id });
    return data;
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao cancelar a requisição."), {
      cause: erro,
    });
  }
}

export async function listarModelos(apiKey) {
  try {
    const { data } = await api.post("/chat/modelos/", { api_key: apiKey });
    return data?.modelos ?? [];
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao listar os modelos."), {
      cause: erro,
    });
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
    throw new Error(mensagemDeErro(erro, "Erro ao carregar áreas."), {
      cause: erro,
    });
  }
}

export async function listarSessoes() {
  try {
    const { data } = await api.get("/chat/sessoes/");
    return Array.isArray(data) ? data : (data?.results ?? []);
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao carregar sessões."), {
      cause: erro,
    });
  }
}

export async function obterSessao(id) {
  try {
    const { data } = await api.get(`/chat/sessoes/${id}/`);
    return data;
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao carregar a sessão."), {
      cause: erro,
    });
  }
}

export async function excluirSessao(id) {
  try {
    await api.delete(`/chat/sessoes/${id}/`);
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao excluir a sessão."), {
      cause: erro,
    });
  }
}