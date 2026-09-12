export default function Conversa({ titulo, dia, hora }) {
  return (
    <div className="px-3 py-2 rounded hover:bg-[#302f2f] hover:cursor-pointer ">
      <p className="text-white text-xs">
        "{titulo.slice(0, 62).trimEnd()}
        {titulo.length > 62 ? "..." : null}"
      </p>
      <div className="flex text-gray-600 text-xs">
        <span>
          {dia}, {hora}
        </span>
      </div>
    </div>
  );
}
