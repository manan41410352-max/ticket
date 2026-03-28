from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Ticket
from .serializers import TicketSerializer
from .services import classify_ticket


class TicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'priority', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at']


class TicketStatsView(APIView):
    def get(self, request):
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status='open').count()

        tickets_per_day = (
            Ticket.objects.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
        )
        avg_tickets_per_day = tickets_per_day.aggregate(avg=Avg('count'))['avg'] or 0

        priority_counts = Ticket.objects.values('priority').annotate(count=Count('id'))
        category_counts = Ticket.objects.values('category').annotate(count=Count('id'))

        priority_breakdown = {
            item['priority']: item['count'] for item in priority_counts
        }
        category_breakdown = {
            item['category']: item['count'] for item in category_counts
        }

        return Response(
            {
                'total_tickets': total_tickets,
                'open_tickets': open_tickets,
                'avg_tickets_per_day': round(avg_tickets_per_day, 2),
                'priority_breakdown': priority_breakdown,
                'category_breakdown': category_breakdown,
            }
        )


class HealthCheckView(APIView):
    def get(self, request):
        return Response(
            {
                'status': 'ok',
                'service': 'ticket-backend',
            }
        )


class TicketClassifyView(APIView):
    def post(self, request):
        description = request.data.get('description')
        title = request.data.get('title', '')

        if not description:
            return Response(
                {'error': 'Description is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = classify_ticket(description, title=title)
        return Response(result, status=status.HTTP_200_OK)
