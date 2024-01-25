import xmltodict
from abc import ABC
from abc import abstractmethod
from datetime import datetime, timedelta
from django.utils import timezone
from requests import request
from bs4 import BeautifulSoup


class BaseMethod(ABC):
    """
    - Базовый класс для методов получения курсов валют, все методы получения
    валют должны быть унаследованы от базового и должны реализовывать все
    абстрактные методы.
    - Унаследовавшись от BaseMethod и реализовав необходимые методы, а так же
    добавив класс метода в .consts.METHODS обеспечивается реализация любого
    кастомного API метода, для получения курсов валют.
    """

    def __init__(self, base_currency, tickers):
        self.base_currency = base_currency
        self.tickers = tickers
        self.req_type = 'GET'

    @abstractmethod
    def validate_tickers(self):
        """
        Метод валидации тикеров, в случае неуспеха должен вызывать
        исключение TickerFormatException, в случае успеха возвращает None
        """
        pass

    @abstractmethod
    def prepare_data(self, response):
        """
        Метод обработки ответа от API курса, принимает возвращаемое
        функцией request значение. Возвращает словарь где ключами являются
        тикеры(currency_from), возвращенные методом, а значениями словари с
        ключами: 'rate_date', 'currency_from', 'currency_to', 'rate', 'scale':
        {
        "AUD": {
                "rate_date": "2023-06-08T21:00Z",  # type str
                "currency_from": "AUD",  # type str
                "currency_to": "RUB",  # type str
                "rate": "54.6904",  # type str
                "scale": 1,   # type int
                },
        "BYN": {
                "rate_date": "2023-06-08T21:00Z",
                "currency_from": "BYN",
                "currency_to": "RUB",
                "rate": "27.9685",
                "scale": 10,
                },
        }
        A так же возвращает дату возвращенную API курса в формате определенном
        в методе format_date.
        """
        pass

    def prepare_request(self, ticker=None):
        """
        Метод подготовки запроса, возвращает словарь, где ключами являются
        аргументы функции request - {'url': 'https://...', 'method': 'GET',
        'data': json.dumps({'token': 'a7f23b933ca'})}.
        """
        request_data = {
            'method': self.req_type,
            'url': self.url,
        }
        return request_data

    def prepare_tickers(self):
        """
        Метод подготовки тикеров, возвращает тикеры в формате
        списка ['tick1', 'tick2', 'tick3'] или пустого списка если тикеры
        не заданы, в таком случае, обрабатываются все валютные пары
        которые возвращает метод prepare_data, если другое не предусмотрено
        в методе validate_tickers.
        """
        prepared_tickers = (
            [
                ticker.strip().upper()
                for ticker in
                self.tickers.replace('/', '').rstrip(',').split(',')
            ]
            if self.tickers
            else []
        )
        # for tick in prepared_tickers:
        #     if '*' in tick:
        #         tick.replace('*', '\S')
        return prepared_tickers

    def find_key(self, res_dict, currency, option):
        res = []
        currency = currency.replace('*', '')
        for key, value in res_dict.items():
            if value['currency_' + option] == currency:
                res.append(key)
        return res

    def handle_response(self, response):
        """
        Метод который принимает ответ от API курса, вызывает обработчик данных
        в зависимости от метода, фильтрует результат при наличии тикеров,
        возвращает стандартный для всех, кастомных методов ответ в виде списка
        словарей следующего содержания:
        [
            {
                "rate_date": "2023-06-08T21:00Z",  # type str
                "currency_from": "AUD",  # type str
                "currency_to": "RUB",  # type str
                "rate": "54.6904",  # type str
                "scale": 0,   # type int
            },
            {
                "rate_date": "2023-06-08T21:00Z",
                "currency_from": "BYN",
                "currency_to": "RUB",
                "rate": "27.9685",
                "scale": -1,
            },
        ]
        """

        def _list_appender(option):
            for res in self.find_key(res_dict, currency, option):
                ans_list.append(
                    res_dict.get(
                        res,
                        self.add_currency_not_found_error(currency, date),
                    ),
                )

        ans_list = []
        res_dict, date = self.prepare_data(response)
        tickers = self.prepare_tickers()
        if not tickers:
            ans_list = list(res_dict.values())
            return ans_list
        for currency in tickers:
            if '*' in currency and currency[0] == '*':
                _list_appender('to')
            elif '*' in currency and currency[-1] == '*':
                _list_appender('from')
            else:
                ans_list.append(
                    res_dict.get(
                        currency,
                        self.add_currency_not_found_error(currency, date),
                    ),
                )
        return ans_list

    def add_currency_not_found_error(self, currency, date):
        """
        Метод заглушка используемый в случаях когда метод API курса, не
        вернул один из тикеров указанный в определенных в методе
        prepare_tickers.
        """
        return {
            'rate_date': date,
            'currency_from': currency,
            'currency_to': self.base_currency or currency,
            'rate': '0',
            'scale': 0,
            'error': {
                'code': '404',
                'description': 'Currency not found',
            },
        }

    def make_request(self):
        """
        Метод который определяет на основании атрибута request_type cпособ
        получения данных (один/несколько запросов), возвращает ответ в виде
        списка словарей следующего содержания:
        [
            {
                "rate_date": "2023-06-08T21:00Z",  # type str
                "currency_from": "AUD",  # type str
                "currency_to": "RUB",  # type str
                "rate": "54.6904",  # type str
                "scale": 0,   # type int
            },
            {
                "rate_date": "2023-06-08T21:00Z",
                "currency_from": "BYN",
                "currency_to": "RUB",
                "rate": "27.9685",
                "scale": -1,
            },
        ]
        """
        raw_response = request(**self.prepare_request())
        raw_response.raise_for_status()
        response = self.handle_response(raw_response)

        return response


class CBRFMethod(BaseMethod):

    def __init__(self, base_currency, tickers):
        super().__init__(base_currency, tickers)
        self.base_currency = 'RUB'
        self.tickers = tickers
        self.req_type = 'GET'
        self.url = 'https://www.cbr.ru/scripts/XML_daily.asp'

    def validate_tickers(self):
        for ticker in self.prepare_tickers():
            if len(ticker) != 3:
                raise Exception

    def prepare_data(self, response):
        raw_dict = xmltodict.parse(response.content)
        res_dict = {}
        date = raw_dict.get('ValCurs').get('@Date')

        for val_dict in raw_dict.get('ValCurs', {}).get('Valute', {}):
            rate_dict = {
                'rate_date': date,
                'currency_from': val_dict.get('CharCode'),
                'currency_to': self.base_currency,
                'rate': val_dict.get('Value').replace(',', '.'),
                'nominal': val_dict.get('Nominal', ''),
            }

            res_dict.update({val_dict.get('CharCode'): rate_dict})
        return res_dict, date


class ECBMethod(BaseMethod):

    def __init__(self, base_currency, tickers):
        super().__init__(base_currency, tickers)
        self.base_currency = 'EUR'
        self.tickers = tickers
        self.req_type = 'GET'
        self.url = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'

    def validate_tickers(self):
        for ticker in self.prepare_tickers():
            if len(ticker) != 3:
                raise Exception

    def prepare_data(self, response):
        raw_dict = xmltodict.parse(response.content).get('gesmes:Envelope').get(
            'Cube').get('Cube')
        res_dict = {}
        date = datetime.strptime(raw_dict.get('@time'), '%Y-%m-%d').strftime(
            '%d.%m.%Y')

        for val_dict in raw_dict.get('Cube', {}):
            rate_dict = {
                'rate_date': date,
                'currency_from': self.base_currency,
                'currency_to': val_dict.get('@currency'),
                'rate': val_dict.get('@rate'),
                'nominal': 1,
            }

            res_dict.update({val_dict.get('@currency'): rate_dict})
        return res_dict, date


class BinanceMethod(BaseMethod):

    def __init__(self, base_currency, tickers):
        super().__init__(base_currency, tickers)
        self.tickers = tickers
        self.req_type = 'GET'
        self.url = 'https://api.binance.com/api/v3/exchangeInfo'
        self.rate_url = 'https://api.binance.com/api/v3/avgPrice?symbol={}'

    def validate_tickers(self):
        for ticker in self.prepare_tickers():
            if len(ticker) < 2:
                raise Exception

    def request_rate(self, ticker):
        response = request(
            self.req_type,
            self.rate_url.format(ticker)
        )
        return response.json().get('price') or 0

    def prepare_data(self, response):
        raw_dict = response.json().get('symbols') or {}
        res_dict = {}
        date = datetime.strptime(str(timezone.now().date()),
                                 '%Y-%m-%d').strftime('%d.%m.%Y')

        def _make_dct(base, quote):
            rate_dict = {
                'rate_date': date,
                'currency_from': base,
                'currency_to': quote,
                'rate': self.request_rate(base + quote),
                'nominal': 1,
            }
            return res_dict.update({(base + quote): rate_dict})

        for tick in self.prepare_tickers():
            if '*' in tick:
                if tick[0] == '*':
                    tick = tick.replace('*', '')
                    for coin in raw_dict:
                        if tick == coin['quoteAsset']:
                            _make_dct(coin['baseAsset'], coin['quoteAsset'])
                elif tick[-1] == '*':
                    tick = tick.replace('*', '')
                    for coin in raw_dict:
                        if tick == coin['baseAsset']:
                            _make_dct(coin['baseAsset'], coin['quoteAsset'])
            else:
                for coin in raw_dict:
                    if tick == coin['symbol']:
                        _make_dct(coin['baseAsset'], coin['quoteAsset'])
                        break

        return res_dict, date


class GarantexMethod(BaseMethod):

    def __init__(self, base_currency, tickers):
        super().__init__(base_currency, tickers)
        self.tickers = tickers
        self.req_type = 'GET'
        self.url = 'https://garantex.org/api/v2/markets'
        self.curr_url = 'https://garantex.org/api/v2/trades?market={}'

    def validate_tickers(self):
        for ticker in self.prepare_tickers():
            if len(ticker) < 2:
                raise Exception

    def request_rate(self, ticker):
        response = request(
            self.req_type,
            self.curr_url.format(ticker)
        )
        return response.json()[0].get('price') or 0

    def prepare_data(self, response):
        raw_dict = response.json()
        res_dict = {}
        date = datetime.strptime(str(timezone.now().date()),
                                 '%Y-%m-%d').strftime('%d.%m.%Y')

        def _make_dct(base, quote):
            rate_dict = {
                'rate_date': date,
                'currency_from': base,
                'currency_to': quote,
                'rate': self.request_rate((base + quote).lower()),
                'nominal': 1,
            }
            return res_dict.update({(base + quote): rate_dict})

        for tick in self.prepare_tickers():
            tick = tick.lower()
            if '*' in tick:
                if tick[0] == '*':
                    tick = tick.replace('*', '')
                    for coin in raw_dict:
                        if tick == coin['bid_unit']:
                            _make_dct(coin['ask_unit'].upper(),
                                      coin['bid_unit'].upper())
                elif tick[-1] == '*':
                    tick = tick.replace('*', '')
                    for coin in raw_dict:
                        if tick == coin['ask_unit']:
                            _make_dct(coin['ask_unit'].upper(),
                                      coin['bid_unit'].upper())
            else:
                for coin in raw_dict:
                    if tick == coin['id']:
                        _make_dct(coin['ask_unit'].upper(),
                                  coin['bid_unit'].upper())
                        break

        return res_dict, date


class XEMethod(BaseMethod):

    def __init__(self, base_currency, tickers):
        super().__init__(base_currency, tickers)
        self.tickers = tickers
        self.req_type = 'GET'
        self.url = 'https://www.xe.com/currencytables/?from={}&date={}'

    def validate_tickers(self):
        for ticker in self.prepare_tickers():
            if len(ticker) < 3:
                raise Exception

    def prepare_request(self, ticker=None):
        current_time = timezone.now()
        if current_time.hour > 4:
            date = current_time - timedelta(days=1)
        else:
            date = current_time - timedelta(days=2)
        request_data = {}
        for tick in self.prepare_tickers():
            if len(tick.replace('*', '')) == 3:
                request_data.update({tick: {
                    'method': self.req_type,
                    'url': self.url.format(tick.replace('*', ''),
                                           date.strftime('%Y-%m-%d')),
                    'ticker': tick.replace('*', '')
                }})
            else:
                request_data.update({tick: {
                    'method': self.req_type,
                    'url': self.url.format(tick[:3],
                                           date.strftime('%Y-%m-%d')),
                    'ticker': tick.replace('*', '')
                }})
        return request_data

    def make_request(self):
        pre_response = {}
        for req in self.prepare_request().values():
            raw_response = request(req['method'], req['url'])
            raw_response.raise_for_status()
            pre_response.update({req['ticker']: raw_response})
        response = self.handle_response(pre_response)

        return response

    def prepare_data(self, response):
        res_dict = {}
        date = datetime.strptime(str(timezone.now().date()),
                                 '%Y-%m-%d').strftime('%d.%m.%Y')

        for ticker, response in response.items():
            soup = list(BeautifulSoup(response.text, "lxml").
                        tbody.stripped_strings)
            for i in range(len(soup[::4])):
                res_dict.update(
                    {str(ticker[:3] + soup[::4][i]):
                         {'rate_date': date,
                          'currency_from': ticker[:3],
                          'currency_to': str(soup[::4][i]),
                          'rate': str(soup[2::4][i]),
                          'nominal': 1}})
                res_dict.update(
                    {str(soup[::4][i] + ticker[:3]):
                         {'rate_date': date,
                          'currency_from': str(soup[::4][i]),
                          'currency_to': ticker[:3],
                          'rate': str(soup[3::4][i]),
                          'nominal': 1}})

        return res_dict, date
