# src/explosionsschutz/models/cybersecurity.py
"""
Cybersecurity-Assessment für Explosionsschutzkonzepte.

Ab EU-MVO 2027 und NIS2 verpflichtend bei kritischen Anlagen.
OneToOne auf ExplosionConcept — optional, wird bei Bedarf angelegt.

ADR-044 Phase 4A.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class CybersecurityAssessment(models.Model):
    """
    Cybersecurity-Bewertung als Ergänzung zum Ex-Schutzkonzept.

    Referenz-Frameworks: IEC 62443, NIS2, EU-MVO 2023/1230 (ab 2027 verpflichtend).
    Optional — wird nur für Anlagen mit OT/IT-Integration oder Fernzugriff angelegt.
    """

    class AssessmentFramework(models.TextChoices):
        IEC_62443 = "IEC_62443", "IEC 62443 (Industrial Automation and Control Systems)"
        NIS2 = "NIS2", "NIS2-Richtlinie (EU 2022/2555)"
        MVO_2027 = "MVO_2027", "EU-Maschinenverordnung 2023/1230 (ab Jan 2027)"
        CUSTOM = "CUSTOM", "Anlagen-spezifisch"

    class AccessControlType(models.TextChoices):
        STAND_ALONE = "STAND_ALONE", "Stand-Alone (keine Netzwerkanbindung)"
        INTEGRATED = "INTEGRATED", "In IT-Infrastruktur integriert"
        REMOTE = "REMOTE", "Fernzugriff möglich"

    concept = models.OneToOneField(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="cybersecurity_assessment",
    )

    assessment_framework = models.CharField(
        max_length=30,
        choices=AssessmentFramework.choices,
        blank=True,
    )
    ot_zone_classification = models.CharField(
        max_length=30,
        blank=True,
        help_text="OT-Sicherheitszone nach IEC 62443, z.B. 'Zone 3 (Control Network)'",
    )
    it_network_isolated = models.BooleanField(
        default=True,
        help_text="OT-Netzwerk ist physisch oder logisch vom IT-Netzwerk getrennt",
    )
    access_control_type = models.CharField(
        max_length=30,
        choices=AccessControlType.choices,
        default=AccessControlType.STAND_ALONE,
    )
    hmi_authentication_required = models.BooleanField(
        default=False,
        help_text="HMI/Bedienpanel erfordert Authentifizierung",
    )
    security_levels_differentiated = models.BooleanField(
        default=False,
        help_text="Unterschiedliche Security Levels (SL) nach IEC 62443 definiert",
    )
    last_security_audit_date = models.DateField(
        null=True,
        blank=True,
    )
    threat_analysis_narrative = models.TextField(
        help_text="Bedrohungsanalyse: identifizierte Angriffsvektoren und Risiken",
    )
    mitigation_measures_narrative = models.TextField(
        help_text="Gegenmaßnahmen: technische und organisatorische Sicherheitsmaßnahmen",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_cybersecurity_assessment"
        verbose_name = "Cybersecurity-Assessment"
        verbose_name_plural = "Cybersecurity-Assessments"

    def __str__(self) -> str:
        concept_title = self.concept.title if self.concept_id else "?"
        return f"Cybersecurity-Assessment: {concept_title}"
