import { useCallback, useEffect, useState } from "react";
import { entrar, me, registrar, sair } from "../services/authService";

export default function useAuth() {
  const [usuario, setUsuario] = useState(null);
  const [checando, setChecando] = useState(true);

  useEffect(() => {
    me()
      .then((dados) => setUsuario(dados.username))
      .catch(() => setUsuario(null))
      .finally(() => setChecando(false));
  }, []);

  const login = useCallback(async (username, password) => {
    const dados = await entrar(username, password);
    setUsuario(dados.username);
  }, []);

  const registrarUsuario = useCallback(async (username, password) => {
    const dados = await registrar(username, password);
    setUsuario(dados.username);
  }, []);

  const logout = useCallback(async () => {
    try {
      await sair();
    } finally {
      setUsuario(null);
    }
  }, []);

  return { usuario, checando, login, registrarUsuario, logout };
}