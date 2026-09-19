import { useMemo, useState } from "react";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import SearchIcon from "@mui/icons-material/Search";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import MenuItem from "@mui/material/MenuItem";
import Menu from "@mui/material/Menu";
import Tooltip from "@mui/material/Tooltip";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import {
  ChatComposer,
  ChatComposerAttachButton,
  ChatComposerAttachmentList,
  ChatComposerSendButton,
  ChatComposerTextArea,
  ChatComposerToolbar,
} from "@mui/x-chat";
import { ChatProvider } from "@mui/x-chat/headless";
const MODOS_REQUISICAO = {
  auto: {
    icone: AutoAwesomeIcon,
    rotulo: "Auto",
    descricao: "O modelo decide se busca artigos ou responde",
    requisicao: undefined,
  },
  busca: {
    icone: SearchIcon,
    rotulo: "Buscar artigos",
    descricao: "FIrá buscar artigos recomendados",
    requisicao: "busca",
  },
  pergunta: {
    icone: QuestionAnswerIcon,
    rotulo: "Pergunta direta",
    descricao: "Responde a sua pergunta",
    requisicao: "resposta",
  },
};

export default function InputChat({
  className = "",
  onEnviar,
  carregando,
  arquivo = null,
  onArquivoChange,
}) {
  const [modoRequisicao, setModoRequisicao] = useState("auto");
  const [anchorElRequisicao, setAnchorElRequisicao] = useState(null);

  const modoAtivo = MODOS_REQUISICAO[modoRequisicao] ?? MODOS_REQUISICAO.auto;
  const IconeAtivo = modoAtivo.icone;

  const selecionarModo = (modo) => {
    setModoRequisicao(modo);
    setAnchorElRequisicao(null);
  };

  const adapter = useMemo(
    () => ({
      sendMessage: async ({ message, attachments }) => {
        const texto = message.parts
          .filter((part) => part.type === "text")
          .map((part) => part.text)
          .join("")
          .trim();
        const anexo = attachments?.[0]?.file ?? arquivo ?? null;

        onArquivoChange?.(null);
        await onEnviar?.(texto, anexo, modoAtivo.requisicao);

        return new ReadableStream({
          start(controller) {
            controller.close();
          },
        });
      },
    }),
    [arquivo, modoAtivo.requisicao, onArquivoChange, onEnviar],
  );

  return (
    <div
      className={`${className} flex flex-col border-t border-borda px-4 py-2.5 sm:px-5`}
    >
      {arquivo && (
        <div className="mb-2 flex w-fit max-w-full items-center gap-2 rounded-lg border border-borda bg-[#2e2e2e] px-3 py-1.5 text-xs text-gray-200">
          <span className="shrink-0">📄</span>
          <span className="truncate">{arquivo.name}</span>
          <button
            type="button"
            onClick={() => onArquivoChange?.(null)}
            aria-label={`Remover ${arquivo.name}`}
            className="shrink-0 px-1 text-base leading-none text-gray-400 transition-colors hover:cursor-pointer hover:text-red-400"
          >
            ⨯
          </button>
        </div>
      )}

      <ChatProvider
        adapter={adapter}
        initialActiveConversationId="smartpapers"
        initialConversations={[{ id: "smartpapers" }]}
      >
        <ChatComposer
          variant="compact"
          features={{
            attachments: {
              acceptedMimeTypes: ["application/pdf"],
              maxFileCount: 1,
            },
          }}
          className="flex items-end gap-2 sm:gap-3"
          sx={{
            backgroundColor: "#3a3a3a!important",
            color: "#fff",
            padding: 0,
            "& textarea": {
              color: "#fff",
              colorScheme: "dark",
            },
          }}
        >
          <Tooltip title="Anexar pdf">
            <ChatComposerAttachButton aria-label="Anexar pdf">
              <AttachFileIcon sx={{color:'white'}}/>
            </ChatComposerAttachButton>
          </Tooltip>
          <Tooltip
            title={`${modoAtivo.rotulo}: ${modoAtivo.descricao} (clique para mudar)`}
          >
            <button
              type="button"
              onClick={(e) => setAnchorElRequisicao(e.currentTarget)}
              aria-label={`Modo de requisição: ${modoAtivo.rotulo}`}
              aria-expanded={Boolean(anchorElRequisicao)}
              aria-haspopup="menu"
              className={
                modoRequisicao === "auto"
                  ? "h-10 w-10 shrink-0 rounded-full border border-borda bg-borda text-white transition hover:cursor-pointer hover:bg-[#12477c]"
                  : "h-10 w-10 shrink-0 rounded-full border border-[#4f9cf9] bg-[#12477c] text-white transition hover:cursor-pointer hover:bg-[#0e3a63]"
              }
            >
              <IconeAtivo />
            </button>
          </Tooltip>
          <Menu
            anchorEl={anchorElRequisicao}
            open={Boolean(anchorElRequisicao)}
            onClose={() => setAnchorElRequisicao(null)}
            anchorOrigin={{ vertical: "top", horizontal: "left" }}
            transformOrigin={{ vertical: "bottom", horizontal: "left" }}
            slotProps={{
              paper: {
                sx: { backgroundColor: "#1a1a1a", color: "#e5e7eb" },
              },
            }}
          >
            {Object.entries(MODOS_REQUISICAO).map(([chave, modo]) => {
              const ItemIcone = modo.icone;
              return (
                <MenuItem
                  key={chave}
                  selected={chave === modoRequisicao}
                  onClick={() => selecionarModo(chave)}
                  sx={{
                    gap: 1.5,
                    fontSize: 14,
                    color: "#e5e7eb",
                    "&:hover": { backgroundColor: "#2e2e2e" },
                  }}
                >
                  <ItemIcone sx={{ fontSize: 18, color: "#4f9cf9" }} />
                  <div className="flex flex-col">
                    <span>{modo.rotulo}</span>
                    <span className="text-xs text-gray-400">
                      {modo.descricao}
                    </span>
                  </div>
                </MenuItem>
              );
            })}
          </Menu>
          <ChatComposerTextArea
            aria-label="Mensagem"
            placeholder="Digite uma mensagem"
            minRows={1}
            maxRows={5}
            className="w-full resize-none overflow-x-hidden overflow-y-auto rounded-full border border-borda bg-transparent px-10 py-2 text-white outline-none transition-colors focus:border-blue-500"
          />
          <ChatComposerAttachmentList />
          <ChatComposerToolbar>
            <Tooltip title="Enviar">
              <ChatComposerSendButton
                aria-label="Enviar mensagem"
                disabled={carregando}
                className="h-10 w-10 shrink-0 rounded-full border-0 bg-[#1d60a3] text-white transition hover:cursor-pointer hover:bg-[#12477c] disabled:cursor-not-allowed disabled:bg-[#2a2a2a] disabled:opacity-50"
              >
                <ArrowForwardIcon />
              </ChatComposerSendButton>
            </Tooltip>
          </ChatComposerToolbar>
        </ChatComposer>
      </ChatProvider>
    </div>
  );
}
