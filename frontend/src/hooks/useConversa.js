import { useCallback, useEffect, useRef, useState } from "react";
import {
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
    async (texto, arquivo = null, requisicao = undefined) => {
      const conteudo = texto.trim();
      if (!conteudo || carregando) return;
      const chaveDaSessao = chaveSessaoVisualizadaRef.current;
      setErro("");
      setCarregamento({ chave: chaveDaSessao });
      const emitidaAgora = new Date().toISOString();
      const idOtimista = `temporaria-${emitidaAgora}`;
      setMensagens((prev) => [
        ...prev,
        {
          id: idOtimista,
          papel: "user",
          conteudo,
          pdf_nome: arquivo?.name || "",
          criada_em: emitidaAgora,
        },
      ]);
      try {
        const resultado = await enviarMensagem({
          mensagem: conteudo,
          sessao_id: sessaoId,
          ano_inicio: filtros.anoInicio || 0,
          ano_fim: filtros.anoFim || 0,
          area: filtros.area || "",
          pdf: arquivo || null,
          requisicao,
        });
        if (chaveSessaoVisualizadaRef.current === chaveDaSessao) {
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
        if (chaveSessaoVisualizadaRef.current === chaveDaSessao) {
          setErro(e?.message ?? "Erro ao processar sua mensagem.");
        }
      } finally {
        setCarregamento((atual) =>
          atual?.chave === chaveDaSessao ? null : atual,
        );
      }
    },
    [carregando, sessaoId, filtros, atualizarSessoes],
  );

  return {
    mensagens,
    carregando,
    erro,
    enviar,
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
