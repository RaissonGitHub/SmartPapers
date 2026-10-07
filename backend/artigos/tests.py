"""Testes do app artigos: modelos, serializers e endpoints públicos."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from artigos.models import Artigo, Autor

User = get_user_model()

USUARIO = "teste-artigos"
SENHA = "senha-forte-123"

CAMPOS_ARTIGO = {
    "openalex_id",
    "titulo",
    "resumo",
    "ano_publicacao",
    "area_conhecimento",
    "link_original",
    "fonte",
}


def criar_artigo(**extras):
    dados = {
        "openalex_id": "W-final",
        "titulo": "Título",
        "resumo": "Resumo",
        "ano_publicacao": 2021,
        "area_conhecimento": "Educação",
        "link_original": "https://exemplo.org/w-final",
    }
    dados.update(extras)
    return Artigo.objects.create(**dados)


class ArtigoModelTest(TestCase):
    def setUp(self):
        self.autor = Autor.objects.create(nome="Ada Lovelace", openalex_id="A-1")
        self.artigo = criar_artigo()
        self.artigo.autores.add(self.autor)

    def test_str_de_artigo(self):
        self.assertEqual(str(self.artigo), "Título")

    def test_str_de_autor(self):
        self.assertEqual(str(self.autor), "A-1 - Ada Lovelace")

    def test_vinculo_com_autores(self):
        self.assertCountEqual(self.artigo.autores.all(), [self.autor])

    def test_openalex_id_e_unico(self):
        with self.assertRaises(Exception):
            criar_artigo(openalex_id="W-final", titulo="Duplicado")


class ArtigoEndpointsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(username=USUARIO, password=SENHA)
        for indice in range(5):
            criar_artigo(
                openalex_id=f"W-{indice}",
                titulo=f"Artigo {indice}",
                ano_publicacao=2020 + indice,
            )

    def _login(self):
        self.assertTrue(self.client.login(username=USUARIO, password=SENHA))

    def test_lista_artigos_exige_autenticacao(self):
        self.assertEqual(self.client.get("/artigos/listar/").status_code, 403)

    def test_lista_artigos_paginada(self):
        self._login()
        resposta = self.client.get("/artigos/listar/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["count"], 5)
        self.assertEqual(len(resposta.data["results"]), 5)

    def test_campos_serializados(self):
        self._login()
        resposta = self.client.get("/artigos/listar/")
        primeiro = resposta.data["results"][0]
        self.assertEqual(set(primeiro), CAMPOS_ARTIGO)
        self.assertIn("openalex_id", primeiro)

    def test_lista_autores(self):
        self._login()
        Autor.objects.create(nome="Alan Turing", openalex_id="A-2")
        resposta = self.client.get("/artigos/autores/")
        self.assertEqual(resposta.status_code, 200)
        nomes = [a["nome"] for a in resposta.data["results"]]
        self.assertIn("Alan Turing", nomes)