import MenuIcon from "@mui/icons-material/Menu";

export default function Nav({ className, usuario, onSair, onMenu }) {
  return (
    <nav
      className={`flex h-12 shrink-0 flex-row items-center justify-between border-b-2 border-b-borda bg-fundo ${className}`}
    >
      <div className="flex items-center">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Abrir menu"
          className="ms-3 cursor-pointer text-[#888] hover:text-white lg:hidden"
        >
          <MenuIcon />
        </button>
        <span className="ps-2 self-center whitespace-nowrap text-xl font-semibold dark:text-[#4f9cf9] md:ps-5">
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
