from django.contrib import admin
from currency_test.models import CurrencyRate, CurrencyRateType
from currency_test.tasks import run_currency_rate_checker


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'currency_from',
        'currency_to',
        'rate',
        'nominal',
        'rate_date'
    ]
    list_filter = ['currency_from', 'currency_to', 'rate_type', 'rate_date']


@admin.register(CurrencyRateType)
class CurrencyRateTypeAdmin(admin.ModelAdmin):
    readonly_fields = [
        'autoload_lastrun',
        'autoload_lastresult',
    ]
    actions = ['run_method', ]

    def run_method(self, request, queryset):
        for obj in queryset:
            run_currency_rate_checker.apply_async(args=(obj.id,))
