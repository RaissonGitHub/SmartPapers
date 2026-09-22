import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelarRequisicao,
  criarSessao,
  enviarMensagem,
  excluirSessao as excluirSessaoApi,
  listarAreas,
  listarSessoes,
  obterSessao,
} from "../services/chatService";

const ordenarArtigos = (lista) => {
  const unicos = new Map();
  for (const artigo of lista) {
    if (artigo.id != null && !unicos.has(artigo.id)) {
      unicos.set(artigo.id, artigo);
    }
  }
  return [...unicos.values()];
};

const compararMensagens = (a, b) => {
  const instanteA = Date.parse(a.criada_em);
  const instanteB = Date.parse(b.criada_em);
  if (!Number.isNaN(instanteA) && !Number.isNaN(instanteB)) {
    if (instanteA !== instanteB) return instanteA - instanteB;
  } else if (a.criada_em !== b.criada_em) {
    if (!a.criada_em) return 1;
    if (!b.criada_em) return -1;
    return a.criada_em < b.criada_em ? -1 : 1;
  }
  return (a.id ?? 0) - (b.id ?? 0);
};

const papelDaMensagem = (papel) => {
  const papelNormalizado = String(papel ?? "").toLowerCase();
  return papelNormalizado === "modelo" ||
    papelNormalizado === "model" ||
    papelNormalizado === "assistant"
    ? "model"
    : "user";
};

const mapearMensagens = (mensagens) =>
  mensagens
    .map((m, i) => ({
      id: m.id ?? i,
      papel: papelDaMensagem(m.papel),
      conteudo: m.conteudo,
      artigos: m.artigos ?? [],
      pdf_nome: m.pdf_nome ?? "",
      criada_em: m.criada_em ?? "",
    }))
    .sort(compararMensagens);

export default function useConversa() {
  const [mensagens, setMensagens] = useState([]);
  const [carregamento, setCarregamento] = useState(null);
  const [erro, setErro] = useState("");
  const [sessaoId, setSessaoId] = useState(null);
  const [sessaoAtiva, setSessaoAtiva] = useState(null);
  const [sessoes, setSessoes] = useState([]);
  const [artigosSessao, setArtigosSessao] = useState([]);
  const [carregandoSessoes, setCarregandoSessoes] = useState(true);
  const [carregandoSessao, setCarregandoSessao] = useState(false);
  const [areas, setAreas] = useState([]);
  const [carregandoAreas, setCarregandoAreas] = useState(true);
  const [filtros, setFiltros] = useState({
    anoInicio: null,
    anoFim: null,
    area: "",
  });
  const [chaveSessaoVisualizada, setChaveSessaoVisualizada] =
    useState("nova-inicial");
  const chaveSessaoVisualizadaRef = useRef("nova-inicial");
  const abortControllerRef = useRef(null);
  const requisicaoIdRef = useRef(null);
  const editandoRef = useRef(false);
  const [pedidoEdicao, setPedidoEdicao] = useState({ texto: "", seq: 0 });
  const [pedidoCancelamento, setPedidoCancelamento] = useState(0);
  const [idEmEdicao, setIdEmEdicao] = useState(null);

  const definirSessaoVisualizada = useCallback((chave) => {
    chaveSessaoVisualizadaRef.current = chave;
    setChaveSessaoVisualizada(chave);
  }, []);

  const carregando = carregamento?.chave === chaveSessaoVisualizada;

  useEffect(() => {
    let cancelado = false;
    (async () => {
      try {
        const lista = await listarAreas();
        if (!cancelado) setAreas(lista);
      } catch {
        // áreas indisponíveis não impedem o chat
      } finally {
        if (!cancelado) setCarregandoAreas(false);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, []);

  const definirFiltro = useCallback((chave, valor) => {
    setFiltros((prev) => ({ ...prev, [chave]: valor }));
  }, []);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      try {
        const lista = await listarSessoes();
        if (!cancelado) setSessoes(lista);
      } catch (e) {
        if (!cancelado) setErro(e?.message ?? "Erro ao carregar sessões.");
      } finally {
        if (!cancelado) setCarregandoSessoes(false);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, []);

  const atualizarSessoes = useCallback(async () => {
    try {
      const lista = await listarSessoes();
      setSessoes(lista);
    } catch {
      // ignora falha ao atualizar a lista
    }
  }, []);

  const selecionarSessao = useCallback(
    async (pk) => {
      editandoRef.current = false;
      setIdEmEdicao(null);
      definirSessaoVisualizada(`sessao-${pk}`);
      setCarregandoSessao(true);
      setErro("");
      try {
        const detalhe = await obterSessao(pk);
        setSessaoAtiva(detalhe.id);
        setSessaoId(detalhe.sessao_id);
        setMensagens(mapearMensagens(detalhe.mensagens ?? []));
        setArtigosSessao(ordenarArtigos(detalhe.artigos_contexto ?? []));
      } catch (e) {
        setErro(e?.message ?? "Erro ao carregar a sessão.");
      } finally {
        setCarregandoSessao(false);
      }
    },
    [definirSessaoVisualizada],
  );

  const novaSessao = useCallback(() => {
    editandoRef.current = false;
    setIdEmEdicao(null);
    definirSessaoVisualizada(`nova-${Date.now()}`);
    setMensagens([]);
    setArtigosSessao([]);
    setErro("");
    setSessaoId(null);
    setSessaoAtiva(null);
  }, [definirSessaoVisualizada]);

  const excluirSessao = useCallback(
    async (pk) => {
      try {
        await excluirSessaoApi(pk);
        setSessoes((prev) => prev.filter((s) => s.id !== pk));
        if (sessaoAtiva !== pk) return;
        setMensagens([]);
        setArtigosSessao([]);
        setSessaoId(null);
        setSessaoAtiva(null);
      } catch (e) {
        setErro(e?.message ?? "Erro ao excluir a sessão.");
      }
    },
    [sessaoAtiva],
  );

  const enviar = useCallback(
    async (texto, arquivo = null, requisicao = undefined, opcoes = {}) => {
      const conteudo = texto.trim();
      if (!conteudo || carregando) return;
      const ehEdicao = editandoRef.current;
      editandoRef.current = false;
      if (ehEdicao) setIdEmEdicao(null);
      const chaveDaSessao = chaveSessaoVisualizadaRef.current;
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const requisicaoId =
        typeof crypto?.randomUUID === "function"
          ? crypto.randomUUID()
          : `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      requisicaoIdRef.current = requisicaoId;
      setErro("");
      setCarregamento({ chave: chaveDaSessao });
      const emitidaAgora = new Date().toISOString();
      const idOtimista = `temporaria-${emitidaAgora}`;
      setMensagens((prev) => {
        let base = prev;
        if (ehEdicao) {
          const ultimaUsuario = [...prev]
            .reverse()
            .find((m) => m.papel === "user");
          const ultimaModelo = [...prev]
            .reverse()
            .find((m) => m.papel === "model");
          const idsRemovidos = new Set(
            [ultimaUsuario, ultimaModelo]
              .map((m) => m?.id)
              .filter((id) => id != null),
          );
          base = base.filter((m) => !idsRemovidos.has(m.id));
        }
        return [
          ...base,
          {
            id: idOtimista,
            papel: "user",
            conteudo,
            pdf_nome: arquivo?.name || "",
            criada_em: emitidaAgora,
          },
        ];
      });
      let idDaSessao = sessaoId;
      if (!idDaSessao) {
        try {
          const nova = await criarSessao(controller.signal);
          idDaSessao = nova.sessao_id;
          if (chaveSessaoVisualizadaRef.current === chaveDaSessao) {
            setSessaoAtiva(nova.id);
            setSessaoId(nova.sessao_id);
            setSessoes((prev) => {
              if (prev.some((s) => s.id === nova.id)) return prev;
              return [
                {
                  id: nova.id,
                  sessao_id: nova.sessao_id,
                  titulo: nova.titulo ?? "",
                  criada_em: nova.criada_em ?? new Date().toISOString(),
                  total_mensagens: nova.total_mensagens ?? 0,
                  ultima_mensagem: nova.ultima_mensagem ?? "",
                },
                ...prev,
              ];
            });
          }
        } catch {
          if (controller.signal.aborted) return;
          idDaSessao = null;
        }
      }
      try {
        const resultado = await enviarMensagem({
          mensagem: conteudo,
          sessao_id: idDaSessao,
          ano_inicio: filtros.anoInicio || 0,
          ano_fim: filtros.anoFim || 0,
          area: filtros.area || "",
          pdf: arquivo || null,
          requisicao,
          requisicao_id: requisicaoId,
          editar: ehEdicao,
          signal: controller.signal,
          ...opcoes,
        });
        if (chaveSessaoVisualizadaRef.current === chaveDaSessao) {
          if (resultado.sessao != null) {
            setSessoes((prev) => {
              if (prev.some((s) => s.id === resultado.sessao)) return prev;
              return [
                {
                  id: resultado.sessao,
                  sessao_id: resultado.sessao_id,
                  titulo: conteudo.length > 500 ? conteudo.slice(0, 500) : conteudo,
                  criada_em: emitidaAgora,
                },
                ...prev,
              ];
            });
          }
          setSessaoAtiva((prev) => resultado.sessao ?? prev);
          setSessaoId((prev) => resultado.sessao_id ?? prev);
          setMensagens((prev) => {
            const persistidas = resultado.mensagens;
            if (Array.isArray(persistidas) && persistidas.length > 0) {
              const semOtimista = prev.filter((m) => m.id !== idOtimista);
              return mapearMensagens([...semOtimista, ...persistidas]);
            }
            return [
              ...prev.filter((m) => m.id !== idOtimista),
              {
                papel: "user",
                conteudo,
                pdf_nome: arquivo?.name || "",
                criada_em: emitidaAgora,
              },
              {
                papel: "model",
                conteudo: resultado.resposta ?? "",
                artigos: resultado.artigos ?? [],
                criada_em: new Date().toISOString(),
              },
            ];
          });
          if ((resultado.artigos ?? []).length > 0) {
            setArtigosSessao((prev) =>
              ordenarArtigos([...prev, ...(resultado.artigos ?? [])]),
            );
          }
          await atualizarSessoes();
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        if (chaveSessaoVisualizadaRef.current === chaveDaSessao) {
          setErro(e?.message ?? "Erro ao processar sua mensagem.");
        }
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        if (requisicaoIdRef.current === requisicaoId) {
          requisicaoIdRef.current = null;
        }
        setCarregamento((atual) =>
          atual?.chave === chaveDaSessao ? null : atual,
        );
      }
    },
    [carregando, sessaoId, filtros, atualizarSessoes],
  );

  const cancelar = useCallback(() => {
    const id = requisicaoIdRef.current;
    if (id) {
      cancelarRequisicao(id).catch(() => {});
    }
    abortControllerRef.current?.abort();
  }, []);

  const editarMensagem = useCallback((texto, id = null) => {
    setPedidoEdicao((prev) => ({ texto, seq: prev.seq + 1 }));
    setIdEmEdicao(id ?? null);
    editandoRef.current = true;
  }, []);

  const cancelarEdicao = useCallback(() => {
    if (!editandoRef.current) return;
    editandoRef.current = false;
    setIdEmEdicao(null);
    setPedidoCancelamento((prev) => prev + 1);
  }, []);

  return {
    mensagens,
    carregando,
    erro,
    enviar,
    cancelar,
    editarMensagem,
    cancelarEdicao,
    pedidoEdicao,
    pedidoCancelamento,
    idEmEdicao,
    sessoes,
    carregandoSessoes,
    carregandoSessao,
    sessaoAtiva,
    artigosSessao,
    selecionarSessao,
    novaSessao,
    excluirSessao,
    areas,
    carregandoAreas,
    filtros,
    definirFiltro,
  };
}
