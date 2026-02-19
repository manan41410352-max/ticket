import os
from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Ticket
from .services import classify_ticket


class TicketListFilteringTests(APITestCase):
    def setUp(self):
        self.list_url = reverse('tickets-list')

        self.ticket_a = Ticket.objects.create(
            title='Payment gateway failure',
            description='Payment attempt fails for multiple cards',
            category='billing',
            priority='high',
            status='open',
        )
        self.ticket_b = Ticket.objects.create(
            title='Server outage',
            description='Production server becomes unreachable',
            category='technical',
            priority='high',
            status='open',
        )
        self.ticket_c = Ticket.objects.create(
            title='Profile update issue',
            description='Account details are not saving',
            category='account',
            priority='low',
            status='resolved',
        )

        base_time = timezone.now()
        Ticket.objects.filter(pk=self.ticket_a.pk).update(
            created_at=base_time - timedelta(hours=3)
        )
        Ticket.objects.filter(pk=self.ticket_b.pk).update(
            created_at=base_time - timedelta(hours=2)
        )
        Ticket.objects.filter(pk=self.ticket_c.pk).update(
            created_at=base_time - timedelta(hours=1)
        )

    @staticmethod
    def _items(response):
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data

    def test_filter_by_category(self):
        response = self.client.get(self.list_url, {'category': 'billing'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Payment gateway failure')

    def test_filter_by_priority(self):
        response = self.client.get(self.list_url, {'priority': 'high'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        self.assertEqual(len(items), 2)
        titles = {item['title'] for item in items}
        self.assertSetEqual(titles, {'Payment gateway failure', 'Server outage'})

    def test_filter_by_status(self):
        response = self.client.get(self.list_url, {'status': 'open'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        self.assertEqual(len(items), 2)
        statuses = {item['status'] for item in items}
        self.assertSetEqual(statuses, {'open'})

    def test_search_title_and_description(self):
        response = self.client.get(self.list_url, {'search': 'payment'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Payment gateway failure')

    def test_combined_filters_and_search(self):
        response = self.client.get(
            self.list_url,
            {'category': 'technical', 'priority': 'high', 'search': 'server'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Server outage')

    def test_ordering_by_created_at(self):
        response = self.client.get(self.list_url, {'ordering': 'created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._items(response)
        titles = [item['title'] for item in items]
        self.assertEqual(
            titles,
            ['Payment gateway failure', 'Server outage', 'Profile update issue'],
        )


class TicketStatsTests(APITestCase):
    def setUp(self):
        self.stats_url = reverse('tickets-stats')

        ticket_1 = Ticket.objects.create(
            title='Billing charge mismatch',
            description='Invoice shows incorrect amount',
            category='billing',
            priority='high',
            status='open',
        )
        ticket_2 = Ticket.objects.create(
            title='API timeout issue',
            description='Requests to API are timing out',
            category='technical',
            priority='medium',
            status='open',
        )
        ticket_3 = Ticket.objects.create(
            title='Service crash',
            description='Backend crashes under load',
            category='technical',
            priority='high',
            status='closed',
        )
        ticket_4 = Ticket.objects.create(
            title='Profile update blocked',
            description='Cannot save account settings',
            category='account',
            priority='low',
            status='open',
        )
        ticket_5 = Ticket.objects.create(
            title='General request',
            description='Feature request from user',
            category='general',
            priority='critical',
            status='resolved',
        )

        base_time = timezone.now()
        Ticket.objects.filter(pk=ticket_1.pk).update(
            created_at=base_time - timedelta(days=2)
        )
        Ticket.objects.filter(pk=ticket_2.pk).update(
            created_at=base_time - timedelta(days=2)
        )
        Ticket.objects.filter(pk=ticket_3.pk).update(
            created_at=base_time - timedelta(days=1)
        )
        Ticket.objects.filter(pk=ticket_4.pk).update(
            created_at=base_time - timedelta(days=1)
        )
        Ticket.objects.filter(pk=ticket_5.pk).update(
            created_at=base_time - timedelta(days=1)
        )

    def test_ticket_stats_response(self):
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tickets'], 5)
        self.assertEqual(response.data['open_tickets'], 3)
        self.assertEqual(response.data['avg_tickets_per_day'], 2.5)
        self.assertDictEqual(
            response.data['priority_breakdown'],
            {
                'low': 1,
                'medium': 1,
                'high': 2,
                'critical': 1,
            },
        )
        self.assertDictEqual(
            response.data['category_breakdown'],
            {
                'billing': 1,
                'technical': 2,
                'account': 1,
                'general': 1,
            },
        )


class TicketClassifyViewTests(APITestCase):
    def setUp(self):
        self.classify_url = reverse('tickets-classify')

    def test_description_is_required(self):
        response = self.client.post(self.classify_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Description is required'})

    @patch('tickets.views.classify_ticket')
    def test_returns_suggested_classification(self, mock_classify):
        mock_classify.return_value = {
            'suggested_category': 'billing',
            'suggested_priority': 'high',
        }

        response = self.client.post(
            self.classify_url,
            {
                'description': (
                    'My credit card was charged twice and I need a refund now.'
                )
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {'suggested_category': 'billing', 'suggested_priority': 'high'},
        )

    @patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False)
    def test_missing_api_key_returns_null_suggestions(self):
        response = self.client.post(
            self.classify_url,
            {'description': 'Payment failed and I need urgent help.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {'suggested_category': None, 'suggested_priority': None},
        )


class HealthCheckViewTests(APITestCase):
    def test_health_check(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {'status': 'ok', 'service': 'ticket-backend'},
        )


class TicketClassificationServiceTests(SimpleTestCase):
    @patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False)
    def test_classify_ticket_without_api_key_returns_nulls(self):
        result = classify_ticket('Any description')
        self.assertEqual(
            result,
            {'suggested_category': None, 'suggested_priority': None},
        )
