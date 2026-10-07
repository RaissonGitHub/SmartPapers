import { BrowserRouter, Routes, Route } from "react-router";
import Index from "./pages/Index";
import LoginScreen from "./components/LoginScreen";
import ErrorBoundary from "./components/ErrorBoundary";
import useAuth from "./hooks/useAuth";
import "./App.css";

function App() {
  const {
    usuario,
    checando,
    tutorialVisto,
    login,
    registrarUsuario,
    logout,
    marcarTutorialVisto,
  } = useAuth();

  if (checando) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-fundo p-5">
        <span className="text-sm text-[#888]">Carregando…</span>
      </div>
    );
  }

  return (
    <BrowserRouter>
      {usuario ? (
        <Routes>
          <Route
            path="/"
            element={
              <Index
                usuario={usuario}
                onSair={logout}
                tutorialVisto={tutorialVisto}
                onTutorialVisto={marcarTutorialVisto}
              />
            }
          />
        </Routes>
      ) : (
        <LoginScreen onLogin={login} onRegistrar={registrarUsuario} />
      )}
    </BrowserRouter>
  );
}

export default function AppRaiz() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
