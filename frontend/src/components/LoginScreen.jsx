import { useState } from "react";

export default function LoginScreen({ onLogin, onRegistrar }) {
  const [modo, setModo] = useState("entrar");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  function trocarModo(novoModo) {
    setModo(novoModo);
    setErro("");
    setPassword("");
    setConfirmar("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (carregando) return;
    setErro("");

    if (modo === "registrar" && password !== confirmar) {
      setErro("As senhas não coincidem.");
      return;
    }

    setCarregando(true);
    try {
      const acao = modo === "registrar" ? onRegistrar : onLogin;
      await acao(username.trim(), password);
    } catch (err) {
      setErro(err.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="flex h-screen items-center justify-center p-5 bg-black">
      <form
        className="flex w-full max-w-90 flex-col gap-3.5 rounded-[14px] border border-[#3a3a3a] bg-[#242424] p-8"
        onSubmit={handleSubmit}
      >
        <div className="text-center text-xl font-semibold tracking-[-0.3px] text-white">
          <span className="text-[#4f9cf9]">Smart</span>Papers
        </div>
        <p className="-mt-1.5 mb-1.5 text-center text-[13px] text-[#888]">
          {modo === "entrar"
            ? "Entre para acessar suas sessões."
            : "Crie sua conta para começar."}
        </p>

        <label className="flex flex-col gap-1.5 text-xs text-[#888]">
          Usuário
          <input
            className="rounded-lg border border-[#3a3a3a] bg-[#2e2e2e] px-3 py-2.25 text-sm text-[#e8e8e8] outline-none transition-colors focus:border-[#4f9cf9]"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs text-[#888]">
          Senha
          <input
            className="rounded-lg border border-[#3a3a3a] bg-[#2e2e2e] px-3 py-2.25 text-sm text-[#e8e8e8] outline-none transition-colors focus:border-[#4f9cf9]"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={
              modo === "entrar" ? "current-password" : "new-password"
            }
            required
          />
        </label>

        {modo === "registrar" && (
          <label className="flex flex-col gap-1.5 text-xs text-[#888]">
            Confirmar senha
            <input
              className="rounded-lg border border-[#3a3a3a] bg-[#2e2e2e] px-3 py-2.25 text-sm text-[#e8e8e8] outline-none transition-colors focus:border-[#4f9cf9]"
              type="password"
              value={confirmar}
              onChange={(e) => setConfirmar(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
        )}

        {erro && (
          <div className="rounded-lg border border-[#6b2a2a] bg-[#3d1a1a] px-3 py-2.25 text-[12.5px] text-[#f87171]">
            {erro}
          </div>
        )}

        <button
          className="mt-1 rounded-lg border-0 bg-[#4f9cf9] p-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-[0.85] disabled:cursor-not-allowed disabled:opacity-40"
          type="submit"
          disabled={carregando}
        >
          {carregando
            ? modo === "entrar"
              ? "Entrando..."
              : "Criando conta..."
            : modo === "entrar"
              ? "Entrar"
              : "Criar conta"}
        </button>

        <div className="text-center text-[12.5px] text-[#888]">
          {modo === "entrar" ? (
            <span>
              Não tem conta?{" "}
              <button
                className="border-0 bg-transparent p-0 text-[12.5px] text-[#4f9cf9] hover:underline"
                type="button"
                onClick={() => trocarModo("registrar")}
              >
                Criar conta
              </button>
            </span>
          ) : (
            <span>
              Já tem conta?{" "}
              <button
                className="border-0 bg-transparent p-0 text-[12.5px] text-[#4f9cf9] hover:underline"
                type="button"
                onClick={() => trocarModo("entrar")}
              >
                Entrar
              </button>
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
