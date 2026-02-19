from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    HealthCheckView,
    TicketClassifyView,
    TicketStatsView,
    TicketViewSet,
)

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='tickets')

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health'),
    path('tickets/stats/', TicketStatsView.as_view(), name='tickets-stats'),
    path('tickets/classify/', TicketClassifyView.as_view(), name='tickets-classify'),
] + router.urls
