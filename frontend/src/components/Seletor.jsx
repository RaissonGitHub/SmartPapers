import * as React from "react";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
export default function Seletor({ valores }) {
  const [age, setAge] = React.useState("");

  const handleChange = (event) => {
    setAge(event.target.value);
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
      <InputLabel id="demo-select-small-label">Área</InputLabel>
      <Select
        labelId="demo-select-small-label"
        id="demo-select-small"
        value={age}
        label="Área"
        onChange={handleChange}
      >
        <MenuItem value="">
          <em>Nenhum</em>
        </MenuItem>
        {valores.map((v, i) => (
          <MenuItem key={v} value={i}>
            {v}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
