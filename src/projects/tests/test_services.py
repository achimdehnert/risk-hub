"""Tests for projects.services (ADR-041 service layer)."""

import pytest

from projects import services
from projects.models import DocumentSection, OutputDocument
from projects.tests.factories import (
    DocumentSectionFactory,
    ProjectFactory,
)


@pytest.mark.django_db
def test_should_create_project_via_service(fixture_tenant, fixture_user):
    from tenancy.models import Site

    site = Site.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        organization=fixture_tenant,
        name="Testwerk",
    )
    cmd = services.CreateProjectCmd(
        tenant_id=str(fixture_tenant.tenant_id),
        site_id=str(site.pk),
        name="Neues Testprojekt",
        description="Beschreibung",
        created_by_id=fixture_user.pk,
    )
    project = services.create_project(cmd)

    assert project.pk is not None
    assert project.name == "Neues Testprojekt"
    assert str(project.tenant_id) == str(fixture_tenant.tenant_id)


@pytest.mark.django_db
def test_should_create_project_with_selected_modules(fixture_tenant, fixture_user):
    from tenancy.models import Site

    site = Site.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        organization=fixture_tenant,
        name="Werk B",
    )
    cmd = services.CreateProjectCmd(
        tenant_id=str(fixture_tenant.tenant_id),
        site_id=str(site.pk),
        name="Projekt mit Modulen",
        selected_modules=["risk", "dsb"],
        created_by_id=fixture_user.pk,
    )
    project = services.create_project(cmd)

    module_codes = list(project.modules.values_list("module", flat=True))
    assert "risk" in module_codes
    assert "dsb" in module_codes


@pytest.mark.django_db
def test_should_save_section_content():
    section = DocumentSectionFactory(
        content="",
        fields_json='[]',
    )
    services.save_section_values(section, {"content": "Neuer Inhalt"})
    section.refresh_from_db()

    assert section.content == "Neuer Inhalt"


@pytest.mark.django_db
def test_should_delete_section_via_service():
    section = DocumentSectionFactory()
    section_pk = section.pk

    services.delete_document_section(section)

    assert not DocumentSection.objects.filter(pk=section_pk).exists()


@pytest.mark.django_db
def test_should_get_projects_for_tenant(fixture_tenant):
    ProjectFactory.create_batch(3, tenant_id=fixture_tenant.tenant_id)
    other_tenant_id = __import__("uuid").uuid4()
    ProjectFactory(tenant_id=other_tenant_id)

    projects = services.get_projects(fixture_tenant.tenant_id)

    assert projects.count() == 3
    assert all(str(p.tenant_id) == str(fixture_tenant.tenant_id) for p in projects)


@pytest.mark.django_db
def test_should_create_output_document_without_template(fixture_tenant):
    project = ProjectFactory(tenant_id=fixture_tenant.tenant_id)
    doc = OutputDocument.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        project=project,
        title="Testdokument",
        kind="custom",
    )

    assert doc.pk is not None
    assert doc.title == "Testdokument"
    assert str(doc.tenant_id) == str(fixture_tenant.tenant_id)
