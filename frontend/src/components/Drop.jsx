import { useState } from "react";
import { useDropzone } from "react-dropzone";

export default function Drop({ className }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const { getRootProps, getInputProps, inputRef } = useDropzone({
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
    onDrop: (files) => {
      setSelectedFile(files[0] ?? null);
    },
  });

  const removeFile = () => {
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const files = selectedFile ? (
    <li className="flex w-full items-center justify-between gap-3 rounded-lg bg-borda px-5 py-2">
      <span className="truncate">
        {selectedFile.name.length >= 50
          ? selectedFile.name.slice(0, 50) + "..."
          : selectedFile.name}
      </span>
      <button
        type="button"
        onClick={removeFile}
        aria-label={`Remover ${selectedFile.name}`}
        className="shrink-0 px-1 text-xl leading-none text-gray-300 transition-colors hover:cursor-pointer hover:text-red-400"
      >
        ⨯
      </button>
    </li>
  ) : null;

  return (
    <section
      className={`${className} flex flex-col items-center justify-center gap-3 bg-[#1a1a1a] p-5 text-white`}
    >
      <span className="rounded-lg bg-borda px-1 py-2 text-5xl">📄</span>
      <span className="font-bold">Anexe seu documento</span>
      <span className="w-1/3 text-center text-wrap text-gray-400">
        Envie um PDF — rascunho, resumo ou proposta — e o SmartPapers encontrará
        artigos relacionados ao conteúdo do documento.
      </span>

      <div className="w-full max-w-120">
        <div
          {...getRootProps({ className: "dropzone" })}
          className="w-full rounded-2xl border border-dashed border-borda px-15 py-20 transition-colors hover:cursor-pointer hover:border-blue-600 hover:bg-[#1e3a5f]"
        >
          <input {...getInputProps()} />
          <p>
            Arraste um PDF aqui ou{" "}
            <span className="text-blue-500">clique para selecionar</span>
          </p>
        </div>

        <p className="mt-3 text-center text-sm text-gray-500">
          Ou digite sua busca diretamente abaixo
        </p>

        <aside className="mt-3 w-full">
          <ul className="w-full">{files}</ul>
        </aside>
      </div>
    </section>
  );
}
