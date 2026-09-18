import { useRef, useState } from "react";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import Tooltip from "@mui/material/Tooltip";

export default function InputChat({ className = "", onEnviar, carregando }) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [text, setText] = useState("");

  const autoResize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const temTexto = text.trim().length > 0;
  const desabilitado = !temTexto || carregando;

  const limparTexto = () => {
    setText("");
    const textarea = textareaRef.current;
    if (textarea) textarea.style.height = "auto";
  };

  const handleEnviar = () => {
    if (desabilitado) return;
    onEnviar?.(text.trim());
    limparTexto();
  };

  return (
    <div
      className={`${className} flex items-end gap-3 border-t border-borda px-5 py-3`}
    >
      <input ref={fileInputRef} type="file" className="hidden" />
      <Tooltip title="Anexar pdf">
        <button
          type="button"
          onClick={handleFileClick}
          className="h-10 w-10 shrink-0 rounded-full bg-borda text-white transition hover:cursor-pointer hover:bg-[#12477c]"
        >
          <FileUploadIcon />
        </button>
      </Tooltip>

      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          autoResize();
        }}
        onInput={autoResize}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleEnviar();
          }
        }}
        className="w-full resize-none overflow-hidden rounded-full border border-borda bg-transparent px-10 py-2 text-white outline-none transition-colors focus:border-blue-500"
      />
      <Tooltip title="Enviar">
        <button
          type="button"
          disabled={desabilitado}
          onClick={handleEnviar}
          aria-label="Enviar mensagem"
          className={`h-10 w-10 shrink-0 rounded-full text-white transition ${
            desabilitado
              ? "cursor-not-allowed bg-[#2a2a2a] opacity-50"
              : "cursor-pointer bg-[#1d60a3] hover:bg-[#12477c]"
          }`}
        >
          ➜
        </button>
      </Tooltip>
    </div>
  );
}
