from django.apps import AppConfig
class IoTGatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.iot_gateway'
    label = 'tap_iot'
    verbose_name = 'IoT Device Gateway'
