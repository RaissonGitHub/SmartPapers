import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  withCredentials: true,
});

let csrfToken = null;
const METODOS_MUTAVEIS = ["post", "put", "patch", "delete"];

async function obterCsrf() {
  const { data } = await api.get("/auth/csrf/");
  csrfToken = data.csrfToken;
  return csrfToken;
}

function invalidarCsrf() {
  csrfToken = null;
}

api.interceptors.request.use(async (config) => {
  if (METODOS_MUTAVEIS.includes((config.method ?? "get").toLowerCase())) {
    config.headers["X-CSRFToken"] = csrfToken || (await obterCsrf());
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (erro) => {
    const config = erro.config;
    const metodo = (config?.method ?? "").toLowerCase();
    if (
      config &&
      !config._csrfRetry &&
      METODOS_MUTAVEIS.includes(metodo) &&
      erro.response?.status === 403
    ) {
      config._csrfRetry = true;
      invalidarCsrf();
      config.headers["X-CSRFToken"] = await obterCsrf();
      return api(config);
    }
    return Promise.reject(erro);
  },
);

export function mensagemDeErro(erro, padrao) {
  const data = erro?.response?.data;
  if (!data) return erro?.message || padrao;
  if (typeof data.erro === "string") return data.erro;
  if (typeof data.detail === "string") return data.detail;
  const primeiro = Object.values(data).find((valor) =>
    Array.isArray(valor) ? valor.length > 0 : Boolean(valor),
  );
  if (Array.isArray(primeiro)) return String(primeiro[0]);
  if (typeof primeiro === "string") return primeiro;
  return padrao;
}

export async function me() {
  const { data } = await api.get("/auth/me/");
  return data;
}

export async function entrar(username, password) {
  try {
    const { data } = await api.post("/auth/login/", { username, password });
    invalidarCsrf();
    return data;
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao entrar."), {
      cause: erro,
    });
  }
}

export async function registrar(username, password) {
  try {
    const { data } = await api.post("/auth/registrar/", { username, password });
    invalidarCsrf();
    return data;
  } catch (erro) {
    throw new Error(mensagemDeErro(erro, "Erro ao criar conta."), {
      cause: erro,
    });
  }
}

export async function sair() {
  try {
    await api.post("/auth/logout/");
  } catch {
    // ignora falhas de rede/encerramento
  } finally {
    invalidarCsrf();
  }
}

export async function obterPreferencias() {
  const { data } = await api.get("/auth/preferencias/");
  return data;
}

export async function salvarPreferencias(preferencias) {
  const { data } = await api.put("/auth/preferencias/", preferencias);
  return data;
}

export default api;