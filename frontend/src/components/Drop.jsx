import { useDropzone } from "react-dropzone";

export default function Drop({ className, onArquivo }) {
  const { getRootProps, getInputProps } = useDropzone({
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
    onDrop: (files) => {
      onArquivo?.(files[0] ?? null);
    },
  });

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
      </div>
    </section>
  );
}