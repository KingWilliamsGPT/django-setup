from django.urls import path, re_path, include, reverse_lazy

from . import views


urlpatterns = [
    path('stripe/', views.Webhooks.stripe_webhook),
] 