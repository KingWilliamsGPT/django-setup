import re
import random
import string

from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from src.users.models import User
from src.users.permissions import IsUserOrReadOnly
from src.users.serializers import CreateUserSerializer, UserSerializer, PasswordResetSerializer, ResetPasswordAndSendEmailSerializer
from src.common.helpers import GetFrontendLink
from src.common import zeptomail



LENGTH_OF_NEW_PASSWORD = 10
FRONTEND_LOGIN_URL = GetFrontendLink('login')
FRONTEND_GENERAL_SETTINGS_LINK = GetFrontendLink('general_settings')

def contains(s, pattern):
    return bool(re.search(pattern, s))

def generate_password(n=LENGTH_OF_NEW_PASSWORD):
    x = string.ascii_letters + '$#%^&~|?_'
    return ''.join([random.choice(x) for i in range(n)])



class UserViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Creates, Updates and Retrieves - User Accounts
    """

    queryset = User.objects.all()
    serializers = {
        'default': UserSerializer,
        'create': CreateUserSerializer,
        'password_reset': PasswordResetSerializer, 
        'reset_and_send_password_to_email': ResetPasswordAndSendEmailSerializer, 
    }
    permissions = {
        'default': (IsUserOrReadOnly,),
        'create': (IsAuthenticated,),
        'reset_and_send_password_to_email': (),
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

    def get_permissions(self):
        self.permission_classes = self.permissions.get(self.action, self.permissions['default'])
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='me', url_name='me')
    def get_user_data(self, instance):
        try:
            return Response(UserSerializer(self.request.user, context={'request': self.request}).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Wrong auth token' + e}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put'])
    def password_reset(self, request):
        '''Reset password when user is logged in'''
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password, confirm_new, old_password = serializer.validated_data['new_password'], serializer.validated_data['repeat_new_password'], serializer.validated_data['old_password']

        if new_password != confirm_new:
            raise ValidationError('new password and it\'s confirmation did not match')

        user = request.user
        if user.check_password(old_password):
            if self.password_is_strong(new_password, user.username):
                user.set_password(new_password)
                user.save()
                return Response({'msg': 'password reset successfully'})
            else:
                raise ValidationError({'error': 'password is not strong'})
        
        raise ValidationError({'error': 'invalid old password'})


    @action(detail=False, methods=['put'])
    def reset_and_send_password_to_email(self, request):
        # collect email from the user
        from src.ebaystuff.views import EbayMailer
        from src.store.models import GetUserSettings

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()
        if user:
            new_password = generate_password()
            user.set_password(new_password)
            user.save()

            user_agent = request.META.get('HTTP_USER_AGENT', '')

            mailer = EbayMailer(
                title='Resetowanie hasła 🔐',
                msg=f'''
                    <p>Cześć, {user.get_full_name().strip() or user.username}</p><br>

                    <p>Zresetowaliśmy twoje hasło do <b>{new_password}</b>, zaloguj się, aby zmienić hasło</p>
                    <p><a href="{FRONTEND_LOGIN_URL}" class="btn btn-primary" target="_blank">Zaloguj się</a></p>

                    {f'<br/><pre style="font-size:12px;color:#999;">Poniżej znajdują się dane przeglądarki osoby zgłaszającej żądanie: <b>{user_agent}</b></pre>' if user_agent.strip() else ''}
                ''',
                view=GetUserSettings(user),
                info='Twoje hasło zostało zresetowane',
                footer=f'Jeśli ten proces nie został zainicjowany, rozważ zmianę adresu e-mail w <a href="{FRONTEND_GENERAL_SETTINGS_LINK}" target="_blank">ustawieniach ogólnych</a> na bardziej prywatny.'
            )

            zeptomail._send(html_body=mailer.render(), subject='Resetowanie hasła 🔐', to=(email,))

        return Response({
                # dont send confirmatory data for security reasons.
            }, 200)


    def password_is_strong(self, password, username):
        common_passwords = ('password', )
        password_len = len(password)

        if not password:
            return False

        if password in common_passwords:
            return False # password too common

        if username in password:
            return False # username must not be in password

        if not (User.PASSWORD_MIN_LENGTH <= password_len <= User.PASSWORD_MAX_LENGTH):
            return False

        if not (
            # password must contain atleast 1 uppercase letter, 1 number and 1 punctuation
            contains(password, r'[A-Z]') and \
            contains(password, r'[0-9]') and \
            contains(password, rf'[{string.punctuation}]')):
            return False

        return True