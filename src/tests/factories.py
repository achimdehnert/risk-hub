# tests/factories.py — ADR-057 §2.5
import uuid
import factory
from django.contrib.auth.models import User

from risk.models import Assessment, Hazard


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    tenant_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Sequence(lambda n: f"Assessment {n}")
    category = Assessment.Category.GENERAL
    status = Assessment.Status.DRAFT


class HazardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hazard

    tenant_id = factory.LazyAttribute(lambda obj: obj.assessment.tenant_id)
    assessment = factory.SubFactory(AssessmentFactory)
    title = factory.Sequence(lambda n: f"Hazard {n}")
    severity = Hazard.Severity.LOW
    probability = Hazard.Probability.UNLIKELY
