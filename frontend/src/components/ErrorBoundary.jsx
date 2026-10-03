import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { erro: null };
  }

  static getDerivedStateFromError(erro) {
    return { erro };
  }

  componentDidCatch(erro, info) {
    console.error("Erro na renderização:", erro, info);
  }

  render() {
    if (!this.state.erro) return this.props.children;

    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-3 bg-fundo p-6 text-center">
        <h1 className="text-lg font-semibold text-white">
          Algo quebrou ao carregar a plataforma
        </h1>
        <p className="max-w-md text-sm text-[#888]">
          Recarregue a página. Se o problema continuar, envie o código do erro
          abaixo.
        </p>
        <pre className="max-w-full overflow-auto rounded-lg border border-borda bg-[#1a1a1a] p-3 text-left text-xs text-[#e8e8e8]">
          {String(this.state.erro?.message || this.state.erro)}
        </pre>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="cursor-pointer rounded-full border border-borda px-4 py-2 text-sm text-[#888] transition-colors hover:border-[#888] hover:text-white"
        >
          Recarregar
        </button>
      </div>
    );
  }
}