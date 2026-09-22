import { useEffect, useMemo, useState } from "react";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckIcon from "@mui/icons-material/Check";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import SearchIcon from "@mui/icons-material/Search";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import TuneIcon from "@mui/icons-material/Tune";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import StopIcon from "@mui/icons-material/Stop";
import MenuItem from "@mui/material/MenuItem";
import Menu from "@mui/material/Menu";
import Popover from "@mui/material/Popover";
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
import { ChatProvider, useChatComposer } from "@mui/x-chat/headless";
import SeletorModelo from "./SeletorModelo";
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

function ControladorEdicao({ pedidoEdicao, pedidoCancelamento }) {
  const { setValue } = useChatComposer();
  useEffect(() => {
    if (pedidoEdicao?.seq > 0) {
      setValue(pedidoEdicao.texto ?? "");
    }
  }, [pedidoEdicao?.seq, pedidoEdicao?.texto, setValue]);
  useEffect(() => {
    if (pedidoCancelamento > 0) {
      setValue("");
    }
  }, [pedidoCancelamento, setValue]);
  return null;
}

export default function InputChat({
  className = "",
  onEnviar,
  onCancel,
  carregando,
  arquivo = null,
  onArquivoChange,
  provedor = "gemini",
  apiKey = "",
  modelo = "",
  onProvedorChange,
  onApiKeyChange,
  onModeloChange,
  pedidoEdicao = null,
  pedidoCancelamento = 0,
  onCancelarEdicao,
}) {
  const [modoRequisicao, setModoRequisicao] = useState("auto");
  const [anchorElRequisicao, setAnchorElRequisicao] = useState(null);
  const [anchorElModelo, setAnchorElModelo] = useState(null);
  const [anchorElFuncoes, setAnchorElFuncoes] = useState(null);

  const modoAtivo = MODOS_REQUISICAO[modoRequisicao] ?? MODOS_REQUISICAO.auto;
  const IconeAtivo = modoAtivo.icone;

  const ModeloIcone = provedor === "ollama" ? SmartToyIcon : ModelTrainingIcon;
  const rotuloModelo =
    provedor === "ollama"
      ? "Ollama"
      : modelo.trim()
        ? modelo.trim().replace(/^models\//, "")
        : "Gemini";

  const selecionarModo = (modo) => {
    setModoRequisicao(modo);
    setAnchorElRequisicao(null);
    setAnchorElFuncoes(null);
  };

  const opcoesModelo = useMemo(() => {
    if (provedor === "ollama") return { provider: "ollama" };
    const modeloSelecionado = modelo.trim();
    const extra = {};
    if (modeloSelecionado) extra.modelo = modeloSelecionado;
    return { provider: "gemini", ...extra };
  }, [provedor, modelo]);

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
        await onEnviar?.(texto, anexo, modoAtivo.requisicao, opcoesModelo);

        return new ReadableStream({
          start(controller) {
            controller.close();
          },
        });
      },
    }),
    [arquivo, modoAtivo.requisicao, onArquivoChange, onEnviar, opcoesModelo],
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
        <ControladorEdicao
          pedidoEdicao={pedidoEdicao}
          pedidoCancelamento={pedidoCancelamento}
        />
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
              "&::placeholder": {
                color: "#fff",
                opacity: 1,
              },
            },
          }}
        >
          <Tooltip title="Anexar pdf">
            <ChatComposerAttachButton aria-label="Anexar pdf">
              <AttachFileIcon sx={{ color: "white" }} />
            </ChatComposerAttachButton>
          </Tooltip>
          <Tooltip title="Opções (busca, resposta e modelo)">
            <button
              type="button"
              onClick={(e) => setAnchorElFuncoes(e.currentTarget)}
              aria-label="Opções de busca, resposta e modelo"
              aria-expanded={Boolean(anchorElFuncoes)}
              aria-haspopup="dialog"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-borda bg-borda text-white transition hover:cursor-pointer hover:bg-[#12477c] md:hidden"
            >
              <TuneIcon sx={{ fontSize: 20 }} />
            </button>
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
                  ? "hidden h-10 w-10 shrink-0 items-center justify-center rounded-full border border-borda bg-borda text-white transition hover:cursor-pointer hover:bg-[#12477c] md:flex"
                  : "hidden h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#4f9cf9] bg-[#12477c] text-white transition hover:cursor-pointer hover:bg-[#0e3a63] md:flex"
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
          <Tooltip title={`Modelo: ${rotuloModelo} (clique para mudar)`}>
            <button
              type="button"
              onClick={(e) => setAnchorElModelo(e.currentTarget)}
              aria-label={`Modelo selecionado: ${rotuloModelo}`}
              aria-expanded={Boolean(anchorElModelo)}
              aria-haspopup="dialog"
              className="hidden h-11 shrink-0 items-center gap-2 rounded-full border border-[#4f9cf9]/80 bg-[#12477c] px-4 text-sm text-white transition hover:cursor-pointer hover:bg-[#0e3a63] md:flex"
            >
              <ModeloIcone sx={{ fontSize: 20 }} />
              <span className="hidden max-w-[12rem] truncate md:inline">
                {rotuloModelo}
              </span>
            </button>
          </Tooltip>
          <Popover
            open={Boolean(anchorElModelo)}
            anchorEl={anchorElModelo}
            onClose={() => setAnchorElModelo(null)}
            anchorOrigin={{ vertical: "top", horizontal: "left" }}
            transformOrigin={{ vertical: "bottom", horizontal: "left" }}
            slotProps={{
              paper: {
                sx: {
                  backgroundColor: "#1f1f1f",
                  color: "#e5e7eb",
                  border: "1px solid #3a3a3a",
                  borderRadius: 2,
                },
              },
            }}
          >
            <div className="w-[min(90vw,22rem)]">
              <SeletorModelo
                provedor={provedor}
                onProvedorChange={onProvedorChange}
                apiKey={apiKey}
                onApiKeyChange={onApiKeyChange}
                modelo={modelo}
                onModeloChange={onModeloChange}
                className="gap-1.5 px-3 py-2.5"
              />
            </div>
          </Popover>
          <Popover
            open={Boolean(anchorElFuncoes)}
            anchorEl={anchorElFuncoes}
            onClose={() => setAnchorElFuncoes(null)}
            anchorOrigin={{ vertical: "top", horizontal: "right" }}
            transformOrigin={{ vertical: "bottom", horizontal: "right" }}
            slotProps={{
              paper: {
                sx: {
                  backgroundColor: "#1f1f1f",
                  color: "#e5e7eb",
                  border: "1px solid #3a3a3a",
                  borderRadius: 2,
                },
              },
            }}
          >
            <div className="w-[min(90vw,20rem)]">
              <div className="flex flex-col gap-1 px-2.5 pt-2.5">
                <span className="px-1.5 text-[11px] uppercase tracking-wide text-gray-400">
                  Tipo de resposta
                </span>
                {Object.entries(MODOS_REQUISICAO).map(([chave, modo]) => {
                  const ItemIcone = modo.icone;
                  const ativo = chave === modoRequisicao;
                  return (
                    <button
                      key={chave}
                      type="button"
                      onClick={() => selecionarModo(chave)}
                      className={`flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition hover:cursor-pointer hover:bg-[#2e2e2e] ${ativo ? "bg-[#1e3a5f]" : ""}`}
                    >
                      <ItemIcone sx={{ fontSize: 18, color: "#4f9cf9" }} />
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className="text-sm text-[#e5e7eb]">
                          {modo.rotulo}
                        </span>
                        <span className="truncate text-[11px] text-gray-400">
                          {modo.descricao}
                        </span>
                      </div>
                      {ativo && (
                        <CheckIcon sx={{ fontSize: 18, color: "#4f9cf9" }} />
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="mx-2.5 my-2 h-px bg-[#3a3a3a]" />
              <SeletorModelo
                provedor={provedor}
                onProvedorChange={onProvedorChange}
                apiKey={apiKey}
                onApiKeyChange={onApiKeyChange}
                modelo={modelo}
                onModeloChange={onModeloChange}
                className="gap-1.5 px-3 pb-3"
              />
            </div>
          </Popover>
          <ChatComposerTextArea
            aria-label="Mensagem"
            placeholder="Digite uma mensagem"
            maxRows={5}
            onKeyDown={(e) => {
              if (e.key === "Escape") onCancelarEdicao?.();
            }}
            className="w-full resize-none overflow-x-hidden overflow-y-auto rounded-full border border-borda bg-transparent px-10 py-2 text-white outline-none transition-colors focus:border-blue-500"
          />
          <ChatComposerAttachmentList />
          <ChatComposerToolbar>
            {carregando ? (
              <Tooltip title="Cancelar">
                <button
                  type="button"
                  onClick={onCancel}
                  aria-label="Cancelar geração"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-0 bg-[#b34747] text-white transition hover:cursor-pointer hover:bg-[#8f3030]"
                >
                  <StopIcon sx={{ fontSize: 20 }} />
                </button>
              </Tooltip>
            ) : (
              <Tooltip title="Enviar">
                <span>
                  <ChatComposerSendButton
                    aria-label="Enviar mensagem"
                    disabled={carregando}
                    className="h-10 w-10 shrink-0 rounded-full border-0 bg-[#1d60a3] text-white transition hover:cursor-pointer hover:bg-[#12477c] disabled:cursor-not-allowed disabled:bg-[#2a2a2a] disabled:opacity-50"
                  >
                    <ArrowForwardIcon />
                  </ChatComposerSendButton>
                </span>
              </Tooltip>
            )}
          </ChatComposerToolbar>
        </ChatComposer>
      </ChatProvider>
    </div>
  );
}
