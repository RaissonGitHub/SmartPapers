import { DatePicker } from "@mui/x-date-pickers/DatePicker";

export default function Ano({ label, minDate, maxDate }) {
  return (
    <DatePicker
      label={label}
      minDate={minDate}
      maxDate={maxDate}
      openTo="year"
      views={["year"]}
      slotProps={{
        textField: {
          className: "filter-row",
          size: "small",
          fullWidth: true,
          sx: {
            width: "45%",
            color: "white",
            // data
            "& .MuiPickersSectionList-sectionContent": {
              color: "white",
              fontSize: "12px",
            },
            "& .MuiPickersOutlinedInput-root": {
              background: "var(--surface2, #2e2e2e)",
              border: "1px solid var(--border, #3a3a3a)",
              borderRadius: "6px",
              color: "var(--text, #e8e8e8)",
              fontSize: "12px",
              fontFamily: "var(--font)",
              outline: "none",
            },
            "& .MuiPickersOutlinedInput-notchedOutline": {
              border: "none",
            },
            "& .MuiPickersOutlinedInput-root:hover": {
              borderColor: "var(--border, #3a3a3a)",
            },
            "& .MuiPickersOutlinedInput-root.Mui-focused": {
              borderColor: "var(--border, #3a3a3a)",
            },
            // texto ano
            "& .MuiInputLabel-root": {
              color: "white",
            },
            //   icone
            "& .MuiSvgIcon-root": {
              color: "white",
            },
          },
        },
      }}
    />
  );
}
