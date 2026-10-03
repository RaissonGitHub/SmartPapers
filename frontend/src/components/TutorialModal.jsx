import { useState } from "react";
import Modal from "@mui/material/Modal";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CloseIcon from "@mui/icons-material/Close";
import CheckIcon from "@mui/icons-material/Check";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SearchIcon from "@mui/icons-material/Search";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import EditIcon from "@mui/icons-material/Edit";
import HistoryIcon from "@mui/icons-material/History";
import TuneIcon from "@mui/icons-material/Tune";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import ArticleIcon from "@mui/icons-material/Article";
import KeyIcon from "@mui/icons-material/Key";
import LanguageIcon from "@mui/icons-material/Language";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import BadgeIcon from "@mui/icons-material/Badge";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import ListAltIcon from "@mui/icons-material/ListAlt";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import imgSessoes from "../assets/sessoes.png";
import imgFiltros from "../assets/filtros.png";
import imgAnexar from "../assets/anexe_seu_documento.png";
import imgModo from "../assets/escolha_busca_ou_pergunta.png";
import imgModelo from "../assets/escolha_do_modelo.png";
import imgArtigos from "../assets/artigos_da_sessao.png";
import imgCancelar from "../assets/input_chat.png";
import imgEditando from "../assets/editando.png";
import imgAistudio from "../assets/tela_google_aistudio.png";
import imgBotaoCriarChave from "../assets/botao_criar_chave.png";
import imgModalCriarChave from "../assets/modal_criar_nova_chave.png";
import imgCriarProjeto from "../assets/criar_projeto_modal.png";
import imgSelecionarProjeto from "../assets/selecione_um_projeto.png";
import imgCopiarChave from "../assets/copie_sua_chave.png";

const LINK_AI_STUDIO = "https://aistudio.google.com/api-keys";

const TOUR = [
  {
icone: MenuBookIcon,
    titulo: "Bem-vindo ao SmartPapers",
    texto:
      "O SmartPapers é um assistente de pesquisa que conecta o seu texto a artigos científicos. Anexe um PDF ou descreva seu tema e receba recomendações baseadas em publicações reais.",
    destaque:
      "Primeira vez aqui? Estas duas abas mostram o básico da plataforma e como criar sua chave de API do Gemini. Dá para rever quando quiser pelo botão de ajuda no topo.",
  },
  {
    icone: HistoryIcon,
    titulo: "Organize em sessões",
    texto:
      "Cada conversa é salva como uma sessão no menu SESSÕES. Use o botão + para iniciar uma nova conversa, clique em uma sessão para retomá-la e no ícone de lixeira para excluí-la permanentemente.",
    imagens: [{ src: imgSessoes }],
  },
  {
    icone: TuneIcon,
    titulo: "Refine com filtros",
    texto:
      "Antes de buscar, defina o período de publicação (De / Até) e a Área de conhecimento. Os filtros valem para todas as requisições da sessão e ajudam a trazer artigos mais relevantes.",
    imagens: [{ src: imgFiltros }],
  },
  {
    icone: AttachFileIcon,
    titulo: "Anexe um PDF",
    texto:
      "Arraste o documento para a área central ou clique no clipe para selecioná-lo. O arquivo é analisado para que a busca seja feita a partir do conteúdo real do seu material.",
    imagens: [{ src: imgAnexar }],
  },
  {
    icone: AutoAwesomeIcon,
    titulo: "Escolha o modo de resposta",
    texto:
      "No botão de modo, ao lado do campo de texto, você define como o modelo deve agir. A seleção é aplicada imediatamente à próxima mensagem.",
    modos: [
      {
        icone: AutoAwesomeIcon,
        rotulo: "Auto",
        descricao: "O modelo decide entre buscar artigos ou responder.",
      },
      {
        icone: SearchIcon,
        rotulo: "Buscar artigos",
        descricao: "Force uma busca de artigos recomendados (FI).",
      },
      {
        icone: QuestionAnswerIcon,
        rotulo: "Pergunta direta",
        descricao: "Responda a sua pergunta sem nova busca.",
      },
    ],
    imagens: [{ src: imgModo }],
  },
  {
    icone: ModelTrainingIcon,
    titulo: "Selecione o modelo",
    texto:
      "No seletor de modelo você alterna entre Google (Gemini). Com o Gemini, informe sua chave de API, clique em Listar modelos e escolha o modelo desejado. As preferências ficam salvas na sua conta.",
    variantes: [
      {
        icone: ModelTrainingIcon,
        rotulo: "Google (Gemini)",
        descricao: "Requer chave de API e um modelo selecionado.",
      },
    ],
    imagens: [{ src: imgModelo }],
  },
  {
    icone: ArticleIcon,
    titulo: "Explore os artigos",
    texto:
      "Os artigos encontrados aparecem no painel ARTIGOS DESTA SESSÃO e nas respostas. Clique em um cartão para ler o resumo completo e acessar o artigo original em uma nova aba.",
    imagens: [{ src: imgArtigos }],
  },
  {
    icone: EditIcon,
    titulo: "Corrija e interrompa quando quiser",
    texto:
      "Você pode editar qualquer mensagem já enviada para reformular a pergunta ou cancelar a geração em andamento com o botão vermelho. Use Esc para sair de uma edição.",
    imagens: [
      { src: imgCancelar, legenda: "Cancelar a geração" },
      { src: imgEditando, legenda: "Editar a mensagem enviada" },
    ],
  },
];

const CHAVE_API = [
  {
    icone: LanguageIcon,
    titulo: "Abra o Google AI Studio",
    texto:
      "Acesse a página de chaves de API do Google AI Studio. Para entrar, basta selecionar uma conta do Google. Nesta tela você vê todas as chaves já criadas.",
    link: LINK_AI_STUDIO,
    imagens: [{ src: imgAistudio }],
  },
  {
    icone: AddCircleOutlineIcon,
    titulo: 'Clique em "Create API key"',
    texto:
      "No canto superior direito da listagem de chaves, clique no botão Create API key para iniciar a criação de uma nova chave.",
    link: LINK_AI_STUDIO,
    imagens: [{ src: imgBotaoCriarChave }],
  },
  {
    icone: BadgeIcon,
    titulo: "Nomeie a chave e escolha o projeto",
    texto:
      "O modal Create new API key abre com dois campos: o nome da chave e a seleção do projeto do Google Cloud que será usado. Dê um nome que identifique o uso, por exemplo smartpapers.",
    imagens: [{ src: imgModalCriarChave }],
  },
  {
    icone: CreateNewFolderIcon,
    titulo: "Crie um projeto, se necessário",
    texto:
      "Se você ainda não tem um projeto, use a opção de criar um novo projeto a partir do próprio modal e informe um nome para ele. Depois, o projeto passa a aparecer na lista para seleção.",
    imagens: [{ src: imgCriarProjeto }],
  },
  {
    icone: ListAltIcon,
    titulo: "Selecione o projeto",
    texto:
      "Volte ao campo de seleção do modal e escolha o projeto que acabou de ser criado (ou um projeto existente) para vincular a chave a ele.",
    imagens: [{ src: imgSelecionarProjeto }],
  },
  {
    icone: ContentCopyIcon,
    titulo: "Copie sua chave",
    texto:
      "A chave é gerada e exibida uma única vez, junto com o nome e o projeto associado. Clique em Copiar para guardá-la com segurança e cole-a no campo de chave de API do SmartPapers.",
    imagens: [{ src: imgCopiarChave }],
  },
];

const GUIAS = [
  { rotulo: "Tour da plataforma", icone: MenuBookIcon, passos: TOUR },
  { rotulo: "Gerar chave de API", icone: KeyIcon, passos: CHAVE_API },
];

export default function TutorialModal({
  className = "",
  open,
  onClose,
  aoConcluir,
}) {
  const [aba, setAba] = useState(0);
  const [passo, setPasso] = useState(0);

  const guia = GUIAS[aba];
  const passos = guia.passos;
  const total = passos.length;
  const atual = passos[passo];
  const Icone = atual.icone;
  const ultimoPasso = passo === total - 1;
  const multiplasImagens = (atual.imagens?.length ?? 0) > 1;

  const fechar = () => {
    aoConcluir?.();
    setPasso(0);
    onClose?.();
  };

  const trocarAba = (indice) => {
    setAba(indice);
    setPasso(0);
  };

  const passar = () => setPasso((p) => Math.min(p + 1, total - 1));
  const voltar = () => setPasso((p) => Math.max(p - 1, 0));

  return (
    <Modal
      open={Boolean(open)}
      onClose={fechar}
      aria-labelledby="tutorial-titulo"
      aria-describedby="tutorial-texto"
    >
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        onClick={fechar}
      >
        <div
          key={`${aba}-${passo}`}
          role="dialog"
          aria-modal="true"
          className={`flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-borda bg-fundo text-gray-100 shadow-2xl ${className}`}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            role="tablist"
            aria-label="Guias da plataforma"
            className="flex shrink-0 border-b border-borda"
          >
            {GUIAS.map((g, indice) => {
              const GuiaIcone = g.icone;
              const ativa = indice === aba;
              return (
                <button
                  key={g.rotulo}
                  type="button"
                  role="tab"
                  aria-selected={ativa}
                  onClick={() => trocarAba(indice)}
                  className={`flex flex-1 cursor-pointer items-center justify-center gap-2 border-b-2 px-4 py-3 text-sm transition-colors ${
                    ativa
                      ? "border-[#4f9cf9] text-white"
                      : "border-transparent text-gray-400 hover:text-gray-200"
                  }`}
                >
                  <GuiaIcone sx={{ fontSize: 18 }} />
                  <span className="">{g.rotulo}</span>
                </button>
              );
            })}
          </div>

          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-borda px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#1e3a5f] text-[#4f9cf9]">
                <Icone fontSize="small" />
              </span>
              <h2 id="tutorial-titulo" className="text-base font-semibold">
                {atual.titulo}
              </h2>
            </div>
            <button
              type="button"
              onClick={fechar}
              aria-label="Fechar tutorial"
              className="cursor-pointer text-gray-400 transition-colors hover:text-white"
            >
              <CloseIcon fontSize="small" />
            </button>
          </div>

          <div className="overflow-y-auto px-5 py-4">
            <p id="tutorial-texto" className="text-sm leading-6 text-gray-300">
              {atual.texto}
            </p>

            {atual.destaque && (
              <p className="mt-3 rounded-lg border border-[#1e3a5f] bg-[#1e3a5f]/40 px-3 py-2.5 text-xs leading-5 text-[#c9defb]">
                {atual.destaque}
              </p>
            )}

            {atual.link && (
              <a
                href={atual.link}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-[#4f9cf9] hover:underline"
              >
                {atual.link.replace(/^https?:\/\//, "")}
                <OpenInNewIcon sx={{ fontSize: 16 }} />
              </a>
            )}

            {atual.modos && (
              <ul className="mt-4 flex flex-col gap-2">
                {atual.modos.map((modo) => {
                  const ModoIcone = modo.icone;
                  return (
                    <li
                      key={modo.rotulo}
                      className="flex items-start gap-2.5 rounded-lg border border-borda bg-[#2e2e2e] px-3 py-2"
                    >
                      <ModoIcone sx={{ fontSize: 18, color: "#4f9cf9" }} />
                      <div className="flex min-w-0 flex-col">
                        <span className="text-sm text-gray-100">
                          {modo.rotulo}
                        </span>
                        <span className="text-xs text-gray-400">
                          {modo.descricao}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {atual.variantes && (
              <ul className="mt-4 flex flex-col gap-2">
                {atual.variantes.map((variante) => {
                  const VarianteIcone = variante.icone;
                  return (
                    <li
                      key={variante.rotulo}
                      className="flex items-start gap-2.5 rounded-lg border border-borda bg-[#2e2e2e] px-3 py-2"
                    >
                      <VarianteIcone sx={{ fontSize: 18, color: "#4f9cf9" }} />
                      <div className="flex min-w-0 flex-col">
                        <span className="text-sm text-gray-100">
                          {variante.rotulo}
                        </span>
                        <span className="text-xs text-gray-400">
                          {variante.descricao}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {atual.imagens && (
              <div className="mt-4 flex flex-wrap items-start justify-center gap-4">
                {atual.imagens.map((imagem) => (
                  <figure
                    key={imagem.src}
                    className={`flex min-w-0 flex-col items-center gap-1.5 ${
                      multiplasImagens ? "flex-1 basis-40" : "w-full"
                    }`}
                  >
                    <div
                      className={`flex w-full items-center justify-center rounded-lg border border-borda bg-[#1a1a1a] px-3 ${
                        multiplasImagens ? "min-h-20 py-4" : "py-2"
                      }`}
                    >
                      <img
                        src={imagem.src}
                        alt={imagem.legenda ?? atual.titulo}
                        loading="lazy"
                        className={`w-full object-contain ${
                          multiplasImagens ? "max-h-24" : "max-h-56"
                        }`}
                      />
                    </div>
                    {imagem.legenda && (
                      <figcaption className="text-center text-[11px] text-gray-500">
                        {imagem.legenda}
                      </figcaption>
                    )}
                  </figure>
                ))}
              </div>
            )}
          </div>

          <div className="shrink-0 border-t border-borda px-5 py-3">
            <div
              className="mb-3 flex items-center justify-center gap-1.5"
              role="tablist"
              aria-label="Progresso do tutorial"
            >
              {passos.map((p, indice) => (
                <button
                  key={p.titulo}
                  type="button"
                  role="tab"
                  aria-label={`Ir para o passo ${indice + 1}: ${p.titulo}`}
                  aria-selected={indice === passo}
                  onClick={() => setPasso(indice)}
                  className={`h-1.5 cursor-pointer rounded-full transition-all ${
                    indice === passo
                      ? "w-6 bg-[#4f9cf9]"
                      : "w-1.5 bg-[#555] hover:bg-[#888]"
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-gray-500">
                Passo {passo + 1} de {total}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={voltar}
                  disabled={passo === 0}
                  className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-borda text-gray-300 transition-colors hover:bg-[#2e2e2e] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Passo anterior"
                >
                  <ChevronLeftIcon fontSize="small" />
                </button>
                {ultimoPasso ? (
                  <button
                    type="button"
                    onClick={fechar}
                    className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-[#1d60a3] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#12477c]"
                  >
                    <CheckIcon fontSize="small" />
                    Concluir
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={passar}
                    className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-[#1d60a3] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#12477c]"
                  >
                    Avançar
                    <ChevronRightIcon fontSize="small" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}