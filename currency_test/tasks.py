import pytz
from base.celery import app
from copy import deepcopy
from decimal import Decimal

from celery.app.task import Task
from datetime import datetime
from django.utils import timezone
from requests.exceptions import RequestException

from currency_test.consts import METHODS
from currency_test.models import CurrencyRate
from currency_test.models import CurrencyRateType


@app.task(base=Task)
def run_currency_rate_checker(rate_type_id):
    """
    Таск run_currency_rate_checker запускается в случае необходимости
    исключительно планировщиком - currency_rates_scheduler. Инстаницирует
    необходимый класс в зависимости от метода, выполняет все валидации,
    отправляет запрос, обрабатывает ответ, записывает данные в БД.
    """

    task_time = timezone.now()

    def create_rate(rate_list):
        for rate in rate_list:
            if not rate.get('error'):
                new_rate = deepcopy(rate)
                valid_from = pytz.utc.localize(datetime.strptime(
                    new_rate.get('rate_date'), '%d.%m.%Y'
                ))
                new_rate['rate_date'] = valid_from
                new_rate['rate_type_id'] = rate_type_id
                new_rate['rate'] = Decimal(new_rate.get('rate') or '0')
                rate_exists = CurrencyRate.objects.filter(
                    rate_type_id=rate_type_id,
                    currency_from=new_rate.get('currency_from'),
                    currency_to=new_rate.get('currency_to'),
                    rate_date=new_rate.get('rate_date'),
                    rate=new_rate.get('rate'),
                    nominal=new_rate.get('nominal'),
                ).first()
                if not rate_exists:
                    curr_rate = CurrencyRate(**new_rate)
                    curr_rate.save()
                else:
                    rate.update(
                        {
                            'error': {
                                'code': '429 ',
                                'description': 'Duplicate',
                            },
                        },
                    )
        return rate_list

    rate_type = CurrencyRateType.objects.filter(id=rate_type_id).first()

    if rate_type:
        rate_type.autoload_lastrun = task_time
        try:
            method = METHODS.get(rate_type.autoload_method)(
                rate_type.base_currency,
                rate_type.tickers,
            )
            method.validate_tickers()
            response = method.make_request()
        except RequestException as exc:
            if hasattr(exc, 'response'):
                response = [{exc.response.status_code: exc.response.reason}]
            else:
                response = [{500: 'ConnectionError'}]
        else:
            response = create_rate(deepcopy(response))

        rate_type.autoload_lastresult = response
        rate_type.save()


