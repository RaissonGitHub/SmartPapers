import Conversa from "./Conversa";
import Ano from "./Ano";
import dayjs from "dayjs";
import Seletor from "./Seletor";
import ArtigoCard from "./ArtigoCard";

export default function Sidebar() {
  return (
    <>
      <div className="flex-col bg-fundo h-dvh w-1/7">
        {/* Conversas */}
        <div className="h-2/5">
          <div>
            <div className="flex justify-between p-3 items-center">
              <span className="text-[#555] text-xs font-bold">SESSÕES</span>
              <button className="border w-6 rounded text-sm text-[#555] border-borda cursor-pointer hover:border-blue-50 hover:text-blue-50">
                +
              </button>
            </div>
            <div className="px-3 flex flex-col gap-5 overflow-y-auto max-h-[32vh] [&::-webkit-scrollbar]:w-1  [&::-webkit-scrollbar-thumb]:rounded  [&::-webkit-scrollbar-thumb]:bg-[#555]">
              {/* Conteúdo */}
              <Conversa
                titulo={
                  "Quais sao os efeitos da inteligencia artificial generativa na minha cama"
                }
                dia={"08/03"}
                hora={"03:92"}
              />
            </div>
          </div>
        </div>
        <div className="bg-borda h-0.5 mx-4"></div>
        {/* filtros */}
        <div className="my-5">
          <div className="flex justify-between px-3 py-1 items-center">
            <span className="text-[#555] text-xs font-bold">FILTROS</span>
          </div>
          <div className="flex justify-between px-2">
            <Ano
              label={"De"}
              minDate={dayjs("2020-01-01")}
              maxDate={dayjs("2026-12-31")}
            />
            <Ano
              label={"Até"}
              minDate={dayjs("2020-01-01")}
              maxDate={dayjs("2026-12-31")}
            />
          </div>
          <div className="flex justify-center px-2 my-2">
            <Seletor valores={["biologia"]}></Seletor>
          </div>
        </div>
        <div className="bg-borda h-0.5 mx-4"></div>
        <div className="h-2/5 my-2">
          <div className="flex justify-between px-3 py-1 items-center">
            <span className="text-[#555] text-xs font-bold my-2">
              ARTIGOS DESTA SESSÃO
            </span>
          </div>
          <div className="px-3 flex flex-col gap-5 overflow-y-auto max-h-[32vh] [&::-webkit-scrollbar]:w-1  [&::-webkit-scrollbar-thumb]:rounded  [&::-webkit-scrollbar-thumb]:bg-[#555]">
            {/* Conteúdo */}
            <ArtigoCard
              titulo={
                "1. Ideias para adiar o fim do mundo"
              }
              autores={['M Mendes']}
              ano={2021}
              sim={87}
            />
          </div>
        </div>
      </div>
    </>
  );
}
