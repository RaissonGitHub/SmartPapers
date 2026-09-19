import Modal from "@mui/material/Modal";
import { useState } from "react";
import { autoresCompletos, autoresResumidos } from "../utils/autores";
export default function ArtigoCard({
  titulo,
  resumo,
  autores,
  ano,
  link,
}) {
  const [open, setOpen] = useState(false);
  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);
  const autoresResumo = autoresResumidos(autores);
  const autoresTodos = autoresCompletos(autores);
  return (
    <>
      <div
        className="rounded px-3 py-2 hover:bg-[#302f2f] hover:cursor-pointer"
        onClick={() => handleOpen()}
      >
        <div className="flex items-start justify-between gap-2.5">
          <p className="line-clamp-2 text-[13px] font-semibold leading-[1.4] text-[#4f9cf9]">
            {titulo}
          </p>
        </div>
        <div className="mt-1 text-xs text-gray-600">
          {autoresResumo}
          {autoresResumo && " · "}
          {ano || "S/D"}
        </div>
        {resumo && (
          <div className="mt-1 line-clamp-2 text-xs leading-5 text-gray-500">
            {resumo}
          </div>
        )}
      </div>
      <Modal open={open} onClose={handleClose}>
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={handleClose}
        >
            <div
              className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-borda bg-fundo p-6 text-gray-100 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="absolute right-4 top-3 text-2xl leading-none text-gray-400 hover:text-white"
                aria-label="Fechar modal"
                onClick={() => handleClose()}
              >
                ×
              </button>

              <div className="pr-8 text-xl font-semibold">{titulo}</div>

              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-400">
                <span>
                  {autoresTodos}
                  {autoresTodos && " · "}
                  {ano || "S/D"} ·{" "}
                </span>
              </div>

              <div className="mt-5 whitespace-pre-line text-sm leading-6 text-gray-300">
                {resumo || "Resumo não disponível."}
              </div>

              {link && (
                <a
                  className="mt-6 inline-block text-sm font-medium text-blue-400 hover:text-blue-300 hover:underline"
                  href={link}
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