from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from .views import (
     CreateSessionView,
     RegisterView,VoiceChatView,
     DeleteSessionView,FarmerLoginView,
     ProfileView, SaveChatMessageView,DisplaySessionView, 
     ChatSessionMessageView,ChatAgentRespondView,
     WeatherApiView,
     CountyViewSet,
     ConstituencyViewSet,
     WardViewSet
     )

from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'counties', CountyViewSet, basename='county')
router.register(r'constituencies', ConstituencyViewSet, basename='constituency')
router.register(r'wards', WardViewSet, basename='ward')


urlpatterns = [
    path('register/',RegisterView.as_view(), name='register'),
    path('login/',FarmerLoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(),name='profile'),
    path('messages/', SaveChatMessageView.as_view(), name='save-chat-message'),
    path('sessions/', CreateSessionView.as_view(), name='create-session'),
    path('sessions/<uuid:session_id>/messages/',ChatSessionMessageView.as_view(), name='session_messages'),
    path('chat/respond/', ChatAgentRespondView.as_view(), name='chat_respond'),
    path('voice/',VoiceChatView.as_view(),name="voice-chat"),
    path('display/session/', DisplaySessionView.as_view(), name="display-session"),
    path('display/session/<uuid:session_id>', DeleteSessionView.as_view(), name='session-delete'),
    path('weather/', WeatherApiView.as_view(), name='weather'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('',include(router.urls))

] 