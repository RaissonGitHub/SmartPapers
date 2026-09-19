import Modal from "@mui/material/Modal";
import { useState } from "react";
import { autoresCompletos, autoresResumidos } from "../utils/autores";

export default function ChatArtigoCard({ artigo }) {
  const [aberto, setAberto] = useState(false);

  const autoresTodos =
    autoresCompletos(artigo.autores) || "Autores não informados";
  const autoresResumo = autoresResumidos(artigo.autores) || "Autores não informados";
  const base = [artigo.ano_publicacao || "S/D", artigo.area_conhecimento || artigo.area]
    .filter(Boolean)
    .join(" · ");
  const meta = [autoresResumo, base].filter(Boolean).join(" · ");
  const metaCompleto = [autoresTodos, base].filter(Boolean).join(" · ");

  const abrir = () => setAberto(true);
  const fechar = () => setAberto(false);

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={abrir}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            abrir();
          }
        }}
        className="cursor-pointer rounded-[10px] border border-borda px-3.5 py-3 transition-[background,border-color] duration-150 hover:border-[#4f9cf9] hover:bg-[#2e2e2e]"
      >
        <div className="flex items-start justify-between gap-2.5">
          <div className="line-clamp-2 text-[13px] font-semibold leading-[1.4] text-[#4f9cf9]">
            {artigo.titulo}
          </div>
        </div>
        <div className="mt-1.5 text-[11.5px] text-[#888]">{meta}</div>
        {artigo.resumo && (
          <div className="mt-1.5 line-clamp-2 text-[12px] leading-[1.55] text-[#888]">
            {artigo.resumo}
          </div>
        )}
      </div>

      <Modal
        open={aberto}
        onClose={fechar}
        aria-labelledby="chat-artigo-titulo"
        aria-describedby="chat-artigo-descricao"
      >
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={fechar}
        >
          <div
            className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-borda bg-fundo p-6 text-gray-100 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute right-4 top-3 text-2xl leading-none text-gray-400 hover:text-white"
              aria-label="Fechar modal"
              onClick={fechar}
            >
              ×
            </button>

            <div className="pr-8 text-xl font-semibold" id="chat-artigo-titulo">
              {artigo.titulo}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-400">
              <span>{metaCompleto}</span>
            </div>

            <div
              className="mt-5 whitespace-pre-line text-sm leading-6 text-gray-300"
              id="chat-artigo-descricao"
            >
              {artigo.resumo || "Resumo não disponível."}
            </div>

            {artigo.link_original && (
              <a
                className="mt-6 inline-block text-sm font-medium text-blue-400 hover:text-blue-300 hover:underline"
                href={artigo.link_original}
                target="_blank"
                rel="noreferrer"
              >
                Acessar artigo original →
              </a>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
}