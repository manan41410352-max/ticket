from django.db import models


class CategoryChoices(models.TextChoices):
    BILLING = 'billing', 'Billing'
    TECHNICAL = 'technical', 'Technical'
    ACCOUNT = 'account', 'Account'
    GENERAL = 'general', 'General'


class PriorityChoices(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class StatusChoices(models.TextChoices):
    OPEN = 'open', 'Open'
    IN_PROGRESS = 'in_progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'
    CLOSED = 'closed', 'Closed'


class Ticket(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CategoryChoices.choices)
    priority = models.CharField(max_length=20, choices=PriorityChoices.choices)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=CategoryChoices.values),
                name='ticket_category_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=PriorityChoices.values),
                name='ticket_priority_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=StatusChoices.values),
                name='ticket_status_valid',
            ),
        ]

    def __str__(self) -> str:
        return self.title
