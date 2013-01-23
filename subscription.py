import config
import stripe

stripe.api_key = config.TEST_SECRET_KEY

test_card = {
    'number': '4242424242424242',
    'exp_month': '11',
    'exp_year':'2016',
    'cvc': '123',
    'name': 'plan test',
}

# create a card token
res = stripe.Token.create(card=test_card)
cc_token = res.id

# create a Customer first

user1 = stripe.Customer.create(
    description = 'Subscription User1',
    card = cc_token
)

# update user info
user1.email = "test@email.com"
user1.save()

# create a plan(Subscription)
SUBSCRIPTION_ID = "TestGold"

plan = stripe.Plan.create(
    id = SUBSCRIPTION_ID,
    amount = 1300, # $13.00 per time
    currency = 'usd',
    interval = 'month',
    name = 'Test Subscription'
)

res = user1.update_subscription(plan=plan.id)

print res

user1.cancel_subscription()



