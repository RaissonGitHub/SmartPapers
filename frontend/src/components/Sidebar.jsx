import HistoricoConversa from "./HistoricoConversa";
import Ano from "./Ano";
import dayjs from "dayjs";
import Seletor from "./Seletor";
import ArtigoCard from "./ArtigoCard";
import Modal from "@mui/material/Modal";
import Tooltip from "@mui/material/Tooltip";
import CloseIcon from "@mui/icons-material/Close";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { useState } from "react";

export default function Sidebar({
  className = "",
  sessoes = [],
  sessaoAtiva = null,
  carregandoSessoes = false,
  carregandoSessao = false,
  artigosSessao = [],
  onSelecionarSessao,
  onNovaSessao,
  onExcluirSessao,
  areas = [],
  carregandoAreas = false,
  filtros = { anoInicio: null, anoFim: null, area: "" },
  onDefinirFiltro,
  onClose,
  recolhida = false,
  onAlternarRecolhida,
}) {
  const [sessaoParaExcluir, setSessaoParaExcluir] = useState(null);
  const confirmarExclusao = () => {
    if (!sessaoParaExcluir) return;
    onExcluirSessao?.(sessaoParaExcluir.id);
    setSessaoParaExcluir(null);
  };
  return (
    <>
      <div
        className={`flex h-full min-h-0 flex-col overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden bg-fundo border-e-2 border-borda ${className}`}
      >
        <div className="sticky top-0 z-10 flex justify-end bg-fundo p-2 lg:hidden">
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar menu"
            className="cursor-pointer text-[#888] hover:text-white"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="sticky top-0 z-10 hidden justify-end border-b border-borda bg-fundo p-2 lg:flex">
          <Tooltip title={recolhida ? "Expandir sidebar" : "Recolher sidebar"}>
            <button
              type="button"
              onClick={onAlternarRecolhida}
              aria-label={recolhida ? "Expandir sidebar" : "Recolher sidebar"}
              className="cursor-pointer text-[#888] hover:text-white"
            >
              {recolhida ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </button>
          </Tooltip>
        </div>
        {!recolhida && (
          <>
            {/* Conversas */}
            <div className="h-2/5">
              <div>
                <div className="flex justify-between p-3 items-center">
                  <span className="text-[#555] text-xs font-bold">SESSÕES</span>
                  <Tooltip title="Nova conversa">
                    <button
                      type="button"
                      onClick={onNovaSessao}
                      aria-label="Nova conversa"
                      className="border w-6 rounded text-sm text-[#555] border-borda cursor-pointer hover:border-blue-50 hover:text-blue-50"
                    >
                      +
                    </button>
                  </Tooltip>
                </div>
                <div className="px-3 flex flex-col gap-2 overflow-y-auto max-h-[32vh] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                  {carregandoSessoes ? (
                    <span className="px-3 text-xs text-gray-600">
                      Carregando sessões...
                    </span>
                  ) : sessoes.length === 0 ? (
                    <span className="px-3 text-xs text-gray-600">
                      Nenhuma sessão ainda.
                    </span>
                  ) : (
                    sessoes.map((sessao) => (
                      <HistoricoConversa
                        key={sessao.id}
                        titulo={sessao.titulo}
                        dia={dayjs(sessao.criada_em).format("DD/MM")}
                        hora={dayjs(sessao.criada_em).format("HH:mm")}
                        ativo={sessao.id === sessaoAtiva}
                        onClick={() => onSelecionarSessao?.(sessao.id)}
                        onExcluir={() => setSessaoParaExcluir(sessao)}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
            <div className="bg-borda h-0.5 mx-4"></div>
            {/* filtros */}
            <div className="my-5">
              <div className="flex justify-between px-3 py-1 items-center">
                <span className="text-[#555] text-xs font-bold">FILTROS</span>
              </div>
              <div className="flex justify-between px-2">
                <Ano
                  label={"De"}
                  minDate={dayjs("2020-01-01")}
                  maxDate={dayjs("2026-12-31")}
                  value={
                    filtros.anoInicio ? dayjs(String(filtros.anoInicio)) : null
                  }
                  onChange={(nova) =>
                    onDefinirFiltro?.("anoInicio", nova ? nova.year() : null)
                  }
                />
                <Ano
                  label={"Até"}
                  minDate={dayjs("2020-01-01")}
                  maxDate={dayjs("2026-12-31")}
                  value={filtros.anoFim ? dayjs(String(filtros.anoFim)) : null}
                  onChange={(nova) =>
                    onDefinirFiltro?.("anoFim", nova ? nova.year() : null)
                  }
                />
              </div>
              <div className="flex justify-center px-2 my-2">
                <Seletor
                  valores={areas}
                  valor={filtros.area}
                  onChange={(valor) => onDefinirFiltro?.("area", valor)}
                  carregando={carregandoAreas}
                />
              </div>
            </div>
            <div className="bg-borda h-0.5 mx-4"></div>
            <div className="h-2/5 my-2">
              <div className="flex justify-between px-3 py-1 items-center">
                <span className="text-[#555] text-xs font-bold my-2">
                  ARTIGOS DESTA SESSÃO
                </span>
              </div>
              <div className="px-3 flex flex-col gap-2 overflow-y-auto max-h-[32vh] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {carregandoSessao ? (
                  <span className="px-3 text-xs text-gray-600">
                    Carregando artigos...
                  </span>
                ) : artigosSessao.length === 0 ? (
                  <span className="px-3 text-xs text-gray-600">
                    Nenhum artigo ainda.
                  </span>
                ) : (
                  artigosSessao.map((artigo, indice) => (
                    <ArtigoCard
                      key={artigo.id ?? indice}
                      titulo={artigo.titulo}
                      resumo={artigo.resumo}
                      autores={artigo.autores}
                      ano={artigo.ano_publicacao}
                      link={artigo.link_original}
                    />
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <Modal
        open={Boolean(sessaoParaExcluir)}
        onClose={() => setSessaoParaExcluir(null)}
        aria-labelledby="excluir-sessao-titulo"
        aria-describedby="excluir-sessao-descricao"
      >
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSessaoParaExcluir(null)}
        >
          <div
            className="relative w-full max-w-sm rounded-lg border border-borda bg-fundo p-6 text-gray-100 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold" id="excluir-sessao-titulo">
              Excluir sessão?
            </h2>
            <p
              className="mt-2 text-sm leading-6 text-gray-400"
              id="excluir-sessao-descricao"
            >
              A conversa{" "}
              <span className="text-gray-200">
                "{sessaoParaExcluir?.titulo || "Nova conversa"}"
              </span>{" "}
              e todas as suas mensagens serão removidas permanentemente.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setSessaoParaExcluir(null)}
                className="cursor-pointer rounded-lg border border-borda px-4 py-2 text-sm text-gray-300 hover:bg-[#2e2e2e] hover:text-white"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarExclusao}
                className="cursor-pointer rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
              >
                Excluir
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
}
