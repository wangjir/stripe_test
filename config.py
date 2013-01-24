TEST_SECRET_KEY = "sk_test_HsBrA12QdlFUsP5TCH8OzU2O"
TEST_PUBLISH_KEY = "pk_test_B3a2qfKTXzgN2styUqeyXsni"

CVC_CHECK_POLICY = {
    'pass': True,
    'fail': False,
    'unchecked': False,
}

PAY_MONTHLY     = 'monthly'
PAY_BIMONTHLY   = 'bi-monthly'
PAY_PER_6_MONTH = '6-month'
PAY_YEARLY      = 'yearly'

SUBSCRIPTION_INTERVAL = {
    PAY_MONTHLY:    ['month', 1],
    PAY_BIMONTHLY:  ['month', 2],
    PAY_PER_6_MONTH:['month', 6],
    PAY_YEARLY:     ['year',  1],
}


