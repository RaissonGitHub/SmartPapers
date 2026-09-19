import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";

export default function Seletor({
  valores = [],
  valor = "",
  onChange,
  label = "Área",
  carregando = false,
}) {
  const handleChange = (event) => {
    onChange?.(event.target.value);
  };

  return (
    <FormControl
      className="filter-row"
      sx={{
        m: 0,
        width: "100%",
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
        "& .MuiOutlinedInput-notchedOutline": {
          border: "none",
        },
        "& .MuiSvgIcon-root": {
          color: "white",
        },
      }}
    >
      <InputLabel id="seletor-area-label">{label}</InputLabel>
      <Select
        labelId="seletor-area-label"
        id="seletor-area"
        value={valor}
        label={label}
        onChange={handleChange}
        disabled={carregando}
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
        {valores.map((v) => (
          <MenuItem key={v} value={v}>
            {v}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}