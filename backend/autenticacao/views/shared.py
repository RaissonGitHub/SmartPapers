from rest_framework import serializers


def contexto_do_serializer(view):
    return {"request": view.request, "view": view}


def resposta_usuario(user):
    return {"id": user.id, "username": user.username}


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=10, write_only=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)