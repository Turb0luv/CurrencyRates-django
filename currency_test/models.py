from django.core.validators import MinValueValidator
from django.db import models
from datetime import datetime, timedelta
from django.db.models import JSONField
from currency_test.consts import AUTOLOAD_METHOD_CHOICES


class CurrencyRateType(models.Model):
    name = models.CharField(
        unique=True,
        max_length=20,
        verbose_name='Name',
    )

    autoload_method = models.CharField(
        max_length=100,
        verbose_name='Autoload method',
        choices=AUTOLOAD_METHOD_CHOICES,
        default=AUTOLOAD_METHOD_CHOICES[0][0],
    )

    base_currency = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Base currency',
    )
    active = models.BooleanField(
        default=True,
        verbose_name='Active',
    )
    interval_value = models.PositiveIntegerField(
        verbose_name='Autoload interval value',
        validators=[
            MinValueValidator(1),
        ],
    )
    tickers = models.TextField(
        default='',
        blank=True,
        verbose_name='Tickers',
    )
    autoload_lastrun = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Autoload last run',
    )
    autoload_lastresult = JSONField(
        default=dict,
        verbose_name='Autoload last result',

    )

    class Meta:
        verbose_name = 'Currency rate type'
        verbose_name_plural = 'Currency rate types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.base_currency:
            self.base_currency = self.base_currency.upper()
        super().save(*args, **kwargs)
    #
    # @property
    # def task_next_run(self):
    #     if self.autoload_lastrun:
    #         return self.autoload_lastrun + self.autoload_interval
    #     else:
    #         return self.autoload_start + self.autoload_interval
    #
    # @property
    # def task_will_run(self):
    #     return self.task_next_run < timezone.now()


class CurrencyRate(models.Model):
    rate_type = models.ForeignKey(
        CurrencyRateType,
        on_delete=models.PROTECT,
        verbose_name='Rate type',
        related_name='currency_rates',
    )
    currency_from = models.CharField(max_length=10)
    currency_to = models.CharField(max_length=10)
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    rate_date = models.DateTimeField(auto_now_add=True)
    nominal = models.IntegerField()

    def __str__(self):
        return str(f'{self.currency_from}/{self.currency_to} ({self.rate_type})')

    def save(self, *args, **kwargs):
        self.rate_date = datetime.now()
        super().save(*args, **kwargs)
