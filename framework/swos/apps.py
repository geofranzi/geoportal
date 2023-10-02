from django.apps import AppConfig


class SwosConfig(AppConfig):
    name = 'swos'

    def ready(self):
        import swos.signals
        import swos.search_es
