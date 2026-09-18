export default function LoadingSteps() {
  return (
    <div className="max-w-160 self-start rounded-[14px] rounded-bl-sm border border-borda bg-[#2e2e2e] px-4 py-3.5 text-[13px] text-[#555]">
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-borda border-t-[#4f9cf9]" />
        <span>Gerando resposta…</span>
      </div>
    </div>
  );
}