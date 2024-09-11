from django.conf import settings

# from src.payments import payment_models

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

DEFAULT_CURRENCY = 'pln'
DEFAULT_COUNTRY = 'PL'


# note that '' empyty strings to stripe are to UNSET A PARAMETER VALUE
def create_stripe_product(
      name, 
      price, # string decimal
      stripe_id=None,
      is_active=True, # whether product is available for sale
      description=None,
      images=('https://th.bing.com/th/id/OIP.fT-6KPR8sc80czo1rlfRcwHaE8?rs=1&pid=ImgDetMain',), # a list of up to 8 urls
      is_shippable=False, # true for physical products
      product_public_url=None, # A URL of a publicly-accessible webpage for this product.
      bank_statement_string=None, #An arbitrary string to be displayed on your customer’s credit card or bank statement.
      unit_label=None,
      package_dimensions=None,
      height=None, length=None, weight=None, width=None,
    ):

  # RESPONSE
    # {
    #   "id": "prod_NWjs8kKbJWmuuc",
    #   "object": "product",
    #   "active": true,
    #   "created": 1678833149,
    #   "default_price": null,
    #   "description": null,
    #   "images": [],
    #   "features": [],
    #   "livemode": false,
    #   "metadata": {},
    #   "name": "Gold Plan",
    #   "package_dimensions": null,
    #   "shippable": null,
    #   "statement_descriptor": null,
    #   "tax_code": null,
    #   "unit_label": null,
    #   "updated": 1678833149,
    #   "url": null
    # }

  if package_dimensions is not None:
    if (height or length or weight or width) and None in (height, length, weight, width):
      raise TypeError('all package_dimensions keys must be set')
    package_dimensions = { # dimensions for this product for shipping purposes
        'height':height, # float required
        'length':length, # float required
        'weight':weight, # float required
        'width':width, # float required
      }

  product = stripe.Product.create(
    name=str(name),
    active=False,
    description=description,
    images=images,
    default_price_data={'currency':DEFAULT_CURRENCY, 'unit_amount_decimal': price},
    shippable=is_shippable,
    package_dimensions=package_dimensions,
    unit_label=unit_label,
    url=product_public_url,
    statement_descriptor=bank_statement_string,
  )


# SESSION

# def create_session(
#     success_url=None,
#     cancel_url=None, # go back
#     currency=DEFAULT_CURRENCY,
#     line_items={
#       adjustable_quantity:{
#         enabled: true,
#         maximum: 999999,
#         minimum: 1,
#       },
#       # price: <string>price_id,
#     },
#     mode='payment',
#     ui_mode="hosted",
#   ):
#   stripe.checkout.Session.create(
#     success_url="https://example.com/success",
#     line_items=[{"price": "price_1MotwRLkdIwHu7ixYcPLm5uZ", "quantity": 2}],
#     mode="payment",
#   )


def create_webhook_endpoint(
    url, # str
    # user,
    enabled_events=('*',),
    description=settings.STRIPE_OBJECT_DELETE_WARNING,
    connect=None,
  ):
  
  webhookendpoint = stripe.WebhookEndpoint.create(
    url=str(url),
    enabled_events=enabled_events,
    description=description,
    connect=connect,
  )

  return webhookendpoint

  # TODO: validate returned object before commiting the database


  # create the webhookendpoint and associate it 
  # user.payment_method.stripe_account
  # payment_models.WebhookEndpoint.create(
  # )


def get_user(secret_key):
  import stripe

  # Set your secret key
  stripe.api_key = secret_key

  try:
    # Retrieve the account information
    account = stripe.Account.retrieve()
  except stripe.AuthenticationError:
    return

  return account


def get_user_id(secret_key):
  return getattr(get_user(secret_key), 'id', None)


class OnboardAccount:
  '''
    refresh_url: The URL the user will be redirected to if the account link is expired, has been previously-visited, or is otherwise invalid. The URL you specify should attempt to generate a new account link with the same parameters used to create the original account link, then redirect the user to the new account link's URL so they can continue with Connect Onboarding. If a new account link cannot be generated or the redirect fails you should display a useful error to the user.
    return_url: The URL that the user will be redirected to upon leaving or completing the linked flow.
  '''

  country = DEFAULT_COUNTRY

  def __init__(self, webhook_url, refresh_url="https://example.com/reauth", return_url="https://example.com/return"):
    self.account = None
    self.account_link = None

    self.refresh_url=refresh_url
    self.return_url=return_url
    self.webhook_url=webhook_url # url to recieve webhook event for this account, THIS HAS TO BE THE BACKEND


  def create_account(self):
    # https://docs.stripe.com/api/accounts/create
    self.account = stripe.Account.create(                                                               
     country=self.country,                                                                             
     type="express",
     capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},    
     business_type="individual",                                                               
    )

  def create_account_link(self):
    if self.account is None:
      raise NameError({'error': 'Internal server error.'})

    self.account_link = stripe.AccountLink.create(                                                           
     account=self.account.id,
     refresh_url=self.refresh_url,
     return_url=self.return_url,
     type="account_onboarding",
    )

  def get_account_link(self):
    if self.account_link and self.account_link.get('url', None) is not None:
      return self.account_link.url
    
    if self.account is None:
      self.create_account()

    self.create_account_link()
    return self.account_link.url

  def is_connected(self):
    # returns True if the account is connected
    pass


  def use_account(self, acct_id):
    self.account = OnboardAccount.get_account(acct_id)
    

  @staticmethod  
  def list_accounts(*a, **kw):
    # list connected accounts
    # https://docs.stripe.com/api/accounts/list
    return stripe.Account.list(*a, **kw)

  @staticmethod
  def delete_account(id):
    # https://docs.stripe.com/api/accounts/delete
    return stripe.Account.delete(id)

  @staticmethod
  def get_account(id):
    # https://docs.stripe.com/api/accounts/retrieve
    return stripe.Account.retrieve(id)

  @staticmethod
  def update_account(id):
    # https://docs.stripe.com/api/accounts/update
    return stripe.Account.modify(id, *a, **kw)

  
  def create_webhook_endpoint(self):
    return stripe.WebhookEndpoint.create(
      
      enabled_events=[
        # https://docs.stripe.com/api/webhook_endpoints/create#create_webhook_endpoint-enabled_events
        'account.updated',              # we will need this to know when the account has been created# https://docs.stripe.com/connect/webhooks#connect-webhooks
        # "charge.succeeded",
        # "charge.failed"
      ],

      url=self.webhook_url,  # where to send events

      connect=True,

      metadata={
        'account_id': self.account.id,  # so I can save in db
      },

  )

  def board(self):
    self.create_account()
    self.create_account_link()
    self.create_webhook_endpoint()
