from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .serializers import UploadSerializer, LogDBEntrySerializer, BigLogSerializer
from .models import LogDBEntry, BigLog


# ViewSets define the view behavior.
class UploadViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadSerializer
    permission_classes = [IsAuthenticated,]  # Only authenticated users can access
    

    def create(self, request):
        file_uploaded = request.FILES.get('file_uploaded', None)
        content_type = file_uploaded
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': 'codebase was not specified'}, status=status.HTTP_400_BAD_REQUEST)       
        
        if file_uploaded:
            self.handle_uploaded_file(file_uploaded, serializer)

        response = "POST API and you have uploaded a {} file".format(content_type)
        return Response(response)
    
    def handle_uploaded_file(self, file, serializer):
        pass


class LogDBEntryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LogDBEntrySerializer
    permission_classes = [IsAuthenticated, ]
    queryset = LogDBEntry.objects.all()
    
    @action(methods=['get'], detail=False)
    def only_this_user(self, request):
        user = self.request.user 
        logs = self.queryset.filter(user=user)

        return Response(self.serializer_class(logs, many=True).data)


class BigLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = BigLogSerializer
    permission_classes = [IsAuthenticated, ]
    queryset = BigLog.objects.all()
    
    @action(methods=['get'], detail=False)
    def only_this_user(self, request):
        user = self.request.user 
        logs = self.queryset.filter(user=user)

        return Response(self.serializer_class(logs, many=True).data)
