"""
Seed aifw action types for risk-hub (idempotent).

Creates LLMProvider, LLMModel and AIActionType entries
in the aifw_* tables (iil-aifw>=0.5.0).

Run after every deploy:
    python manage.py seed_action_types
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed aifw LLM providers, models and action types for risk-hub"

    def handle(self, *args, **options):
        from aifw.models import AIActionType, LLMModel, LLMProvider

        self.stdout.write("Seeding aifw LLM configuration for risk-hub...")

        providers_data = [
            {
                "name": "anthropic",
                "display_name": "Anthropic Claude",
                "api_key_env_var": "ANTHROPIC_API_KEY",
            },
            {
                "name": "openai",
                "display_name": "OpenAI",
                "api_key_env_var": "OPENAI_API_KEY",
            },
        ]
        providers = {}
        for data in providers_data:
            p, created = LLMProvider.objects.update_or_create(name=data["name"], defaults=data)
            providers[data["name"]] = p
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {p.display_name}")

        models_data = [
            {
                "provider": "openai",
                "name": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "max_tokens": 4096,
                "input_cost_per_million": 0.15,
                "output_cost_per_million": 0.6,
                "is_default": True,
            },
            {
                "provider": "anthropic",
                "name": "claude-3-5-haiku-20241022",
                "display_name": "Claude 3.5 Haiku",
                "max_tokens": 8192,
                "input_cost_per_million": 0.25,
                "output_cost_per_million": 1.25,
                "is_default": False,
            },
        ]
        models = {}
        for data in models_data:
            provider = providers[data.pop("provider")]
            m, created = LLMModel.objects.update_or_create(
                provider=provider, name=data["name"], defaults=data
            )
            models[data["name"]] = m
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {m}")

        default_model = models["gpt-4o-mini"]
        fallback_model = models["claude-3-5-haiku-20241022"]

        actions_data = [
            (
                "hazard_analysis",
                "Hazard Analysis",
                "AI-assisted explosion hazard analysis for areas.",
                3000,
                0.2,
            ),
            (
                "substance_risk",
                "Substance Risk Assessment",
                "AI-assisted risk assessment for hazardous substances.",
                2000,
                0.2,
            ),
        ]
        for code, name, description, max_tokens, temperature in actions_data:
            a, created = AIActionType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "default_model": default_model,
                    "fallback_model": fallback_model,
                    "is_active": True,
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {a.code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n\u2705 risk-hub aifw seeded: "
                f"{LLMProvider.objects.count()} providers, "
                f"{LLMModel.objects.count()} models, "
                f"{AIActionType.objects.count()} actions"
            )
        )
