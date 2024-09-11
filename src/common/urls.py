from rest_framework.routers import SimpleRouter

from .views import LogDBEntryViewSet, BigLogViewSet

app_name = 'common'

common_router = SimpleRouter()
common_router.register(r'logdbentries', LogDBEntryViewSet)
common_router.register(r'biglogentries', BigLogViewSet)
