import Modal from "@mui/material/Modal";
import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
export default function ArtigoCard({
  titulo,
  resumo,
  autores,
  ano,
  sim,
  link,
}) {
  const [open, setOpen] = useState(false);
  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);
  return (
    <>
      <div
        className="px-3 py-2 rounded hover:bg-[#302f2f] hover:cursor-pointer"
        onClick={() => handleOpen()}
      >
        <p className="text-white text-xs">
          "{titulo.slice(0, 62).trimEnd()}
          {titulo.length > 62 ? "..." : null}"
        </p>
        <div className="flex text-gray-600 text-xs gap-2">
          <span>
            {autores} · {ano}
          </span>
          <span className="rounded-full bg-blue-500/15 px-2 text-xs text-blue-400">
            {sim}% sim.
          </span>
        </div>
      </div>
      <Modal
        open={open}
        onClose={handleClose}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <Box>
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-borda bg-fundo p-6 text-gray-100 shadow-2xl">
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
                  {autores} · {ano || "S/D"} ·{" "}
                </span>

                <span className="rounded-full bg-blue-500/15 px-2 py-1 text-xs text-blue-400">
                  {sim}% similaridade
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
        </Box>
      </Modal>
    </>
  );
}
