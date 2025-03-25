from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

class AuthentikOIDCBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        User = get_user_model()
        user = User.objects.create_user(
            username=claims.get("preferred_username") or claims["sub"],
            email=claims.get("email", ""),
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
        )
        user.save()
        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", user.email)
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()
        return user
            