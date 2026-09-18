export const LIMITE_AUTORES = 10;

export function normalizarAutores(autores) {
  if (Array.isArray(autores)) return autores.filter(Boolean);
  if (typeof autores === "string" && autores.trim()) {
    return autores
      .split(/,\s*/)
      .map((autor) => autor.trim())
      .filter(Boolean);
  }
  return [];
}

export function autoresResumidos(autores, limite = LIMITE_AUTORES) {
  const lista = normalizarAutores(autores);
  if (lista.length <= limite) return lista.join(", ");
  return `${lista.slice(0, limite).join(", ")}...`;
}

export function autoresCompletos(autores) {
  return normalizarAutores(autores).join(", ");
}
