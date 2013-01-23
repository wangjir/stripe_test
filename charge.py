import config
import stripe

stripe.api_key = config.TEST_SECRET_KEY

test_card = {
    'number': '4242424242424242',
    'exp_month': '11',
    'exp_year':'2016',
    'cvc': '123',
    'name': 'abc jir',
}

response = stripe.Charge.create(
    amount = 560,
    currency = 'usd',
    card = test_card,
    description = 'Charge for test'
)

print response
