from currency_test.methods import (CBRFMethod, ECBMethod, BinanceMethod,
                                   GarantexMethod, XEMethod)

AUTOLOAD_METHOD_CHOICES = [
    ('empty_method', '----------'),
    ('cbrf_method', 'CBRF rate loader'),
    ('ecb_method', 'ECB rate loader'),
    ('binance_method', 'Binance rate loader'),
    ('garantex_method', 'Garantex rate loader'),
    ('xe_method', 'XE rate loader'),
]

METHODS = {
    'cbrf_method': CBRFMethod,
    'ecb_method': ECBMethod,
    'binance_method': BinanceMethod,
    'garantex_method': GarantexMethod,
    'xe_method': XEMethod
}
