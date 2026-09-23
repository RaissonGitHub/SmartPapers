import { useState } from "react";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import KeyIcon from "@mui/icons-material/Key";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import { listarModelos } from "../services/chatService";

export default function SeletorModelo({
  className = "",
  provedor = "gemini",
  onProvedorChange,
  apiKey = "",
  onApiKeyChange,
  modelo = "",
  onModeloChange,
  ollamaHabilitado = null,
  apiKeyDefinida = false,
  chaveEditada = false,
}) {
  const [modelos, setModelos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [mostrarChave, setMostrarChave] = useState(false);
  const provedorAtivo = ollamaHabilitado === true ? provedor : "gemini";

  const carregarModelos = async () => {
    const chave = (chaveEditada ? apiKey : "").trim();
    if (!chave) {
      setErro("Informe sua chave de API do Google antes de listar os modelos.");
      return;
    }
    setErro("");
    setCarregando(true);
    try {
      const lista = await listarModelos(chave);
      setModelos(lista);
      if (!lista?.length) {
        setErro("Nenhum modelo com geração de conteúdo encontrado para esta chave.");
      }
    } catch (e) {
      setErro(e?.message ?? "Não foi possível listar os modelos.");
    } finally {
      setCarregando(false);
    }
  };

  const aoMudarChave = (valor) => {
    onApiKeyChange?.(valor);
    if (!valor.trim()) {
      setModelos([]);
      setErro("");
      onModeloChange?.("");
    }
  };

  const aoMudarProvedor = (valor) => {
    onProvedorChange?.(valor);
    setErro("");
  };

  const toggleSx = {
    flex: "1 1 auto",
    border: "1px solid var(--border, #3a3a3a)",
    color: "var(--text, #e8e8e8)",
    fontSize: "12px",
    fontFamily: "var(--font)",
    textTransform: "none",
    "&.Mui-selected": {
      backgroundColor: "#1d60a3",
      color: "#fff",
      "&:hover": { backgroundColor: "#12477c" },
    },
    "&:hover": { backgroundColor: "#2e2e2e" },
  };

  return (
    <div className={`${className} flex w-full flex-wrap items-center gap-2`}>
      <ToggleButtonGroup
        exclusive
        size="small"
        fullWidth
        value={provedorAtivo}
        onChange={(_, valor) => valor && aoMudarProvedor(valor)}
        sx={{
          flex: "1 1 100%",
          "& .MuiToggleButtonGroup-grouped:not(:first-of-type)": {
            borderLeft: "1px solid var(--border, #3a3a3a)",
          },
        }}
      >
        <ToggleButton value="gemini" sx={toggleSx}>
          Google (Gemini)
        </ToggleButton>
        {ollamaHabilitado === true && (
        <ToggleButton value="ollama" sx={toggleSx}>
          Ollama (local)
        </ToggleButton>
        )}
      </ToggleButtonGroup>
      {provedorAtivo === "ollama" && (
        <span className="w-full text-[11px] leading-4 text-gray-400">
          Ollama do servidor, sem enviar chave. O modelo local usa o
          configurado pelo backend (MODELO_OLLAMA).
        </span>
      )}
      {provedorAtivo === "gemini" && (
        <>
        <TextField
        size="small"
        fullWidth
        type={mostrarChave ? "text" : "password"}
        placeholder={
          apiKeyDefinida && !chaveEditada
            ? "Chave já configurada (digite para substituir)"
            : "Sua chave de API do Google IA (Gemini)"
        }
        value={chaveEditada ? apiKey : ""}
        onChange={(e) => aoMudarChave(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") carregarModelos();
        }}
        autoComplete="off"
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <KeyIcon sx={{ color: "#9ca3af", fontSize: 18 }} />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label={mostrarChave ? "Ocultar chave" : "Mostrar chave"}
                  onClick={() => setMostrarChave((atual) => !atual)}
                  edge="end"
                  size="small"
                  sx={{ color: "#9ca3af" }}
                >
                  {mostrarChave ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          },
        }}
        sx={{
          flex: "1 1 10rem",
          minWidth: 0,
          "& .MuiOutlinedInput-root": {
            background: "var(--surface2, #2e2e2e)",
            border: "1px solid var(--border, #3a3a3a)",
            borderRadius: "6px",
            color: "var(--text, #e8e8e8)",
            fontSize: "13px",
            fontFamily: "var(--font)",
            outline: "none",
          },
          "& .MuiOutlinedInput-notchedOutline": { border: "none" },
          "& input": { color: "#e8e8e8" },
        }}
      />
      <Button
        variant="contained"
        onClick={carregarModelos}
        disabled={carregando}
        startIcon={carregando ? <AutorenewIcon className="animate-spin" /> : <SmartToyIcon />}
        sx={{
          flex: "0 0 auto",
          background: "#1d60a3",
          color: "#fff",
          textTransform: "none",
          fontFamily: "var(--font)",
          fontSize: "13px",
          "&:hover": { background: "#12477c" },
          "&:disabled": { background: "#2a2a2a", color: "#888" },
        }}
      >
        {carregando ? "Carregando..." : "Listar modelos"}
      </Button>
      <FormControl
        size="small"
        sx={{
          flex: "1 1 14rem",
          minWidth: 0,
          "& .MuiInputLabel-root": {
            color: "white",
            fontSize: "13px",
            fontFamily: "var(--font)",
          },
          "& .MuiOutlinedInput-root": {
            background: "var(--surface2, #2e2e2e)",
            border: "1px solid var(--border, #3a3a3a)",
            borderRadius: "6px",
            color: "var(--text, #e8e8e8)",
            fontSize: "13px",
            fontFamily: "var(--font)",
            outline: "none",
          },
          "& .MuiOutlinedInput-notchedOutline": { border: "none" },
          "& .MuiSvgIcon-root": { color: "white" },
        }}
      >
        <InputLabel id="seletor-modelo-label">Modelo do Gemini</InputLabel>
        <Select
          labelId="seletor-modelo-label"
          id="seletor-modelo"
          value={modelo}
          label="Modelo do Gemini"
          onChange={(e) => onModeloChange?.(e.target.value)}
          disabled={carregando || modelos.length === 0}
          MenuProps={{
            slotProps: {
              paper: {
                sx: {
                  backgroundColor: "#1a1a1a",
                  color: "#e5e7eb",
                  border: "1px solid #3a3a3a",
                },
              },
            },
            MenuListProps: {
              sx: {
                maxHeight: 320,
                "& .MuiMenuItem-root": {
                  color: "#e5e7eb",
                  fontSize: 13,
                  fontFamily: "var(--font)",
                  "&:hover": { backgroundColor: "#2e2e2e" },
                  "&.Mui-selected": {
                    backgroundColor: "#1e3a5f",
                    "&:hover": { backgroundColor: "#2e4a75" },
                  },
                },
              },
            },
          }}
        >
          <MenuItem value="">
            <em>Nenhum</em>
          </MenuItem>
          {modelos.map((m) => (
            <MenuItem key={m.name} value={m.name}>
              {m.display_name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {/* Nota de privacidade */}
        <span className="w-full text-[11px] leading-4 text-gray-500">
          A escolha fica salva na sua sessão de login e a chave é usada apenas
          para chamar o Gemini.
        </span>
        </>
      )}
      {erro && (
        <span className="w-full text-[11px] leading-4 text-red-400">{erro}</span>
      )}
    </div>
  );
}