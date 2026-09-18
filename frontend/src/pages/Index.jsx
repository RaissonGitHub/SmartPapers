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
  return (
    <>
      <div className="flex h-screen flex-col overflow-hidden">
        <Nav className={"w-full"} usuario={usuario} onSair={onSair} />
        <div className="grid flex-1 grid-cols-7 overflow-hidden">
          <Sidebar
            className={"col-span-1 h-full"}
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
          />
          <div className="col-span-6 flex h-full min-h-0 flex-col overflow-hidden bg-fundo ">
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
            />
          </div>
        </div>
      </div>
    </>
  );
}