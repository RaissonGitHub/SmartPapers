import { useState } from "react";
import ChatArea from "../components/ChatArea";
import Drop from "../components/Drop";
import InputChat from "../components/InputChat";
import Nav from "../components/Nav";
import Sidebar from "../components/Sidebar";
import useConversa from "../hooks/useConversa";

export default function Index({ usuario, onSair }) {
  const {
    mensagens,
    carregando,
    erro,
    enviar,
    sessoes,
    carregandoSessoes,
    carregandoSessao,
    sessaoAtiva,
    artigosSessao,
    selecionarSessao,
    novaSessao,
    excluirSessao,
    areas,
    carregandoAreas,
    filtros,
    definirFiltro,
  } = useConversa();
  const [arquivo, setArquivo] = useState(null);
  const [sidebarAberta, setSidebarAberta] = useState(false);
  const [sidebarRecolhida, setSidebarRecolhida] = useState(false);
  const [provedor, setProvedor] = useState("gemini");
  const [apiKey, setApiKey] = useState("");
  const [modelo, setModelo] = useState("");
  return (
    <>
      <div className="flex h-screen flex-col overflow-hidden">
        <Nav
          className={"w-full"}
          usuario={usuario}
          onSair={onSair}
          onMenu={() => setSidebarAberta(true)}
        />
        <div
          className={`relative grid flex-1 grid-cols-1 overflow-hidden ${sidebarRecolhida ? "lg:grid-cols-[4rem_minmax(0,1fr)]" : "lg:grid-cols-[18rem_minmax(0,1fr)]"}`}
        >
          <button
            type="button"
            aria-label="Fechar menu"
            onClick={() => setSidebarAberta(false)}
            className={`fixed inset-0 z-30 cursor-default bg-black/50 transition-opacity duration-300 lg:hidden ${sidebarAberta ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"}`}
          />
          <Sidebar
            className={`fixed top-0 bottom-0 left-0 z-40 flex w-[min(85vw,20rem)] transform transition-transform duration-300 ease-in-out ${sidebarAberta ? "translate-x-0" : "-translate-x-full"} h-full lg:relative lg:inset-auto lg:z-auto lg:flex lg:w-auto lg:translate-x-0 ${sidebarRecolhida ? "lg:w-16" : ""}`}
            sessoes={sessoes}
            sessaoAtiva={sessaoAtiva}
            carregandoSessoes={carregandoSessoes}
            carregandoSessao={carregandoSessao}
            artigosSessao={artigosSessao}
            onSelecionarSessao={selecionarSessao}
            onNovaSessao={novaSessao}
            onExcluirSessao={excluirSessao}
            areas={areas}
            carregandoAreas={carregandoAreas}
            filtros={filtros}
            onDefinirFiltro={definirFiltro}
            onClose={() => setSidebarAberta(false)}
            recolhida={sidebarRecolhida}
            onAlternarRecolhida={() => setSidebarRecolhida((atual) => !atual)}
          />
          <div className="flex h-full min-h-0 flex-col overflow-hidden bg-fundo">
            {mensagens.length === 0 ? (
              <Drop className="w-full flex-1" onArquivo={setArquivo} />
            ) : (
              <ChatArea
                className="min-h-0 w-full flex-1"
                mensagens={mensagens}
                carregando={carregando}
              />
            )}
            {erro && (
              <div className="mx-6 mb-2 rounded-lg border border-[#6b2a2a] bg-[#3d1a1a] px-3.5 py-2.5 text-sm text-[#f87171]">
                {erro}
              </div>
            )}
            <InputChat
              className="w-full"
              onEnviar={enviar}
              carregando={carregando}
              arquivo={arquivo}
              onArquivoChange={setArquivo}
              provedor={provedor}
              onProvedorChange={setProvedor}
              apiKey={apiKey}
              onApiKeyChange={setApiKey}
              modelo={modelo}
              onModeloChange={setModelo}
            />
          </div>
        </div>
      </div>
    </>
  );
}
