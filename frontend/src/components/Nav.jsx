import { Link } from "react-router";

export default function Nav() {
  return (
    <nav className="bg-fundo h-12 flex fle-row border-solid border-b-2 border-b-borda justify-between">
      <div className="flex">
        <span className="ps-5 self-center whitespace-nowrap text-xl font-semibold dark:text-[#4f9cf9]">
          Smart
        </span>
        <span className="self-center whitespace-nowrap text-xl font-semibold dark:text-white">
          Papers
        </span>
      </div>
      <div className="flex pe-8">
        <span className="self-center whitespace-nowrap text-m font-semibold dark:text-white">Login</span>
      </div>
    </nav>
  );
}
