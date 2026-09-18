import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

export default function HistoricoConversa({
  titulo,
  dia,
  hora,
  ativo = false,
  onClick,
  onExcluir,
}) {
  const textoTitulo = titulo || "Nova conversa";
  return (
    <div
      className={`group flex items-center gap-1 rounded px-3 py-2 hover:cursor-pointer hover:bg-[#302f2f] ${
        ativo ? "bg-[#302f2f]" : ""
      }`}
    >
      <div className="min-w-0 flex-1" onClick={onClick}>
        <p className="truncate text-xs text-white">"{textoTitulo}"</p>
        <div className="flex text-xs text-gray-600">
          <span>
            {dia}, {hora}
          </span>
        </div>
      </div>
      <Tooltip title="Delete">
        <IconButton
          aria-label="Excluir sessão"
          onClick={(e) => {
            e.stopPropagation();
            onExcluir?.();
          }}
          className="shrink-0 rounded p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:cursor-pointer hover:bg-borda"
          sx={{
            color: "#4b5563",
            "&:hover": {
              color: "#f87171",
            },
          }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </div>
  );
}
