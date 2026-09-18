export default function Nav({ className, usuario, onSair }) {
  return (
    <nav
      className={`flex h-12 shrink-0 flex-row items-center justify-between border-b-2 border-b-borda bg-fundo ${className}`}
    >
      <div className="flex">
        <span className="ps-5 self-center whitespace-nowrap text-xl font-semibold dark:text-[#4f9cf9]">
          Smart
        </span>
        <span className="self-center whitespace-nowrap text-xl font-semibold dark:text-white">
          Papers
        </span>
      </div>
      <div className="flex items-center gap-3 pe-8">
        <span className="whitespace-nowrap text-sm font-semibold dark:text-white">
          {usuario}
        </span>
        <button
          onClick={onSair}
          className="cursor-pointer rounded-full border border-borda px-3 py-1 text-xs text-[#888] transition-colors hover:border-[#888] hover:text-white"
        >
          Sair
        </button>
      </div>
    </nav>
  );
}