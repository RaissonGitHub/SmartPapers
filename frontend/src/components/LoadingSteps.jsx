export default function LoadingSteps({ progresso = "" }) {
  return (
    <div className="flex max-w-160 flex-col gap-1 self-start rounded-[14px] rounded-bl-sm border border-borda bg-[#2e2e2e] px-4 py-3.5 text-[13px] text-[#555]">
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-borda border-t-[#4f9cf9]" />
        <span>{progresso || "Gerando resposta…"}</span>
      </div>
      {progresso && (
        <span className="ms-5 text-xs text-[#555]">
          A busca pode levar alguns instantes. Não feche esta página.
        </span>
      )}
    </div>
  );
}
