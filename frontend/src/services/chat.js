import api, { mensagemDeErro } from "./api";

export async function enviarMensagem({
  mensagem,
  sessao_id = null,
  ano_inicio = 0,
  ano_fim = 0,
  area = "",
  pdf = null,
}) {
  try {
    if (pdf) {
      const form = new FormData();
      form.append("mensagem", mensagem);
      if (sessao_id) form.append("sessao_id", sessao_id);
      if (ano_inicio) form.append("ano_inicio", String(ano_inicio));
      if (ano_fim) form.append("ano_fim", String(ano_fim));
      if (area) form.append("area", area);
      form.append("pdf", pdf);
      const { data } = await api.post("/chat/agente/", form, {
        timeout: 600000,
      });
      return data;
    }

    const body = { mensagem };
    if (sessao_id) body.sessao_id = sessao_id;
    if (ano_inicio) body.ano_inicio = ano_inicio;
    if (ano_fim) body.ano_fim = ano_fim;
    if (area) body.area = area;
    const { data } = await api.post("/chat/agente/", body, {
      timeout: 600000,
    });
    return data;
  } catch (erro) {
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

export async function listarAreas() {
  try {
    const { data } = await api.get("/chat/areas/");
    return data?.areas ?? [];
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