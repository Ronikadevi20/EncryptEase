from django.apps import AppConfig
import warnings


class ApplicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications'

    def ready(self):
        warnings.filterwarnings(
            "ignore",
            message="Model 'applications.followupdraft' was already registered",
            category=RuntimeWarning
        )