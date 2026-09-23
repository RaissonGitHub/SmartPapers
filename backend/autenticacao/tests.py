from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class PreferenciasSegurancaTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="teste", password="senha-teste-123"
        )
        self.client = APIClient()
        self.client.force_login(self.usuario)

    def _definir_chave(self, chave):
        sessao = self.client.session
        sessao["pref_provider"] = "gemini"
        sessao["pref_api_key"] = chave
        sessao.save()

    def test_get_nao_expoe_chave_em_texto_puro(self):
        self._definir_chave("AIzaSyCHAVEAPTATESTESECRETA1234")
        resposta = self.client.get("/auth/preferencias/")
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("AIzaSyCHAVEAPTATESTESECRETA1234", resposta.data["api_key"])
        self.assertIn("\u2022\u2022", resposta.data["api_key"])
        self.assertTrue(resposta.data["api_key_definida"])

    def test_put_rejeita_chave_invalida(self):
        resposta = self.client.put(
            "/auth/preferencias/",
            {"provider": "gemini", "api_key": "x"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn("pref_api_key", self.client.session)

    def test_put_rejeita_chave_mascarada(self):
        resposta = self.client.put(
            "/auth/preferencias/",
            {"provider": "gemini", "api_key": "AIza\u2022\u2022\u2022\u2022wxyz"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_put_sem_api_key_nao_sobrescreve_chave_existente(self):
        self._definir_chave("AIzaSyCHAVEAPTATESTESECRETA1234")
        resposta = self.client.put(
            "/auth/preferencias/",
            {"provider": "gemini", "modelo": "gemini-3.8-flash"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            self.client.session.get("pref_api_key"),
            "AIzaSyCHAVEAPTATESTESECRETA1234",
        )

    def test_put_aceita_chave_valida_e_responde_mascarada(self):
        resposta = self.client.put(
            "/auth/preferencias/",
            {
                "provider": "gemini",
                "api_key": "AIzaSyCHAVENOVATESTESECRETA123",
                "modelo": "gemini-3.8-flash",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.data["api_key_definida"])
        self.assertNotIn("AIzaSyCHAVENOVATESTESECRETA123", resposta.data["api_key"])
        self.assertEqual(
            self.client.session.get("pref_api_key"),
            "AIzaSyCHAVENOVATESTESECRETA123",
        )

    def test_registro_nao_revela_existencia_de_usuario(self):
        User.objects.create_user(username="novo", password="senha123")
        resposta = self.client.post(
            "/auth/registrar/",
            {"username": "novo", "password": "senha-forte-1"},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn("já está em uso", str(resposta.data))
        self.assertNotIn("em uso", str(resposta.data))
        self.assertIn("não foi possível criar", str(resposta.data).lower())

    def test_login_tem_rate_limit(self):
        import rest_framework.throttling as throttling
        from unittest import mock

        anon = APIClient()
        with mock.patch.object(
            throttling.SimpleRateThrottle,
            "THROTTLE_RATES",
            {"login": "2/min"},
        ):
            statuses = [
                anon.post(
                    "/auth/login/",
                    {"username": "x", "password": "senha-errada"},
                    format="json",
                ).status_code
                for _ in range(3)
            ]
        self.assertEqual(statuses[-1], 429)
        self.assertTrue(all(s in (400, 429) for s in statuses))