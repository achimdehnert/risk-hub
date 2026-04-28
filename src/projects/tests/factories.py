"""Factory Boy factories for projects app tests."""

import uuid

import factory
from factory.django import DjangoModelFactory

from projects.models import DocumentSection, OutputDocument, Project


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = "tenancy.Organization"

    slug = factory.Sequence(lambda n: f"org-{n}")
    name = factory.Sequence(lambda n: f"Organisation {n}")


class SiteFactory(DjangoModelFactory):
    class Meta:
        model = "tenancy.Site"

    organization = factory.SubFactory(OrganizationFactory)
    tenant_id = factory.LazyAttribute(lambda o: o.organization.tenant_id)
    name = factory.Sequence(lambda n: f"Werk {n}")


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    site = factory.SubFactory(SiteFactory)
    tenant_id = factory.LazyAttribute(lambda o: o.site.tenant_id)
    name = factory.Sequence(lambda n: f"Testprojekt {n}")
    description = "Automatisch generiertes Testprojekt"
    project_number = factory.Sequence(lambda n: f"P-{n:04d}")
    client_name = "Test GmbH"


class OutputDocumentFactory(DjangoModelFactory):
    class Meta:
        model = OutputDocument

    tenant_id = factory.LazyAttribute(lambda o: o.project.tenant_id)
    project = factory.SubFactory(ProjectFactory)
    title = factory.Sequence(lambda n: f"Dokument {n}")
    kind = "custom"


class DocumentSectionFactory(DjangoModelFactory):
    class Meta:
        model = DocumentSection

    document = factory.SubFactory(OutputDocumentFactory)
    section_key = factory.Sequence(lambda n: f"section_{n}")
    title = factory.Sequence(lambda n: f"Abschnitt {n}")
    order = factory.Sequence(lambda n: n)
    content = ""
    fields_json = "[]"
    values_json = "{}"
