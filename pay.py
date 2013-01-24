#
# Real money transaction interface using stripe API
#

import stripe
import config

# stripe.api_key = config.STRIPE_KEY
stripe.api_key = config.TEST_SECRET_KEY

#
# _call_
# 
# stripe call - Handle all exception 
#
def _call_(method, **params):

    try:
        if method == 'charge':
            resp = stripe.Charge.create(**params)
        elif method == 'retrieve':
            resp = stripe.Charge.retrieve(**params)
        elif method == 'refund':
            ch = params.pop('charge_instance')
            resp = ch.refund(**params)
        elif method == 'customer':
            resp = stripe.Customer.create(**params)
        elif method == 'plan':
            resp = stripe.Plan.create(**params)
        elif method == 'subscription':
            cu = params.pop('customer_instance')
            resp = cu.update_subscription(**params)
        elif method == 'cancel_subscription':
            cu = stripe.Customer.retrieve(**params)
            resp = cu.cancel_subscription()
        else:
            return False, "Unknown command."

    except stripe.CardError, e:
        # Card Errors are:
        #    error code(str)   error message
        #   incorrect_number   The card number is incorrect
        #   invalid_number     The card number is not a valid credit card number
        #   invalid_expiry_month    The card's expiration month is invalid
        #   invalid_expiry_year The card's expiration year is invalid
        #   invalid_cvc The card's security code is invalid
        #   expired_card       The card has expired
        #   incorrect_cvc      The card's security code is incorrect
        #   card_declined      The card was declined.
        #   missing            There is no card on a customer that is being charged.
        #   processing_error   An error occurred while processing the card.
        return False, e.message     

    except stripe.InvalidRequestError, e:
        # "Can not find the transaction or invalid request."
        return False, e.message
    
    except stripe.AuthenticationError, e:
        # every BAD, some one change the API key
        raise Exception("DANGER! The stripe API key is changed!")
        
    except stripe.APIConnectionError, e:
        # network problem
        return False, e.message

    except stripe.StripeError, e:
        # generic error
        # need LOG
        return False, e.message

    return True, resp

#
# We wish to return a very simple result
#   - if success.  Return True and Stripe response
#   - if error.    Return False and error message
# 
# If the error is happened on stripe side, we store the response to db.
# We could query the db get detail information when we need.
#

CARD_PARM_REQUIRED = set([
    'number',
    'exp_month',
    'exp_year',
    'cvc'
])

CARD_PARM_OPTIONAL = set([
    'name',
    'address_line1',
    'address_line2',
    'address_zip',
    'address_state',
    'address_country'
])

def _check_card(cc):
    keys = set(cc.keys())
    if len(keys - CARD_PARM_REQUIRED - CARD_PARM_OPTIONAL) > 0:
        return "Unknown Card fields"
    if len(CARD_PARM_REQUIRED - keys) > 0:
        return "Missing " + list(CARD_PARM_REQUIRED - keys)[0]
    return ""


#
# charge
#
# Charge a credit card immediately.
# The CVC check is required. For now
#   - pass 
#   - fail       Refund
#   - unchecked  Refund
#
# Input
#   - amount      - USD in cent
#   - cc          - credit card dict
#   - description 
#     must given. This is the only value that we could find the transaction
#     in our database by a given stripe record, without searching our whole
#     database. It should be a transaction ID or plus user ID in our db
#     which could locate the row every quick.
#
#     That means, we should create a record in our db, before calling this 
#     function.
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   charge_dict - stripe response in dict 
#   charge_id - stripe.Charge response id 
#
#
def charge(amount, cc, description):
    emsg = _check_card(cc)
    if emsg:
        return {'rv': False, 'error_msg': emsg}

    rv, resp = _call_('charge',
        amount = amount,
        currency = 'usd',
        card = cc,
        description = description
    )
    if not rv:
        return {'rv': False, 'error_msg': resp}
    else:
        ch = resp
        
    charge_dict = resp.to_dict()
    if charge_dict.get('paid'):
        cvc_check = charge_dict.get('card').get('cvc_check')
        if config.CVC_CHECK_POLICY.get(cvc_check, False):
            return {
                'rv': True, 
                'error_msg': '', 
                'charge_dict': charge_dict, 
                'charge_id': charge_dict.get('id')
            }
        else:
            # refund 
            try:
                refund_resp = ch.refund()
            except:
                return {
                    'rv': False, 
                    'error_msg': 'DANGER! Money is charged, but cvc check is unpassed. And the refund is failed.', 
                    'charge_dict': charge_dict, 
                    'charge_id': charge_dict.get('id')
                }

            return {
                'rv': False, 
                'error_msg': 'CVC check is failed. Money is charged and refunded.', 
                'charge_dict': refund_resp.to_dict(), 
                'charge_id': charge_dict.get('id')
            }
    else:
        return {
            'rv': False, 
            'error_msg': charge_dict.get('failure_message'),
            'charge_dict': charge_dict,
            'charge_id': charge_dict.get('id')
        }


#
# refund
#
# Refund a transaction, default is whole amount
# 
# Input
#   - charge_id   - stripe.Charge response id 
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   charge_dict - stripe response a stripe.Charge instance for the refund 
#                 we change it to a dict
#
def refund(charge_id, amount=0):
    rv, resp = _call_('retrieve', id=charge_id)
    if not rv:
        return {'rv': False, 'error_msg': resp}

    # resp is a stripe.Charge instance
    ch = resp
    if amount>0:
        rv, resp = _call_('refund', charge_instance=ch, amount=amount)
    else:
        rv, resp = _call_('refund', charge_instance=ch)

    if not rv:
        return {'rv': False, 'error_msg': resp}
    else:
        return {'rv': True,  'error_msg': '', 'charge_dict': resp.to_dict()}


#
# retrieve
#
# Retrieve a Charged transaction. (Query it)
# 
# Input
#   - charge_id   - stripe.Charge response id 
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   charge_dict - stripe response a stripe.Charge instance for the retrieve 
#                 we change it to a dict
#
def retrieve(charge_id):
    rv, resp = _call_('retrieve', id=charge_id)
    if not rv:
        return {'rv': False, 'error_msg': resp}
    else:
        return {'rv': True,  'error_msg': '', 'charge_dict': resp.to_dict()}


#
# plan
#
# Make a subscription plan, and then use this plan to charge a user cyclically.
# By default, the plan is monthly
#
# Input
#   - subscription_id MUST be a unqiue value.
#      otherwise will get "Plan already exists error".
#   - interval_type
#      4 type of interval:
#      PAY_MONTHLY, PAY_BIMONTHLY, PAY_PER_6_MONTH, PAY_YEARLY
#      see config.SUBSCRIPTION_INTERVAL for more detail
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   plan_dict - stripe respond a stripe.Plan instance. we change it to a dict
#
def plan(subscription_id, amount, subscription_name, interval_type=''):
    interval, interval_count = config.SUBSCRIPTION_INTERVAL.get(
        interval_type, 
        config.SUBSCRIPTION_INTERVAL.get(config.PAY_MONTHLY)
    )

    rv, resp = _call_('plan',
        id = subscription_id,
        amount = amount,
        currency = 'usd',
        interval = interval,
        interval_count = interval_count,
        name = subscription_name
    )
    if not rv:
        return {'rv': False, 'error_msg': resp}

    return {
        'rv': True,  
        'error_msg': '', 
        'plan_dict': resp.to_dict()
    }


#
# subscription
#
# Make a subscription for a credit card based on a plan (subscription_id)
#
# Relationship between Plan, Customer, Subscription
#   A subscription is like: WHO pays WHAT for AMOUNT per INTERVAL:
#   - Plan - contains AMOUNT and INTERVAL
#       Plan.subscription_id - WHAT
#   - Customer - WHO
#       Customer.active_card - the credit card
#   - Subscription 
#       A relationship between a Customer and a Plan
#       One Customer can only have one Plan,
#       one Plan can be used by multiple Customers
#     C1 ---> P1
#     C2 ---> P1
#     C3 ---> P1,  if add P2 to C3 again > C3 --> P2
#
# Input
#   - cc          - credit card dict
#   - description 
#     must given. This is the only value that we could find this subscription
#     in our database by a given stripe.Subscription record, without searching 
#     our whole database. It should be an unqiue ID which we could locate the 
#     row every quick.
#   - subscription_id  - the "Plan" we created by plan()
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   customer_dict - stripe create a customer 'who is using this subscription'
#   customer_id   - comes from customer_dict, used for cancel a subscription
#   subscription_dict - The detail of the subscription 
#
def subscription(cc, description, subscription_id):
    # create a customer first
    emsg = _check_card(cc)
    if emsg:
        return {'rv': False, 'error_msg': emsg}

    rv, resp = _call_('customer',
        card = cc,
        description = description
    )
    if not rv:
        return {'rv': False, 'error_msg': resp}
    
    customer = resp
    customer_dict = customer.to_dict()
    
    cvc_check = customer_dict.get('active_card').get('cvc_check')
    if not config.CVC_CHECK_POLICY.get(cvc_check, False):
        return {
            'rv': False, 
            'error_msg': 'CVC check is failed. Subscription is not set.', 
            'customer_dict': customer_dict, 
            'customer_id': customer_dict.get('id')
        }

    # create subscripton based on the plan and the customer
    rv, resp = _call_('subscription',
        customer_instance = customer,
        plan = subscription_id
    ) 
    if not rv:
        return {'rv': False, 'error_msg': resp}
    
    return {
        'rv': True, 
        'error_msg': resp.get('failure_message'),
        'customer_dict': customer_dict,
        'customer_id': customer_dict.get('id'), 
        'subscription_dict': resp.to_dict(),
    }

#
# cancel_subscription
#
# Cancel a subscription for a customer 
#
# Input
#   - customer_id
#
# Output:
#   rv        - True or False
#   error_msg - if False
#   subscription_dict - The detail of the subscription 
#
def cancel_subscription(customer_id):
    rv, resp = _call_('cancel_subscription', id = customer_id)
    if not rv:
        return {'rv': False, 'error_msg': resp}
    return {
        'rv': True, 
        'error_msg': resp.get('failure_message'),
        'subscription_dict': resp.to_dict(),
    }
    


