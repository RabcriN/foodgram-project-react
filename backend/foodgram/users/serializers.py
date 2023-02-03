from django.contrib.auth import authenticate
from djoser.compat import get_user_email_field_name
from rest_framework import serializers

from .models import User

INVALID_CREDENTIALS_ERROR = ("Unable to log in with provided credentials.")
INACTIVE_ACCOUNT_ERROR = ("User account is disabled.")


class TokenCreateSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=False,
        style={"input_type": "password"}
    )
    default_error_messages = {
        "invalid_credentials": INVALID_CREDENTIALS_ERROR,
        "inactive_account": INACTIVE_ACCOUNT_ERROR,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.email_field = get_user_email_field_name(User)
        self.fields[self.email_field] = serializers.EmailField()

    def validate(self, attrs):
        password = attrs.get("password")
        email = attrs.get("email").lower()
        self.user = authenticate(
            request=self.context.get("request"), email=email, password=password
        )
        if not self.user:
            self.user = User.objects.filter(email=email).first()
            if self.user and not self.user.check_password(password):
                self.fail("invalid_credentials")
        if self.user and self.user.is_active:
            return attrs
        self.fail("invalid_credentials")
