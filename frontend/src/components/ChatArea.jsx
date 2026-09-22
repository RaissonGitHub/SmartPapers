import { useEffect, useMemo, useRef } from "react";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import ReactMarkdown from "react-markdown";
import EditIcon from "@mui/icons-material/Edit";
import ChatArtigoCard from "./ChatArtigoCard";
import LoadingSteps from "./LoadingSteps";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
const estilizarElemento = (Tag, className) =>
  function Elemento(props) {
    const { node, ...rest } = props;
    void node;
    return <Tag className={className} {...rest} />;
  };

const MARKDOWN_COMPONENTS = {
  h1: estilizarElemento("h1", "mb-1.5 mt-3 text-sm font-semibold"),
  h2: estilizarElemento("h2", "mb-1.5 mt-3 text-sm font-semibold"),
  h3: estilizarElemento("h3", "mb-1.5 mt-3 text-sm font-semibold"),
  p: estilizarElemento("p", "mb-2 last:mb-0"),
  ul: estilizarElemento("ul", "mb-2 list-disc pl-5"),
  ol: estilizarElemento("ol", "mb-2 list-decimal pl-5"),
  li: estilizarElemento("li", "mb-1"),
  strong: estilizarElemento("strong", "font-semibold"),
  code: estilizarElemento(
    "code",
    "rounded bg-white/10 px-1.5 py-0.5 text-xs font-mono",
  ),
  hr: estilizarElemento("hr", "my-2.5 border-borda"),
  a: estilizarElemento("a", "text-[#4f9cf9] hover:underline"),
};

export default function ChatArea({
  className = "",
  mensagens,
  carregando,
  onEditar,
  onCancelarEdicao,
  idEmEdicao = null,
}) {
  const bottomRef = useRef(null);

  const ultimaMensagemDoUsuario = useMemo(() => {
    for (let i = mensagens.length - 1; i >= 0; i--) {
      if (mensagens[i].papel === "user") return mensagens[i];
    }
    return null;
  }, [mensagens]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando]);

  return (
    <div
      className={`${className} overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[#555]`}
    >
      <div className="flex min-h-full flex-col gap-4 p-5">
        {mensagens.map((m, i) => {
          const emEdicao =
            idEmEdicao != null && m.id !== undefined && m.id === idEmEdicao;
          return (
            <div key={m.id ?? i}>
              <div className="group relative">
                <div
                  className={
                    m.papel === "user"
                      ? "flex flex-col items-end"
                      : "flex flex-col items-start"
                  }
                >
                  <div
                    className={
                      m.papel === "user"
                        ? `max-w-[85%] rounded-[18px_4px_18px_18px] bg-[#dce9fb] px-4 py-3 text-[#1e3a5f]${emEdicao ? " ring-2 ring-[#4f9cf9]" : ""}`
                        : "max-w-[85%] rounded-[4px_18px_18px_18px] bg-[#303030] px-4 py-3 text-[#f1f1f1]"
                    }
                  >
                    <ReactMarkdown components={MARKDOWN_COMPONENTS}>
                      {m.conteudo}
                    </ReactMarkdown>
                  </div>

                  {m.papel === "user" && emEdicao && (
                    <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-[#12477c] px-2 py-0.5 text-[11px] font-medium text-white">
                      <EditIcon fontSize="small" />
                      Editando...
                    </span>
                  )}

                  {m.papel === "user" && m.pdf_nome && (
                    <div className="mt-2.5 flex max-w-[85%] items-center gap-2 rounded-lg border border-[#b6cde6] bg-white/60 px-3 py-2 text-start text-xs font-medium text-[#1e3a5f]">
                      <span className="shrink-0">
                        <PictureAsPdfIcon sx={{ fontSize: 20 }} />
                      </span>
                      <span className="truncate">{m.pdf_nome}</span>
                    </div>
                  )}

                  {m.papel === "model" && m.artigos?.length > 0 && (
                    <div className="mt-3.5 flex max-w-[55%] flex-col gap-3">
                      {m.artigos.map((a, j) => (
                        <ChatArtigoCard key={a.id ?? j} artigo={a} />
                      ))}
                    </div>
                  )}
                </div>
                {m.papel === "model" ? (
                  <IconButton
                    aria-label="Copiar mensagem"
                    className="absolute right-0 top-full opacity-100"
                    onClick={() => navigator.clipboard.writeText(m.conteudo)}
                    size="small"
                    title="Copiar mensagem"
                  >
                    <ContentCopyIcon fontSize="small" className="text-white" />
                  </IconButton>
                ) : (
                  <div
                    className={`absolute ${ultimaMensagemDoUsuario?.id === m.id ? "left-[96%]" : "left-[98%]"} top-full flex transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100`}
                  >
                    {ultimaMensagemDoUsuario?.id === m.id && !carregando && (
                      <Tooltip
                        title={emEdicao ? "Cancelar edição" : "Editar mensagem"}
                      >
                        <IconButton
                          aria-label={
                            emEdicao ? "Cancelar edição" : "Editar mensagem"
                          }
                          onClick={() =>
                            emEdicao
                              ? onCancelarEdicao?.()
                              : onEditar?.(m.conteudo, m.id)
                          }
                          size="small"
                        >
                          <EditIcon fontSize="small" className="text-white" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Copiar mensagem">
                      <IconButton
                        aria-label="Copiar mensagem"
                        onClick={() =>
                          navigator.clipboard.writeText(m.conteudo)
                        }
                        size="small"
                      >
                        <ContentCopyIcon
                          fontSize="small"
                          className="text-white"
                        />
                      </IconButton>
                    </Tooltip>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {carregando && <LoadingSteps />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
