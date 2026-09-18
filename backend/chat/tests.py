from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from artigos.models.artigo import Artigo
from chat.models import Mensagem, Sessao
from chat.services.rag import _substituir_ancoras_por_titulo


class SubstituicaoAncoraLinksTestCase(TestCase):
    def test_substitui_texto_visivel_pelo_titulo(self):
        resposta = "Veja [clique aqui](https://doi.org/10.1234) e [x](https://outro.org)"
        artigos = [
            {
                "titulo": "Machine Learning Aplicado",
                "link_original": "https://doi.org/10.1234",
            }
        ]
        resultado = _substituir_ancoras_por_titulo(resposta, artigos)
        self.assertIn("[Machine Learning Aplicado](https://doi.org/10.1234)", resultado)
        self.assertIn("[x](https://outro.org)", resultado)

    def test_mantem_link_de_url_nao_mapeada(self):
        resposta = "[texto](https://forumlberto.org)"
        resultado = _substituir_ancoras_por_titulo(resposta, [])
        self.assertEqual(resultado, resposta)

    def test_remove_colchetes_do_titulo(self):
        resposta = "[palavra](https://doi.org/1)"
        artigos = [{"titulo": "IA [2024] e Web", "link_original": "https://doi.org/1"}]
        resultado = _substituir_ancoras_por_titulo(resposta, artigos)
        self.assertEqual(resultado, "[IA 2024 e Web](https://doi.org/1)")

    def test_usuario_sem_titulo_vira_artigo(self):
        resposta = "[palavra](https://doi.org/2)"
        artigos = [{"link_original": "https://doi.org/2"}]
        resultado = _substituir_ancoras_por_titulo(resposta, artigos)
        self.assertEqual(resultado, "[artigo](https://doi.org/2)")


class SessaoViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(
            username="teste", password="senha123"
        )
        self.client.force_authenticate(user=self.usuario)

    def test_sessoes_exigem_autenticacao(self):
        anonimo = APIClient()
        resposta = anonimo.get("/chat/sessoes/")
        self.assertIn(resposta.status_code, (401, 403))

    def test_criar_sessao(self):
        resposta = self.client.post(
            "/chat/sessoes/", {"titulo": "Minha conversa"}, format="json"
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(resposta.data["sessao_id"])
        self.assertEqual(resposta.data["titulo"], "Minha conversa")
        self.assertEqual(Sessao.objects.count(), 1)

    def test_criar_sessao_vincular_usuario_logado(self):
        resposta = self.client.post("/chat/sessoes/", format="json")
        self.assertEqual(resposta.status_code, 201)
        sessao = Sessao.objects.get(pk=resposta.data["id"])
        self.assertEqual(sessao.usuario, self.usuario)

    def test_listar_sessoes_retorna_apenas_do_usuario(self):
        Sessao.objects.create(sessao_id="abc-1", titulo="Minha", usuario=self.usuario)
        outro = User.objects.create_user(username="outro", password="senha123")
        Sessao.objects.create(sessao_id="abc-2", titulo="De outro", usuario=outro)

        resposta = self.client.get("/chat/sessoes/")
        self.assertEqual(resposta.status_code, 200)
        ids = [s["sessao_id"] for s in resposta.data["results"]]
        self.assertIn("abc-1", ids)
        self.assertNotIn("abc-2", ids)

    def test_detalhe_traz_mensagens_em_ordem(self):
        sessao = Sessao.objects.create(
            sessao_id="abc-3", titulo="Minha", usuario=self.usuario
        )
        Mensagem.objects.create(sessao=sessao, papel="USUARIO", conteudo="olá")
        Mensagem.objects.create(sessao=sessao, papel="MODELO", conteudo="oi!")

        resposta = self.client.get(f"/chat/sessoes/{sessao.id}/")
        self.assertEqual(resposta.status_code, 200)
        conteudos = [m["conteudo"] for m in resposta.data["mensagens"]]
        self.assertEqual(conteudos, ["olá", "oi!"])

    def test_nao_acessa_sessao_de_outro_usuario(self):
        outro = User.objects.create_user(username="outro2", password="senha123")
        sessao = Sessao.objects.create(
            sessao_id="abc-4", titulo="Privada", usuario=outro
        )
        resposta = self.client.get(f"/chat/sessoes/{sessao.id}/")
        self.assertEqual(resposta.status_code, 404)

    def test_excluir_sessao_remove_mensagens(self):
        sessao = Sessao.objects.create(
            sessao_id="abc-5", titulo="Minha", usuario=self.usuario
        )
        Mensagem.objects.create(sessao=sessao, papel="USUARIO", conteudo="x")

        resposta = self.client.delete(f"/chat/sessoes/{sessao.id}/")
        self.assertEqual(resposta.status_code, 204)
        self.assertEqual(Mensagem.objects.count(), 0)


class AgentePersistenciaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(
            username="comum", password="senha123"
        )
        self.client.force_authenticate(user=self.usuario)

    @patch(
        "chat.services.conversa_service.processar_mensagem_usuario",
        return_value={
            "resposta": "eu não busco",
            "ferramenta_utilizada": False,
            "artigos": [],
        },
    )
    def test_mensagem_sem_sessao_cria_sessao_e_persiste(self, mock_rag):
        resposta = self.client.post(
            "/chat/agente/", {"mensagem": "o que é IA?"}, format="json"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.data["sessao_id"])

        sessao = Sessao.objects.get(sessao_id=resposta.data["sessao_id"])
        self.assertEqual(sessao.titulo, "o que é IA?")
        self.assertEqual(sessao.usuario, self.usuario)
        self.assertEqual(sessao.mensagens.count(), 2)
        papeis = [m.papel for m in sessao.mensagens.order_by("criada_em", "id")]
        self.assertEqual(papeis, ["USUARIO", "MODELO"])
        mock_rag.assert_called_once()

    @patch(
        "chat.services.conversa_service.processar_mensagem_usuario",
        return_value={
            "resposta": "Achei artigos úteis.",
            "ferramenta_utilizada": True,
            "artigos": [{"id": 42, "titulo": "Paper X"}],
        },
    )
    def test_artigos_sao_salvos_e_vai_para_contexto(self, mock_rag):
        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "procure sobre IA", "requisicao": "busca"},
            format="json",
        )
        sessao = Sessao.objects.get(sessao_id=resposta.data["sessao_id"])
        mensagem_modelo = sessao.mensagens.get(papel="MODELO")
        self.assertTrue(mensagem_modelo.ferramenta_utilizada)
        self.assertEqual(mensagem_modelo.artigos[0]["titulo"], "Paper X")
        self.assertEqual(sessao.artigos_contexto[0]["titulo"], "Paper X")

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_filtros_sao_repassados_ao_rag(self, mock_rag):
        mock_rag.return_value = {
            "resposta": "ok",
            "ferramenta_utilizada": False,
            "artigos": [],
        }
        resposta = self.client.post(
            "/chat/agente/",
            {
                "mensagem": "procure artigos",
                "ano_inicio": 2018,
                "ano_fim": 2022,
                "area": "medicine",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(mock_rag.call_args.kwargs["ano_inicio"], 2018)
        self.assertEqual(mock_rag.call_args.kwargs["ano_fim"], 2022)
        self.assertEqual(mock_rag.call_args.kwargs["area"], "medicine")

    def test_areas_exige_autenticacao(self):
        anonimo = APIClient()
        resposta = anonimo.get("/chat/areas/")
        self.assertIn(resposta.status_code, (401, 403))

    def test_areas_retorna_valores_distintos(self):
        Artigo.objects.create(
            openalex_id="o-1", titulo="A", area_conhecimento="Medicine"
        )
        Artigo.objects.create(
            openalex_id="o-2", titulo="B", area_conhecimento="Medicine"
        )
        Artigo.objects.create(
            openalex_id="o-3", titulo="C", area_conhecimento="Computer Science"
        )
        resposta = self.client.get("/chat/areas/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            set(resposta.data["areas"]),
            {"Medicine", "Computer Science"},
        )

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_resposta_usa_historico_da_sessao(self, mock_rag):
        sessao = Sessao.objects.create(
            sessao_id="abc-6", titulo="Hist", usuario=self.usuario
        )
        Mensagem.objects.create(sessao=sessao, papel="USUARIO", conteudo="anterior")
        Mensagem.objects.create(
            sessao=sessao, papel="MODELO", conteudo="resposta anterior"
        )
        mock_rag.return_value = {
            "resposta": "nova resposta",
            "ferramenta_utilizada": False,
            "artigos": [],
        }

        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "pergunta", "sessao_id": "abc-6"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        hist_esperado = [
            {"role": "user", "content": "anterior"},
            {"role": "assistant", "content": "resposta anterior"},
        ]
        mock_rag.assert_called_once()
        self.assertEqual(mock_rag.call_args.kwargs["historico"], hist_esperado)
        self.assertEqual(sessao.mensagens.count(), 4)

    def test_agente_exige_autenticacao(self):
        anonimo = APIClient()
        resposta = anonimo.post("/chat/agente/", {"mensagem": "oi"}, format="json")
        self.assertIn(resposta.status_code, (401, 403))


class AutenticacaoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registrar_cria_usuario_e_loga(self):
        resposta = self.client.post(
            "/auth/registrar/",
            {"username": "novo", "password": "senha-forte-1"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(resposta.data["username"])
        self.assertTrue(User.objects.filter(username="novo").exists())
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_registrar_rejeita_username_repetido(self):
        User.objects.create_user(username="novo", password="senha123")
        resposta = self.client.post(
            "/auth/registrar/",
            {"username": "novo", "password": "senha-forte-1"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_login_estabelece_sessao_e_me_responde(self):
        User.objects.create_user(username="logado", password="senha123")
        resposta = self.client.post(
            "/auth/login/",
            {"username": "logado", "password": "senha123"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(self.client.session.get("_auth_user_id"))

        me = self.client.get("/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "logado")

    def test_login_invalido(self):
        resposta = self.client.post(
            "/auth/login/",
            {"username": "nao-existe", "password": "senha123"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_logout_encerra_sessao(self):
        User.objects.create_user(username="saindo", password="senha123")
        self.client.post(
            "/auth/login/",
            {"username": "saindo", "password": "senha123"},
            format="json",
        )
        resposta = self.client.post("/auth/logout/", format="json")
        self.assertEqual(resposta.status_code, 204)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_me_exige_autenticacao(self):
        resposta = self.client.get("/auth/me/")
        self.assertIn(resposta.status_code, (401, 403))

    def test_fluxo_sessao_com_csrf_permite_post(self):
        User.objects.create_user(username="csrf", password="senha123")

        cliente_csrf = APIClient(enforce_csrf_checks=True)

        token1 = cliente_csrf.get("/auth/csrf/").data["csrfToken"]
        login = cliente_csrf.post(
            "/auth/login/",
            {"username": "csrf", "password": "senha123"},
            format="json",
            HTTP_X_CSRFTOKEN=token1,
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(cliente_csrf.session.get("_auth_user_id"))

        token2 = cliente_csrf.get("/auth/csrf/").data["csrfToken"]

        sem = cliente_csrf.post(
            "/chat/sessoes/",
            {"titulo": "x"},
            format="json",
            HTTP_X_CSRFTOKEN="token-invalido",
        )
        self.assertEqual(sem.status_code, 403)

        com = cliente_csrf.post(
            "/chat/sessoes/",
            {"titulo": "Com csrf"},
            format="json",
            HTTP_X_CSRFTOKEN=token2,
        )
        self.assertEqual(com.status_code, 201)
        self.assertEqual(Sessao.objects.get(pk=com.data["id"]).titulo, "Com csrf")