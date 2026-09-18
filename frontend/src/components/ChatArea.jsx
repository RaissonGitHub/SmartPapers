import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import ChatArtigoCard from "./ChatArtigoCard";
import LoadingSteps from "./LoadingSteps";

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

export default function ChatArea({ className = "", mensagens, carregando }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando]);

  return (
    <div
      className={`${className} overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[#555]`}
    >
      <div className="flex min-h-full flex-col gap-4 p-5">
        {mensagens.map((m, i) => (
          <div
            key={i}
            className={
              m.papel === "user"
                ? "flex flex-col items-end"
                : "flex flex-col items-start"
            }
          >
            <div
              className={
                m.papel === "user"
                  ? "max-w-[70%] rounded-[16px_4px_16px_16px] bg-[#dce9fb] px-4 py-3 text-sm leading-relaxed text-[#1e3a5f]"
                  : "max-w-160 rounded-[14px] rounded-bl-sm border border-borda bg-[#2e2e2e] px-4 py-3 text-sm leading-relaxed text-[#e8e8e8]"
              }
            >
              {m.papel === "model" ? (
                <ReactMarkdown components={MARKDOWN_COMPONENTS}>
                  {m.conteudo}
                </ReactMarkdown>
              ) : (
                <span className="whitespace-pre-line">{m.conteudo}</span>
              )}

              {m.papel === "user" && m.pdf_nome && (
                <div className="mt-2.5 flex max-w-full items-center gap-2 rounded-lg border border-[#b6cde6] bg-white/60 px-3 py-2 text-xs font-medium text-[#1e3a5f]">
                  <span className="shrink-0">📄</span>
                  <span className="truncate">{m.pdf_nome}</span>
                </div>
              )}

              {m.papel === "model" && m.artigos?.length > 0 && (
                <div className="mt-3.5 flex max-w-full flex-col gap-3">
                  {m.artigos.map((a, j) => (
                    <ChatArtigoCard key={a.id ?? j} artigo={a} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {carregando && <LoadingSteps />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
