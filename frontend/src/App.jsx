import { BrowserRouter, Routes, Route } from "react-router";
import Index from "./pages/Index";
import LoginScreen from "./components/LoginScreen";
import useAuth from "./hooks/useAuth";
import "./App.css";

function App() {
  const { usuario, checando, login, registrarUsuario, logout } = useAuth();

  if (checando) {
    return <div className="flex h-screen items-center justify-center p-5" />;
  }

  return (
    <BrowserRouter>
      {usuario ? (
        <Routes>
          <Route
            path="/"
            element={<Index usuario={usuario} onSair={logout} />}
          />
        </Routes>
      ) : (
        <LoginScreen onLogin={login} onRegistrar={registrarUsuario} />
      )}
    </BrowserRouter>
  );
}

export default App;
