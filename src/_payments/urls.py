from rest_framework.routers import SimpleRouter

from .views import (
    CheckoutViewSet,
    WebhookViewSet,
    StatisticsViewSet,
    PaymentHistoryViewSet,
    CreateCustomTransactionViewSet,
)

app_name = 'payments'

payments_router = SimpleRouter()

payments_router.register(r'checkout-endpoint', CheckoutViewSet, basename='checkout')
payments_router.register(r'webhook-endpoint', WebhookViewSet, basename='webhook')
payments_router.register(r'statistics', StatisticsViewSet)
payments_router.register(r'payment_history', PaymentHistoryViewSet)
payments_router.register(r'create_custom_transaction', CreateCustomTransactionViewSet)
