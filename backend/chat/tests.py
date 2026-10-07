import json
import threading
from unittest.mock import patch

from artigos.models.artigo import Artigo
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from chat.models import Mensagem, Sessao
from chat.services.cancelamento import CHAVE_PREFIXO, RequisicaoCancelada
from chat.services.gemini_provider import GeminiProvider
from chat.services.orcamento import (
    TempoEsgotado,
    checar_orcamento,
    definir_orcamento,
    limpar_orcamento,
    tempo_restante,
)
from chat.services.pdf_service import _parsear_resumo_secoes
from chat.services.providers import OllamaProvider
from chat.services.rag import (
    _intencao_busca,
    _normalizar_anos_tool_call,
    _substituir_ancoras_por_titulo,
    selecionar_pdf,
)
from chat.services.refinamento import rerank_por_aderencia


class NormalizacaoAnosToolCallTestCase(TestCase):
    def setUp(self):
        Artigo.objects.create(
            openalex_id="o-antigo", titulo="Antigo", ano_publicacao=2017
        )
        Artigo.objects.create(
            openalex_id="o-novo", titulo="Novo", ano_publicacao=2025
        )

    def test_intervalo_fora_da_base_usa_janela_disponivel(self):
        args = {"ano_inicio": 2010, "ano_fim": 2015}

        _normalizar_anos_tool_call(args)

        self.assertEqual(args["ano_inicio"], 2017)
        self.assertEqual(args["ano_fim"], 2025)

    def test_intervalo_valido_e_preservado(self):
        args = {"ano_inicio": 2021, "ano_fim": 2025}

        _normalizar_anos_tool_call(args)

        self.assertEqual(args, {"ano_inicio": 2021, "ano_fim": 2025})


class NormalizacaoAnosSemBaseTestCase(TestCase):
    def test_base_vazia_usa_janela_fallback(self):
        args = {"ano_inicio": 1999, "ano_fim": 1999}

        _normalizar_anos_tool_call(args)

        self.assertEqual(args["ano_inicio"], 2020)
        self.assertEqual(args["ano_fim"], 2026)


class OllamaTimeoutTestCase(TestCase):
    @patch("ollama.Client")
    def test_timeout_e_configurado_no_cliente_http(self, mock_client):
        mock_client.return_value.chat.return_value.message.content = "resposta"
        provedor = OllamaProvider(modelo="teste")

        provedor.chat_simple([])

        self.assertEqual(mock_client.call_args.kwargs["timeout"], 120)
        self.assertNotIn("timeout", mock_client.return_value.chat.call_args.kwargs)


class SubstituicaoAncoraLinksTestCase(TestCase):
    def test_substitui_texto_visivel_pelo_titulo(self):
        resposta = (
            "Veja [clique aqui](https://doi.org/10.1234) e [x](https://outro.org)"
        )
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
        self.usuario = User.objects.create_user(username="teste", password="senha123")
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
        self.usuario = User.objects.create_user(username="comum", password="senha123")
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

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_erro_do_provedor_nao_cria_sessao_fantasma(self, mock_rag):
        from google.genai import errors as erros_genai

        mock_rag.side_effect = erros_genai.ClientError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "The model is overloaded.",
                    "status": "UNAVAILABLE",
                }
            },
        )
        resposta = self.client.post(
            "/chat/agente/",
            {
                "mensagem": "oi",
                "provider": "gemini",
                "api_key": "AIzaSytesteCHAVESECRETA1234",
                "modelo": "gemini-3.8-flash",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 502)
        self.assertEqual(Sessao.objects.count(), 0)
        self.assertEqual(Mensagem.objects.count(), 0)

    def test_areas_exige_autenticacao(self):
        anonimo = APIClient()
        resposta = anonimo.get("/chat/areas/")
        self.assertIn(resposta.status_code, (401, 403))

    def test_areas_retorna_valores_distintos(self):
        Artigo.objects.create(
            openalex_id="o-1", titulo="A", area_conhecimento="Medicine", ano_publicacao=2018
        )
        Artigo.objects.create(
            openalex_id="o-2", titulo="B", area_conhecimento="Medicine", ano_publicacao=2021
        )
        Artigo.objects.create(
            openalex_id="o-3", titulo="C", area_conhecimento="Computer Science", ano_publicacao=2021
        )
        resposta = self.client.get("/chat/areas/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            set(resposta.data["areas"]),
            {"Medicine", "Computer Science"},
        )
        self.assertEqual(resposta.data["ano_minimo"], 2018)
        self.assertEqual(resposta.data["ano_maximo"], 2021)

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


class AgentePdfTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username="pdf", password="senha123")
        self.client.force_authenticate(user=self.usuario)
        self.arquivo = SimpleUploadedFile(
            "artigo.pdf", b"%PDF-1.4 dados-falsos", content_type="application/pdf"
        )

    def _mensagem_modelo_padrao(self, resposta="ok"):
        return {
            "resposta": resposta,
            "ferramenta_utilizada": False,
            "artigos": [],
        }

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    @patch("chat.services.conversa_service.processar_pdf")
    def test_pdf_persiste_nome_e_secoes(self, mock_pdf, mock_rag):
        secoes = [{"indice": 1, "resumo": "Metodologia", "texto": "Texto da seção."}]
        mock_pdf.return_value = secoes
        mock_rag.return_value = self._mensagem_modelo_padrao()

        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "use este pdf como base", "pdf": self.arquivo},
            format="multipart",
        )
        self.assertEqual(resposta.status_code, 200)

        sessao = Sessao.objects.get(sessao_id=resposta.data["sessao_id"])
        self.assertEqual(sessao.pdf_nome, "artigo.pdf")
        self.assertEqual(sessao.pdf_secoes, secoes)

        mensagem_usuario = sessao.mensagens.get(papel="USUARIO")
        self.assertEqual(mensagem_usuario.pdf_nome, "artigo.pdf")

        self.assertEqual(mock_pdf.call_args.args[1], ["use este pdf como base"])
        self.assertEqual(mock_rag.call_args.kwargs["pdf_secoes"], secoes)

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_pdf_rejeita_arquivo_nao_pdf(self, mock_rag):
        mock_rag.return_value = self._mensagem_modelo_padrao()
        arquivo_txt = SimpleUploadedFile(
            "nota.txt", b"texto", content_type="text/plain"
        )
        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "use o anexo", "pdf": arquivo_txt},
            format="multipart",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Sessao.objects.count(), 0)

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_pdf_depende_de_mensagem(self, mock_rag):
        mock_rag.return_value = self._mensagem_modelo_padrao()
        resposta = self.client.post(
            "/chat/agente/",
            {"pdf": self.arquivo},
            format="multipart",
        )
        self.assertEqual(resposta.status_code, 400)

    @patch("chat.services.conversa_service.processar_mensagem_usuario")
    def test_secoes_persistidas_usadas_sem_novo_pdf(self, mock_rag):
        sessao = Sessao.objects.create(
            sessao_id="abc-pdf",
            titulo="Com pdf",
            usuario=self.usuario,
            pdf_nome="anexo.pdf",
            pdf_secoes=[{"indice": 1, "resumo": "Resumo", "texto": "Texto"}],
        )
        Mensagem.objects.create(sessao=sessao, papel="USUARIO", conteudo="oi")
        Mensagem.objects.create(sessao=sessao, papel="MODELO", conteudo="x")
        mock_rag.return_value = self._mensagem_modelo_padrao()

        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "continue", "sessao_id": "abc-pdf"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            mock_rag.call_args.kwargs["pdf_secoes"],
            [{"indice": 1, "resumo": "Resumo", "texto": "Texto"}],
        )

    def test_mensagens_retornadas_em_ordem_cronologica(self):
        sessao = Sessao.objects.create(
            sessao_id="ordem-msg",
            titulo="Ordem",
            usuario=self.usuario,
        )
        for conteudo in ["pergunta 1", "resposta 1", "pergunta 2", "resposta 2"]:
            papel = "USUARIO" if conteudo.startswith("pergunta") else "MODELO"
            Mensagem.objects.create(sessao=sessao, papel=papel, conteudo=conteudo)

        resposta = self.client.get(f"/chat/sessoes/{sessao.id}/")
        self.assertEqual(resposta.status_code, 200)
        conteudos = [m["conteudo"] for m in resposta.data["mensagens"]]
        self.assertEqual(
            conteudos, ["pergunta 1", "resposta 1", "pergunta 2", "resposta 2"]
        )


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
        self.assertNotIn("já está em uso", str(resposta.data))
        self.assertNotIn("em uso", str(resposta.data))

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


class GeminiMultiturnTestCase(TestCase):
    def test_modelo_single_turn_recebe_apenas_ultimo_turno(self):
        from unittest.mock import MagicMock

        from google.genai import errors as erros_genai

        provedor = GeminiProvider(modelo="antigravity-preview-05-2026", api_key="x")
        client = MagicMock()
        provedor._client = client

        erro = erros_genai.ClientError(
            400,
            {
                "error": {
                    "code": 400,
                    "message": "Multiturn chat is not enabled for "
                    "models/antigravity-preview-05-2026",
                    "status": "INVALID_ARGUMENT",
                }
            },
        )
        client.models.generate_content.side_effect = [erro, MagicMock()]

        provedor.chat(
            [
                {"role": "system", "content": "instrucao"},
                {"role": "user", "content": "primeira pergunta"},
                {"role": "assistant", "content": "primeira resposta"},
                {"role": "user", "content": "segunda pergunta"},
            ],
            tools=[lambda: None],
        )

        chamadas = client.models.generate_content.call_args_list
        self.assertEqual(len(chamadas), 2)
        conteudos = chamadas[1].kwargs["contents"]
        self.assertEqual(len(conteudos), 1)
        self.assertEqual(
            conteudos[0].parts[0].text,
            "segunda pergunta",
        )

    @patch("google.genai.Client")
    def test_listar_modelos_filtra_preview_single_turn(self, mock_client):
        from chat.services.gemini_provider import listar_modelos_gemini

        def fake_modelo(nome, display=None):
            return type(
                "FakeModel",
                (),
                {
                    "name": f"models/{nome}",
                    "display_name": display or nome,
                    "supported_actions": [
                        "generateContent",
                        "GenerateContent",
                    ],
                },
            )()

        mock_client.return_value.models.list.return_value = [
            fake_modelo("gemini-2.5-flash", "Gemini 2.5 Flash"),
            fake_modelo("antigravity-preview-05-2026", "Antigravity Preview"),
            fake_modelo("gemini-3.8-flash", "Gemini 3.8 Flash"),
        ]

        modelos = listar_modelos_gemini("CHAVE-X")

        nomes = [m["name"] for m in modelos]
        self.assertNotIn("antigravity-preview-05-2026", nomes)
        self.assertNotIn("gemini-2.5-flash", nomes)
        self.assertIn("gemini-3.8-flash", nomes)
        self.assertEqual(len(modelos), 1)


class AgenteErroProvedorTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username="erro", password="senha123")
        self.client.force_authenticate(user=self.usuario)

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_erro_da_api_gemini_vira_502_com_mensagem_limpa(self, mock_processar):
        from google.genai import errors as erros_genai

        mock_processar.side_effect = erros_genai.ClientError(
            400,
            {
                "error": {
                    "code": 400,
                    "message": "API key not valid.",
                    "status": "INVALID_ARGUMENT",
                }
            },
        )

        resposta = self.client.post(
            "/chat/agente/",
            {
                "mensagem": "oi",
                "provider": "gemini",
                "api_key": "AIzaSytesteCHAVESECRETA1234",
                "modelo": "gemini-3.8-flash",
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 502)
        self.assertIn("chave de api", resposta.data["erro"].lower())
        self.assertNotIn("AIzaSytesteCHAVESECRETA1234", resposta.data["erro"])
        self.assertNotIn("API key not valid", resposta.data["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_erro_generico_da_api_gemini_mantem_preambulo(self, mock_processar):
        from google.genai import errors as erros_genai

        mock_processar.side_effect = erros_genai.ClientError(
            429,
            {
                "error": {
                    "code": 429,
                    "message": "Quota exceeded for model.",
                    "status": "RESOURCE_EXHAUSTED",
                }
            },
        )

        resposta = self.client.post(
            "/chat/agente/",
            {
                "mensagem": "oi",
                "provider": "gemini",
                "api_key": "AIzaSytesteCHAVESECRETA1234",
                "modelo": "gemini-3.8-flash",
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 502)
        self.assertIn("Erro na chamada ao Gemini", resposta.data["erro"])
        self.assertNotIn("AIzaSytesteCHAVESECRETA1234", resposta.data["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_chave_antiga_invalida_na_sessao_nao_bloqueia_envio(self, mock_processar):
        mock_processar.return_value = {
            "sessao": 9,
            "sessao_id": "abc-invalida",
            "mensagens": [],
        }
        sessao = self.client.session
        sessao["pref_provider"] = "gemini"
        sessao["pref_api_key"] = "AIza\u2022\u2022\u2022\u2022wxyz"
        sessao["pref_modelo"] = "gemini-3.8-flash"
        sessao.save()

        resposta = self.client.post("/chat/agente/", {"mensagem": "oi"}, format="json")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["sessao_id"], "abc-invalida")


class AgenteValidacaoEntradaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username="limit", password="senha123")
        self.client.force_authenticate(user=self.usuario)
        self.base = {
            "mensagem": "oi",
            "provider": "gemini",
            "api_key": "AIzaSytesteCHAVESECRETA1234",
            "modelo": "gemini-3.8-flash",
        }

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_mensagem_dentro_do_limite_prossegue(self, mock_processar):
        mock_processar.return_value = {"ok": True, "modelo": "x", "tempo": 0.0}
        self.base["mensagem"] = "a" * 50000
        resposta = self.client.post("/chat/agente/", self.base, format="json")
        self.assertEqual(resposta.status_code, 200)

    def test_mensagem_acima_do_limite_e_rejeitada(self):
        self.base["mensagem"] = "a" * 50001
        resposta = self.client.post("/chat/agente/", self.base, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("muito longa", resposta.data["erro"])

    def test_pdf_falso_pela_extensao_e_rejeitado(self):
        falso = SimpleUploadedFile("malware.pdf", b"MZ\x90\x00\x00\x00" + b"X" * 4096)
        self.base["pdf"] = falso
        resposta = self.client.post("/chat/agente/", self.base, format="multipart")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("não é um PDF válido", resposta.data["erro"])

    def test_arquivo_nao_pdf_por_extensao_e_rejeitado(self):
        exe = SimpleUploadedFile("malware.exe", b"x" * 512)
        self.base["pdf"] = exe
        resposta = self.client.post("/chat/agente/", self.base, format="multipart")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("arquivo PDF", resposta.data["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_pdf_grande_e_rejeitado(self, mock_processar):
        valido = SimpleUploadedFile("grande.pdf", b"%PDF-1.7\n" + b"0" * 64)
        with patch("chat.views.agent_chat.MAX_PDF_BYTES", 10):
            self.base["pdf"] = valido
            resposta = self.client.post("/chat/agente/", self.base, format="multipart")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("muito grande", resposta.data["erro"])
        mock_processar.assert_not_called()

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_pdf_valido_prossegue_para_processamento(self, mock_processar):
        mock_processar.return_value = {"ok": True, "modelo": "x", "tempo": 0.0}
        valido = SimpleUploadedFile("nota.pdf", b"%PDF-1.7\nconteudo")
        self.base["pdf"] = valido
        resposta = self.client.post("/chat/agente/", self.base, format="multipart")
        self.assertEqual(resposta.status_code, 200)


class PdfRobustezFormatacaoTestCase(TestCase):
    def test_parsear_resumo_trata_fences_negrito_e_acento(self):
        resposta = (
            "```json\n"
            "Resumo das seções:\n"
            "SECAO 1 | **conteúdo** | Introduz o tema e define o escopo da pesquisa.\n"
            "SECAO 2 | conteudo | Discute a metodologia aplicada na coleta de dados.\n"
            "SECAO 4 | referência | Cita estudos anteriores sobre o tema.\n"
            "```\n"
        )

        resultado = _parsear_resumo_secoes(resposta)

        self.assertEqual(
            resultado[1], ("conteudo", "Introduz o tema e define o escopo da pesquisa.")
        )
        self.assertEqual(
            resultado[2], ("conteudo", "Discute a metodologia aplicada na coleta de dados.")
        )
        self.assertEqual(
            resultado[4], ("referencia", "Cita estudos anteriores sobre o tema.")
        )
        self.assertNotIn(3, resultado)

    def test_selecionar_pdf_ignora_json_fenced_com_texto(self):
        from unittest.mock import Mock

        provedor = Mock()
        provedor.chat_simple.return_value = (
            'O documento mais relevante é o seguinte:\n'
            '```json\n{"pdf_id": 2}\n```\n'
        )
        pdfs = [
            {"id": 1, "nome": "artigo a.pdf", "secoes": [{"indice": 1}]},
            {"id": 2, "nome": "artigo b.pdf", "secoes": [{"indice": 1}, {"indice": 2}]},
        ]

        pdf_id, secoes = selecionar_pdf(pdfs, "explique esta nota", provedor)

        self.assertEqual(pdf_id, 2)
        self.assertEqual(len(secoes), 2)

    def test_selecionar_pdf_resposta_invalida_cai_no_primeiro_pdf(self):
        from unittest.mock import Mock

        provedor = Mock()
        provedor.chat_simple.return_value = (
            "Não sei qual documento escolher, todos parecem relevantes."
        )
        pdfs = [
            {"id": 1, "nome": "artigo a.pdf", "secoes": [{"indice": 1}]},
            {"id": 2, "nome": "artigo b.pdf", "secoes": [{"indice": 1}]},
        ]

        pdf_id, secoes = selecionar_pdf(pdfs, "explique este pdf", provedor)

        self.assertEqual(pdf_id, 1)
        self.assertEqual(len(secoes), 1)

def test_selecionar_pdf_null_explicito_nao_forca_fallback(self):
        from unittest.mock import Mock

        provedor = Mock()
        provedor.chat_simple.return_value = '{"pdf_id": null}'
        pdfs = [
            {"id": 1, "nome": "artigo a.pdf", "secoes": [{"indice": 1}]},
            {"id": 2, "nome": "artigo b.pdf", "secoes": [{"indice": 1}]},
        ]

        pdf_id, secoes = selecionar_pdf(pdfs, "pergunta geral", provedor)

        self.assertIsNone(pdf_id)
        self.assertEqual(secoes, [])


class OrcamentoTempoTestCase(TestCase):
    def tearDown(self):
        limpar_orcamento()

    def test_sem_orcamento_aberto_nao_ha_limite(self):
        limpar_orcamento()
        self.assertIsNone(tempo_restante())
        checar_orcamento("busca")

    def test_tempo_restante_conta_regressivamente(self):
        definir_orcamento(30)
        restante = tempo_restante()
        self.assertIsNotNone(restante)
        self.assertGreater(restante, 0)
        self.assertLessEqual(restante, 30)

    def test_orcamento_zerado_esgota_na_hora(self):
        definir_orcamento(0)
        self.assertEqual(tempo_restante(), 0)
        with self.assertRaises(TempoEsgotado) as contexto:
            checar_orcamento("busca")
        self.assertEqual(contexto.exception.etapa, "busca")
        self.assertIn("demorou demais", str(contexto.exception))

    def test_limpar_orcamento_remove_o_limite(self):
        definir_orcamento(0)
        limpar_orcamento()
        checar_orcamento("busca")


class GeminiTimeoutOrcamentoTestCase(TestCase):
    def tearDown(self):
        limpar_orcamento()

    def test_timeout_padrao_sem_orcamento(self):
        provedor = GeminiProvider(modelo="teste", api_key="chave")
        with patch("google.genai.Client") as mock_client:
            provedor._get_client()
        opcoes = mock_client.call_args.kwargs["http_options"]
        self.assertEqual(opcoes.timeout, 90_000)

    def test_timeout_usa_o_tempo_restante_do_orcamento(self):
        definir_orcamento(12)
        provedor = GeminiProvider(modelo="teste", api_key="chave")
        with patch("google.genai.Client") as mock_client:
            provedor._get_client()
        opcoes = mock_client.call_args.kwargs["http_options"]
        self.assertGreater(opcoes.timeout, 5_000)
        self.assertLessEqual(opcoes.timeout, 12_000)

    def test_orcamento_no_fim_ainda_usa_o_piso(self):
        definir_orcamento(0)
        provedor = GeminiProvider(modelo="teste", api_key="chave")
        with patch("google.genai.Client") as mock_client:
            provedor._get_client()
        opcoes = mock_client.call_args.kwargs["http_options"]
        self.assertEqual(opcoes.timeout, 5_000)

    def test_teto_configuravel_por_env(self):
        import chat.services.gemini_provider as modulo

        original = modulo.GEMINI_TIMEOUT_SEGUNDOS
        modulo.GEMINI_TIMEOUT_SEGUNDOS = 7.0
        try:
            provedor = GeminiProvider(modelo="teste", api_key="chave")
            with patch("google.genai.Client") as mock_client:
                provedor._get_client()
            opcoes = mock_client.call_args.kwargs["http_options"]
            self.assertEqual(opcoes.timeout, 7_000)
        finally:
            modulo.GEMINI_TIMEOUT_SEGUNDOS = original


class AgenteStreamingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username="fluxo", password="senha123")
        self.client.force_authenticate(user=self.usuario)
        self.requisicao_id = "req-teste-stream"

    def _eventos(self, resposta):
        brutos = list(resposta.streaming_content)
        return [json.loads(bruto.decode("utf-8")) for bruto in brutos]

    def _enviar(self, corpo=None):
        dados = {
            "mensagem": "procure artigos",
            "requisicao_id": self.requisicao_id,
            "stream": "true",
        }
        dados.update(corpo or {})
        return self.client.post("/chat/agente/", dados, format="json")

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_query_stream_ativa_o_streaming(self, mock_processar):
        mock_processar.return_value = {"resposta": "ok"}

        resposta = self.client.post(
            "/chat/agente/?stream=1",
            {"mensagem": "oi", "requisicao_id": self.requisicao_id},
            format="json",
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self._eventos(resposta)[-1]["tipo"], "resultado")

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_resultado_chega_como_evento_ndjson(self, mock_processar):
        mock_processar.return_value = {
            "resposta": "Achei artigos.",
            "sessao_id": "abc",
            "sessao": 7,
            "mensagens": [],
        }

        resposta = self._enviar()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/x-ndjson")
        self.assertEqual(resposta["X-Accel-Buffering"], "no")
        eventos = self._eventos(resposta)
        self.assertEqual(eventos[-1]["tipo"], "resultado")
        self.assertEqual(eventos[-1]["dados"]["resposta"], "Achei artigos.")

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_etapas_sao_publicadas_antes_do_resultado(self, mock_processar):
        def fake(**kwargs):
            from chat.services import progresso

            progresso.avancar("busca", "Buscando artigos na base…")
            return {"resposta": "ok", "sessao_id": "abc", "sessao": 7, "mensagens": []}

        mock_processar.side_effect = fake

        eventos = self._eventos(self._enviar())

        tipos = [evento["tipo"] for evento in eventos]
        self.assertIn("etapa", tipos)
        self.assertLess(tipos.index("etapa"), tipos.index("resultado"))
        etapa = next(e for e in eventos if e["tipo"] == "etapa")
        self.assertEqual(etapa["etapa"], "busca")
        self.assertEqual(etapa["texto"], "Buscando artigos na base…")

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_campo_stream_aceita_valores_verdadeiros(self, mock_processar):
        mock_processar.return_value = {"resposta": "ok"}

        resposta = self._enviar({"stream": "sim"})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self._eventos(resposta)[-1]["tipo"], "resultado")

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_sem_stream_continua_respondendo_json(self, mock_processar):
        mock_processar.return_value = {"resposta": "ok", "sessao_id": "abc"}

        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "oi", "requisicao_id": self.requisicao_id},
            format="json",
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["resposta"], "ok")
        self.assertTrue(resposta["Content-Type"].startswith("application/json"))

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_erro_do_provedor_vira_evento_de_erro(self, mock_processar):
        from google.genai import errors as erros_genai

        mock_processar.side_effect = erros_genai.ClientError(
            429, {"error": {"code": 429, "message": "Quota exceeded for model."}}
        )

        eventos = self._eventos(
            self._enviar({"provider": "gemini", "api_key": "AIzaSyCHAVESECRETA1234"})
        )

        self.assertEqual(eventos[-1]["tipo"], "erro")
        self.assertEqual(eventos[-1]["status"], 502)
        self.assertIn("Erro na chamada ao Gemini", eventos[-1]["erro"])
        self.assertNotIn("AIzaSyCHAVESECRETA1234", eventos[-1]["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_tempo_esgotado_via_504_no_stream(self, mock_processar):
        mock_processar.side_effect = TempoEsgotado("busca")

        eventos = self._eventos(self._enviar())

        self.assertEqual(eventos[-1]["tipo"], "erro")
        self.assertEqual(eventos[-1]["status"], 504)
        self.assertIn("demorou demais", eventos[-1]["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_tempo_esgotado_via_504_no_json(self, mock_processar):
        mock_processar.side_effect = TempoEsgotado("busca")

        resposta = self.client.post(
            "/chat/agente/",
            {"mensagem": "oi", "requisicao_id": self.requisicao_id},
            format="json",
        )

        self.assertEqual(resposta.status_code, 504)
        self.assertIn("demorou demais", resposta.data["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_valor_invalido_do_provedor_via_400_no_stream(self, mock_processar):
        mock_processar.side_effect = ValueError("Provedor desconhecido: 'x'.")

        eventos = self._eventos(self._enviar())

        self.assertEqual(eventos[-1]["tipo"], "erro")
        self.assertEqual(eventos[-1]["status"], 400)
        self.assertIn("Provedor desconhecido", eventos[-1]["erro"])

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_cancelamento_vira_evento_de_cancelada(self, mock_processar):
        mock_processar.side_effect = RequisicaoCancelada()

        eventos = self._eventos(self._enviar())

        self.assertEqual(eventos[-1]["tipo"], "cancelada")
        self.assertEqual(eventos[-1]["requisicao_id"], self.requisicao_id)

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_cliente_desistir_cancela_o_pipeline(self, mock_processar):
        liberado = threading.Event()

        def fake(**kwargs):
            from chat.services import progresso

            progresso.avancar("busca", "Busy…")
            liberado.wait(5)
            return {"resposta": "ok"}

        mock_processar.side_effect = fake

        resposta = self._enviar()
        # streaming_content vem embrulhado em map(), que não tem close(); o
        # gerador de verdade (e o seu finally) fica em _iterator.
        gerador = resposta._iterator
        self.assertIn(b"etapa", next(gerador))
        gerador.close()

        self.assertTrue(
            cache.get(CHAVE_PREFIXO + self.requisicao_id),
            "esperava o cancelamento cooperativo após o cliente desistir",
        )
        liberado.set()

    @patch("chat.views.agent_chat.processar_e_salvar")
    def test_pdf_com_stream_tambem_responde_em_ndjson(self, mock_processar):
        mock_processar.return_value = {"resposta": "ok", "pdf_nome": "nota.pdf"}
        valido = SimpleUploadedFile("nota.pdf", b"%PDF-1.7\nconteudo")
        dados = {
            "mensagem": "explique o pdf",
            "requisicao_id": self.requisicao_id,
            "stream": "1",
            "pdf": valido,
        }

        resposta = self.client.post("/chat/agente/", dados, format="multipart")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self._eventos(resposta)[-1]["tipo"], "resultado")


class IntencaoBuscaTestCase(TestCase):
    def test_detecta_pedidos_explicitos(self):
        for frase in [
            "busque artigos sobre o tema",
            "procure referências semelhantes",
            "consegue trazer artigos que tratam do mesmo tema?",
            "pesquise papers relacionados",
            "recomende artigos científicos",
            "com base no artigo procure sobre o mesmo tema",
        ]:
            self.assertTrue(_intencao_busca(frase), frase)

    def test_nao_detecta_perguntas_conceituais(self):
        for frase in [
            "o que é machine learning?",
            "explique a fotossíntese",
            "resuma o que o pdf diz",
            "por que o céu é azul?",
        ]:
            self.assertFalse(_intencao_busca(frase), frase)

    def test_nao_detecta_consultas_curtas_vagas(self):
        self.assertFalse(_intencao_busca("ok"))
        self.assertFalse(_intencao_busca("obrigado"))
        self.assertFalse(_intencao_busca(""))


class RerankAderenciaTestCase(TestCase):
    def setUp(self):
        self.artigos = [
            {
                "id": 1,
                "titulo": "The Netflix Recommender System",
                "autores": [],
                "ano_publicacao": 2015,
                "area_conhecimento": "Computer Science",
                "similaridade": 94.3,
            },
            {
                "id": 2,
                "titulo": "Graph Neural Networks in Recommender Systems",
                "autores": [],
                "ano_publicacao": 2022,
                "area_conhecimento": "Computer Science",
                "similaridade": 90.0,
            },
            {
                "id": 3,
                "titulo": "Bibliometrics for academic publishing",
                "autores": [],
                "ano_publicacao": 2021,
                "area_conhecimento": "Decision Sciences",
                "similaridade": 88.0,
            },
        ]

    def _provedor(self, resposta):
        from unittest.mock import Mock

        provedor = Mock()
        provedor.chat_simple.return_value = resposta
        return provedor

    def test_marcador_ausente_mantem_ranking_vetorial(self):
        provedor = self._provedor(
            "Os artigos tratam de recomendações e processamento de linguagem."
        )

        resultado = rerank_por_aderencia("recomendação de artigos", self.artigos, 2, provedor)

        self.assertEqual([a["id"] for a in resultado], [1, 2])

    def test_marcador_vazio_com_candidatos_fracos_devolve_vazia(self):
        fracos = [
            {"id": 1, "titulo": "A", "similaridade": 45.0},
            {"id": 2, "titulo": "B", "similaridade": 40.0},
        ]
        provedor = self._provedor("Nenhum artigo aderente.\nARTIGOS_ADERENTES: []")

        resultado = rerank_por_aderencia(
            "Pergunta fora do escopo da base", fracos, 2, provedor
        )

        self.assertEqual(resultado, [])

    def test_marcador_vazio_com_candidatos_fortes_mantem_vetorial(self):
        provedor = self._provedor("Nenhum artigo aderente.\nARTIGOS_ADERENTES: []")

        resultado = rerank_por_aderencia("pergunta", self.artigos, 2, provedor)

        self.assertEqual([a["id"] for a in resultado], [1, 2])

    def test_marcador_reordena_por_aderencia(self):
        provedor = self._provedor("Preferência por bibliometria.\nARTIGOS_ADERENTES: [3, 1]")

        resultado = rerank_por_aderencia("pergunta", self.artigos, 2, provedor)

        self.assertEqual([a["id"] for a in resultado], [3, 1])

    def test_falha_no_provedor_mantem_ranking_vetorial(self):
        from unittest.mock import Mock

        provedor = Mock()
        provedor.chat_simple.side_effect = RuntimeError("gemini indisponível")

        resultado = rerank_por_aderencia("pergunta", self.artigos, 2, provedor)

        self.assertEqual([a["id"] for a in resultado], [1, 2])
