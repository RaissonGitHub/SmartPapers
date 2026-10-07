import { useCallback, useEffect, useRef, useState } from "react";
import {
  entrar,
  me,
  obterTutorial,
  registrar,
  sair,
  salvarTutorial,
} from "../services/authService";

export default function useAuth() {
  const [usuario, setUsuario] = useState(null);
  const [checando, setChecando] = useState(true);
  const [tutorialVisto, setTutorialVisto] = useState(null);
  const ativoRef = useRef(true);
  const marcadoRef = useRef(false);

  useEffect(() => {
    ativoRef.current = true;
    return () => {
      ativoRef.current = false;
    };
  }, []);

  const carregarTutorial = useCallback(async () => {
    try {
      const dados = await obterTutorial();
      if (!ativoRef.current) return;
      if (marcadoRef.current) return;
      setTutorialVisto(Boolean(dados?.visto));
    } catch {
      if (ativoRef.current && !marcadoRef.current) setTutorialVisto(null);
    }
  }, []);

  useEffect(() => {
    me()
      .then(async (dados) => {
        if (!ativoRef.current) return;
        setUsuario(dados.username);
        await carregarTutorial();
      })
      .catch(() => {
        if (ativoRef.current) setUsuario(null);
      })
      .finally(() => {
        if (ativoRef.current) setChecando(false);
      });
  }, [carregarTutorial]);

  const login = useCallback(
    async (username, password) => {
      const dados = await entrar(username, password);
      setUsuario(dados.username);
      await carregarTutorial();
    },
    [carregarTutorial],
  );

  const registrarUsuario = useCallback(
    async (username, password) => {
      const dados = await registrar(username, password);
      setUsuario(dados.username);
      await carregarTutorial();
    },
    [carregarTutorial],
  );

  const logout = useCallback(async () => {
    try {
      await sair();
    } finally {
      setUsuario(null);
      setTutorialVisto(null);
      marcadoRef.current = false;
    }
  }, []);

  const marcarTutorialVisto = useCallback(async (visto = true) => {
    marcadoRef.current = true;
    setTutorialVisto(visto);
    try {
      await salvarTutorial(visto);
    } catch {
      return;
    }
  }, []);

  return {
    usuario,
    checando,
    tutorialVisto,
    login,
    registrarUsuario,
    logout,
    marcarTutorialVisto,
  };
}
