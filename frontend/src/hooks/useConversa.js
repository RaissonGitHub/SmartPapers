import { useCallback, useEffect, useState } from "react";
import {
  enviarMensagem,
  excluirSessao as excluirSessaoApi,
  listarAreas,
  listarSessoes,
  obterSessao,
} from "../services/chat";

const ordenarArtigos = (lista) => {
  const unicos = new Map();
  for (const artigo of lista) {
    if (artigo.id != null && !unicos.has(artigo.id)) {
      unicos.set(artigo.id, artigo);
    }
  }
  return [...unicos.values()];
};

const mapearMensagens = (mensagens) =>
  mensagens.map((m) => ({
    papel: m.papel === "MODELO" ? "model" : "user",
    conteudo: m.conteudo,
    artigos: m.artigos ?? [],
    pdf_nome: m.pdf_nome ?? "",
  }));

export default function useConversa() {
  const [mensagens, setMensagens] = useState([]);
  const [carregando, setCarregando] = useState(false);
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

  const selecionarSessao = useCallback(async (pk) => {
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
  }, []);

  const novaSessao = useCallback(() => {
    setMensagens([]);
    setArtigosSessao([]);
    setErro("");
    setSessaoId(null);
    setSessaoAtiva(null);
  }, []);

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
    async (texto, arquivo = null) => {
      const conteudo = texto.trim();
      if (!conteudo || carregando) return;
      setErro("");
      setCarregando(true);
      setMensagens((prev) => [
        ...prev,
        { papel: "user", conteudo, pdf_nome: arquivo?.name || "" },
      ]);
      try {
        const resultado = await enviarMensagem({
          mensagem: conteudo,
          sessao_id: sessaoId,
          ano_inicio: filtros.anoInicio || 0,
          ano_fim: filtros.anoFim || 0,
          area: filtros.area || "",
          pdf: arquivo || null,
        });
        setSessaoAtiva((prev) => resultado.sessao ?? prev);
        setSessaoId((prev) => resultado.sessao_id ?? prev);
        setMensagens((prev) => [
          ...prev,
          {
            papel: "model",
            conteudo: resultado.resposta ?? "",
            artigos: resultado.artigos ?? [],
          },
        ]);
        if ((resultado.artigos ?? []).length > 0) {
          setArtigosSessao((prev) =>
            ordenarArtigos([...prev, ...(resultado.artigos ?? [])]),
          );
        }
        await atualizarSessoes();
      } catch (e) {
        setErro(e?.message ?? "Erro ao processar sua mensagem.");
      } finally {
        setCarregando(false);
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