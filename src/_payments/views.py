import logging
import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path 

from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.template import loader
from django.template import Context, Template
from django.http import HttpResponse
from django.db.models import Count, Sum
from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse

User = get_user_model()

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from src.store.models import UserStoreProduct, PaymentAccount, StripeAccount, PaypalAccount, Error
from src.store.models import get_store
from src.store.layout_compiler import LayoutCompiler
from src.common import mail as _mail
from src.common import zeptomail as _mailz
from src.common.helpers import format_money, generate_date_dict

from .models import (
    DailyTransactionStat
)
from .serializers import CheckoutProductSerializer
from .models import Transaction, TransactionError

from .serializers import (
    DailyTransactionStatSerializer,
    StatRangeSerializer,
    AllStatisticsSerializer,
    TransactionSerializer,
    CreateCustomTransactionSerializer,
)

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

EMAIL_TOKEN = settings.ELASTIC_EMAIL_KEY
SENDER_NAME = settings.ELASTIC_EMAIL_NAME
SENDER_EMAIL = settings.ELASTIC_EMAIL

LOGGER = logging.getLogger('src.payments.views')

ACCOUNT_DELETION_POLICY_VERIFICATION_TOKEN = settings.ACCOUNT_DELETION_POLICY_VERIFICATION_TOKEN


class Messages:
    successful_order = 'Successful Order'
    half_baked_order = 'Halve Backed Order'
    empty_codebase = 'Your codebase is currently Empty'
    low_codebase = 'Your codebase is currently Low'
    unsuccessful_order = 'Order not sent'
    successfull_order = 'Congratulations, Successful Order'

    @staticmethod
    def seller_msg(is_unsuccesful_order):
        return Messages.unsuccessful_order if is_unsuccesful_order else Messages.successful_order


    @staticmethod
    def low_codebase_msg(is_codebase_empty): # only call this method when codebase is low
        return Messages.empty_codebase if is_codebase_empty else Messages.low_codebase


class EmailTemplates:
    to_customer = 'common/products/index.html'
    to_seller = 'common/products/index.html'
    to_customer_personalized = 'common/personalized/index.html'


class Email:
    TEMPLATE_PATH = Path('src') / 'common' / 'templates'

    DEFAULT_IMAGE = r""""""
    
    @staticmethod
    def _send(to, msg, subject, replyTo=None, replyToName=None, from_name=None, bounce_email=None):
        # ELASTIC EMAIL CODE
        # email = _mail.Email(
        #     token=EMAIL_TOKEN,
        #     subject=subject,
        #     from_=SENDER_EMAIL,
        #     from_name=from_name or SENDER_NAME,
        #     to=(to,),
        #     html=msg,
        #     replyTo=replyTo,
        #     replyToName=replyToName,
        # )
        # _mail.send(email)

        # ZEPTO EMAIL CODE
        email = _mailz.Email(_mailz.Config(settings.ZEPTO_API_KEY), bounce_email)
        email.send(
            from_=settings.ZEPTO_EMAIL,
            from_name=settings.ZEPTO_EMAIL_NAME,
            to=(to,),
            subject=subject,
            html_body=msg,
            reply_to=((replyTo, replyToName),)
        )



    @staticmethod
    def renderLayoutView(layout, context):
        subject = layout.subject
        msg = layout.message

        # print(f'''{list(context['codes'])}\n'''*20)
        codes = list(context['codes']) or 'EMPTY'

        seller_context = {
            'CODES':            f"""<ul>{"".join(f'<li>{code}</li>' for code in context['codes'])}</ul>""",
            'THUMBNAIL':        f"<img src=\"{context['product'].get_image_url()}\" style=\"width: 200px; display: block; border-radius: 6px; text-align: center; float: right;\" />",
            'TITLE':            context['product'].name,
            'PRICE_PER_PRODUCT':context['product'].price,
            'TOTAL_PRICE':      context['order'].price,
            'QUANTITY':         context['order'].quantity,
            'CURRENCY':         context['currency'],
            'TRANSACTION_ID':   context['transaction'].id,
            'BUYER_EMAIL':      context['transaction'].buyer_email,
            'BUYER_PHONE':      context['transaction'].buyer_phone,
            'BUYER_NAME':       context['transaction'].buyer_name,
            'STORE_NAME':       context['transaction'].get_store_name(),
            # 'STORE_LOGO':       'still on it...',
        }

        layout = LayoutCompiler(msg, seller_context)
        layout_msg = layout.compile()

        email_context = {
            'msg': layout_msg,
            'date': context['transaction'].date_created,
            'footer': context['personalized_settings'].footer,
            'what_is_left': context['what_is_left'],
            'personalized_settings': context['personalized_settings'],
        }

        return Email._getPersonalizedTemplate().render(email_context)


    @staticmethod
    def SendCustomerTransaction(context, subject='Successful Order'):
        # context = {
        #         'transaction': transaction,
        #         'codes': codes_to_send,
        #         'order': order,
        #         'what_is_left': what_is_left,
        #         'store_owner': store_owner,
        #     }
        transaction = context['transaction']
        store = transaction.store
        store_owner = store.storeprofile.user
        seller_email = transaction.seller_email()
        seller_name = store_owner.get_full_name() or store_owner.get_username()
        general_settings = context['general_settings']
        order = context['order']
        product = order.product
        layout = product.layout


        context.update({
            'store': store,
            'store_owner': store_owner,
            'product': product,
            'seller_email': seller_email,
            'seller_name': seller_name,
        })

        from_name = None

        if not general_settings.use_default_layout and layout:
            msg = Email.renderLayoutView(layout, context)
            subject = layout.subject
        else:
            msg = Email._getCustomerTemplate().render(context)

        Email._send(
            to=transaction.buyer_email,
            msg=msg,
            subject=subject,
            replyTo=seller_email,
            replyToName=seller_name,
            from_name='TheUsersStore',
        )


    @staticmethod
    def SendSellerTransaction(context):
        pass

    @staticmethod
    def SendLowCodeWarning(subject, context):
        # TODO:
        # handle incomplete orders eg. (the following orders could not be complete because the codebase is empty)
        msg = Email._getLowCodeTemplate().render(context)

        transaction = context['transaction']
        store = transaction.store
        store_owner = store.storeprofile.user
        seller_email = transaction.seller_email()           # CRITICAL: either user.email or user.store_profile.store.settings.transaction_email
        seller_name = store_owner.get_full_name() or store_owner.get_username()        

        Email._send(
            to=seller_email,
            msg=msg,
            subject=subject,
        )

    @staticmethod
    def _getCustomerTemplate():
        path = EmailTemplates.to_customer
        return loader.get_template(path)

    @staticmethod
    def _getLowCodeTemplate():
        path = 'common/refil_codes/index.html'
        return loader.get_template(path)

    @staticmethod
    def _getPersonalizedTemplate():
        return loader.get_template(EmailTemplates.to_customer_personalized)


class FufilOrder:
    def __init__(self, payment_gateway='stripe', **kw):
        _payment_gateways = {
            'stripe': self.do_stripe_fufilment,
            # ... others
        }
        fufiler = _payment_gateways.get(payment_gateway, None)
        if fufiler is None:
            raise ValueError(f'payment_gateway should be in {list(_payment_gateways.keys())}')
        else:
            fufiler(**kw)
        self._threads = []

    def fufil_order(self, partial_transaction):
        # send email to customer with product

        '''
            Settings
                - trasaction email: mails to send seller sales messages, defaults=user.email
        '''

        if partial_transaction.fufiled:
            return

        code_to_orderitem_mapping = {}
        failed_codes_orderitems = []


        all_orders = partial_transaction.items.all()

        for order_to_fufil in all_orders:
            product = order_to_fufil.product # none should rarely happen
            if product:
                quantity = order_to_fufil.quantity
                remaining_codes = product.codebase.codes.filter(deleted=False)
                remaining_codes_count = len(remaining_codes)
                what_is_left = 0

                if quantity <= remaining_codes_count:
                    codes_to_send = remaining_codes[:quantity]
                else:
                    codes_to_send = remaining_codes
                    what_is_left = quantity - remaining_codes_count

                self.handle_one_product(
                    partial_transaction,
                    order_to_fufil,
                    codes_to_send,
                    what_is_left,
                    remaining_codes_count,
                )

        self.finish_sending_products()


    def handle_one_product(self, transaction, order, codes_to_send, what_is_left, remaining_codes_count):
        # handle fufilment of one product order
        from src.store.models import Code

        # send codes to buyer
        # send success | unfufiled orders to seller
        codebase = order.product.codebase
        minimum_code_limit = transaction.store.settings.code_warning_threshold
        codes_to_send = Code.objects.filter(id__in=(code.id for code in codes_to_send))
        store_profile = transaction.store.storeprofile
        general_settings = store_profile.general_settings
        personalized_settings = store_profile.personalized_settings

        context = {
            'transaction': transaction,
            'codes': codes_to_send,
            'order': order,
            'what_is_left': what_is_left, 
            'orders_fufiled': order.quantity - what_is_left, 
            'orders_not_fufiled': what_is_left, 
            'codes_left': remaining_codes_count,
            'codebasee': codebase,
            'codebase': codebase,
            'store_profile': store_profile,
            'general_settings': general_settings,
            'personalized_settings': personalized_settings,
            'currency': 'PLN',
        }

        is_unsuccesful_order = bool(what_is_left)
        is_codebase_low = remaining_codes_count <= minimum_code_limit

        def do_buyer():
            # deliver product to buyer
            # Todo:
            # - set thee sent codes as deleted
            
            # delete the codes: sortof
            # print('what is codes_to_send\n'*10)
            # print(f'codes_to_send={codes_to_send} type(codes_to_send)={type(codes_to_send)}')
            codes_to_send.update(deleted=True)

            subject = Messages.successful_order if not what_is_left  else Messages.half_baked_order
            Email.SendCustomerTransaction(context, subject)

        def do_seller():
            # delete the codes: sortof
            
            subject = Messages.successful_order if not what_is_left  else Messages.half_baked_order
            Email.SendCustomerTransaction(context, subject)


        def do_low_codebase():
            codebase_is_empty = remaining_codes_count==0
            subject = Messages.low_codebase_msg(codebase_is_empty)
            Email.SendLowCodeWarning(subject, context)

        do_buyer()
        # do_seller()
        if is_codebase_low:
            do_low_codebase()


    def finish_sending_products(thread_list=()):
        #I was hoping to thread self.handle_one_product()
        pass

    def post_fufil_order(self, transaction):
        # what to do when the other has been fufiled
        DailyTransactionStat.record(transaction)


    def _create_pending_transaction(self):
        pass

    def _codebase_is_low(self, code_count, transaction):
        return code_count <= transaction.store.settings.code_warning_threshold

    def _issue_low_codebase_warning(self, transaction, code_left, codebase):
        context = {
            'transaction': transaction,
            'codes_left': code_left,
            'codebase': codebase,
        }
        Email.SendLowCodeWarning(context)

    def _issue_empty_codebase_warning(self):
        pass

    def do_stripe_fufilment(self, others):
        # Fixed: calling this method more than once is idempotent
        # TODO: 
            # save order
            # send email to customer with product
            # send seller sales email
            # modify sales statistics
            # if codes are low notify seller

        # this method is basicaly to convert the stripe like items to more generic items so other 
        # methods can handle it.

        payment_status = others['payment_status']
        amount_total = others['amount_total']
        customer = others['customer']
        customer_email = others['customer_email']
        session = others['session']
        customer_name = session['customer_details']['name']
        customer_phone = session['customer_details']['phone'] or ""

        transaction_id = session["metadata"]["transaction_id"]

        transaction = Transaction.objects.filter(id=transaction_id).first()         # using the transaction id like this makes this process idempotent
        if not transaction:
            raise TransactionError("Stripe returned a transaction id that does not exits")

        if transaction.stripe_checkout_id != session['id']: # this code should never execute onless something is wrong with my code
            raise TransactionError("Cannot fill 2 stripe session ids on on transaction")

        if payment_status == 'paid':
            transaction.paid = True
            transaction.amount_paid=amount_total
            transaction.amount_paid/=100            # stripes measures in cent or something
            transaction.buyer_email=customer_email
            transaction.buyer_name=customer_name
            transaction.buyer_phone=customer_phone
            transaction.save()

            self.fufil_order(transaction)


class WebhookViewSet(viewsets.GenericViewSet):
    '''This should automaticaly be called by the payment service.'''

    permission_classes = []  
    queryset = PaymentAccount.objects.all()
    serializers = {'default': CheckoutProductSerializer, } # I prefere to use this than serializer_class, for scalability

    event = None

    
    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])


    def caller_is_stripe_server(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', None)

        if not sig_header:
            raise NotFound()

        # print(f'payload {payload} sig_header {sig_header} key {settings.STRIPE_WEBHOOK_KEY}')

        try:
            # block request from unkown webhook callers
            self.event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_KEY,
            )
            return True
        except ValueError as e:
            return False
        except stripe.error.SignatureVerificationError as e:
            logging.error('could not verify stripe server')
            logging.exception(e)
            return False


    def activate_account(self, account):
        account.is_init = True
        account.save()
        # with open('some_file', 'a') as f:
        #     f.write('account was created')
        


    @action(methods=['post'], detail=False, url_name='connect_stripe')
    def webhook_connect_stripe_account(self, request):
        '''Respond to all event from the stripe server'''
        from src.common.mail import send_html


        if self.caller_is_stripe_server(request):

            event = self.event

            # from src.common.mail import send_html
            # from pprint import pformat

            # send_html('Test Event', f'<h1>Last Event</h1> <pre>{pformat(event)}</pre>', ['williamusanga23@gmail.com'])

            if event['type'] == 'account.updated':
                account_id = event['data']['object'].id # connect only

                LOGGER.error(f'{account_id}')

                account = StripeAccount.objects.filter(account_id=account_id).first()

                # activate account
                self.activate_account(account)
                
            elif event['type'] == 'checkout.session.completed':
                # TODO:
                # create transaction
                # update statistics
                # deliver product to customer
                # send email to seller.
                session_object = event['data']['object']
                others = {
                    'payment_status':session_object['payment_status'],
                    'amount_total':session_object['amount_total'],
                    'customer':session_object['customer'],
                    'customer_email': session_object['customer_details']['email'],
                }
                session = stripe.checkout.Session.retrieve(
                    session_object['id'],
                    expand=['line_items'],
                )

                # from pprint import pformat

                # print('\n'*10, f"{pformat(session)}")

                others['session'] = session
                
                # fufil order
                if others['payment_status'] == 'paid':
                    FufilOrder('stripe', others=others)

            return HttpResponse(status=200)

        return HttpResponse(status=404)


    @action(methods=['get', 'post'], detail=False, url_name='ebay_account_closure_webhook')
    def ebay_account_closure_webhook(self, request):
        # try:
        #     from src.common.zeptomail import _send

        #     x=_send(to=('williamusanga23@gmail.com',), subject='Testing', html_body=f'<h1>Request Method {request.method}<br>{request.data}<br>Request.Get<br> </h1>') 
        #     return Response({}, 200)
        # except Exception:
        #     pass

        # return Response(request.query_params)

        this_url = request.build_absolute_uri()

        if this_url.startswith('https'):
            code = '100s'
        else:
            code = '100'

        e=Error.objects.create(code=code, msg=f'''\
REQUEST.METHOD => {request.method}
REQUEST.DATA => {request.data}
REQUEST.QUERYPARAMS => {request.query_params}
REQUEST.ABS_URL => {this_url}
''')

        if request.method == 'POST':
            # this is the part where I handle deleting user account

            return Response(request.data, 200)

        else:
            challenge_code = request.GET.get('challenge_code', None)
            if challenge_code is None:
                raise ValidationError('challenge_code Required')

            ACCOUNT_DELETION_WEBHOOK = request.build_absolute_uri(reverse('webhook-ebay_account_closure_webhook')) # this webhook url by the way
            toEncode = challenge_code+ACCOUNT_DELETION_POLICY_VERIFICATION_TOKEN+ACCOUNT_DELETION_WEBHOOK
            toHash = toEncode.encode()
            challenge_response = hashlib.sha256(toHash).hexdigest()

            e.msg += f"""\
{{
    "challengeResponse": {challenge_response},
    "webhook": {ACCOUNT_DELETION_WEBHOOK},
    "vtoken": {ACCOUNT_DELETION_POLICY_VERIFICATION_TOKEN},
    "toEncodee": {toEncode},
    "toHash": {toHash},
}}"""
            e.save()

            return Response({
                "challengeResponse": challenge_response,
            }, 200)
        


class CheckoutViewSet(viewsets.GenericViewSet):

    queryset = UserStoreProduct.objects.all()
    serializers = {'default': CheckoutProductSerializer, } # I prefere to use this than serializer_class, for scalability
    permission_classes = []  

    
    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

    def get_queryset(self):
        from src.store.models import UserStoreProduct
        return UserStoreProduct.objects.all()

    @action(methods=['post'], detail=False)
    def checkout(self, request):
        '''
            Send a list of products to this endpoint, I'll respond with a checkout url, redirect the user to that url.
            I'm guessing you might implement a cart, in the frontend with cookies. or just send a single product.
            
            - Any invalid product_id will be ignored.
            - Any product_id that does not exists will be ignored
            - Any product entry with ammout less than one will be ignored
            - Any product that does not belong to the seller are filtered out.
            - User must own the payment method
            - Payment method must exists
            - User must exists

            eg. 
            ```json
                {
                    "products": [
                        {"product_id": "...id", amount: min(1)},
                        {"product_id": "...id", amount: min(1)},
                        {"product_id": "...id", amount: min(1)},
                    ],
                    "payment_method_id": "",    # int
                    "store_owner_id": "",       # uuid
                }
            ```
        '''


        # Retrieve product details and total amount from request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        products = serializer.validated_data['products']
        payment_method = PaymentAccount.objects.filter(id=serializer.validated_data['payment_method_id']).first()
        store_owner_id = serializer.validated_data['store_owner_id']
        success_url = serializer.validated_data['success_url']
        cancel_url = serializer.validated_data['cancel_url']
        store_owner = User.objects.filter(id=store_owner_id).first()

        if not payment_method:
            raise ValidationError({'error': 'payment method id supplied does not exists'})

        # if not (payment_method.account.is_init):
        #     raise ValidationError({'error': f'this payment method has not been configured {payment_method.account.account_id}'})
        
        if not store_owner:
            raise ValidationError({'error': 'store_owner_id does not exists'})

        if payment_method.user != store_owner:
            raise ValidationError({'error': 'Store owner does not own this payment method'})



        product_and_amount = {
            # product_id: amount
        }

        for product in products:
            product_id = product.get('product_id', None)
            amount = product.get('amount', 0)
            if product_id and amount:
                product_and_amount[product_id] = amount

        product_ids = product_and_amount.keys()
        store = get_store(store_owner)

        products = (UserStoreProduct.objects
                    .filter(product_id__in=product_ids) # get only products in the db
                    .filter(store=store) # get only products that the user owns
                )

        # do specific checkout
        checkout_method = getattr(self, f'do_{payment_method.account_type.lower()}_checkout', None)

        if checkout_method is None:
            self.handle_checkout_error()


        checkout_link = checkout_method(
            products, store, product_and_amount, payment_method,
            # set success and cancel url
            success_url, cancel_url
        )

        return Response({'checkout_link': checkout_link})


    def do_stripe_checkout(self, products, store, product_and_amount, payment_method, success_url, cancel_url):
        # do stripe checkout
        from src.payments.helpers import stripe
        from src.payments.models import DailyTransactionStat


        account = payment_method.account
        destination_account_id = payment_method.account.account_id

        if not destination_account_id:
            # logger.critical_log('A configured stripe account failed at checkout')
            raise ValidationError({'error': 'The payment method supplied has not been configured A'})

        # check if this account has been fully configured
        if not account.is_init:
            stripe_acct = stripe.Account.retrieve(destination_account_id)
            if stripe_acct.requirements.currently_due:
                raise ValidationError({
                'error': 'The payment method supplied has not been configured B',
                'requirements': stripe_acct.requirements.currently_due,
                })
            else:
                account.is_init = True
                account.save()


        # cats = (url for url in ('https://th.bing.com/th/id/R.dfe8c4a50b45f659cb195b745b492f39?rik=qMZvfEb7oxH4Pw&pid=ImgRaw&r=0', 
        #         'https://th.bing.com/th/id/R.094ee0d312d6fb870f22e4e57a69bdd7?rik=394J%2fneqvGt7zQ&riu=http%3a%2f%2fimages4.fanpop.com%2fimage%2fphotos%2f16000000%2fBeautiful-Cat-cats-16096437-1280-800.jpg&ehk=7Ul0qN8DJPOyACXqdst%2bSeHYBg6ESI9MPS%2fjVm2XumU%3d&risl=&pid=ImgRaw&r=0', 
        #         'https://th.bing.com/th/id/OIP.UmQlynMptL0oLuBCpV3qxAHaEu?rs=1&pid=ImgDetMain'))

        # start a partial transaction, fill on payment
        transation = Transaction.objects.create(
            store=store,
            payment_method=payment_method,
        )

        line_items = []
        amount_ordered = 0
        for product in products:
            quantity = product_and_amount[product.product_id]
            amount_ordered += quantity
            line_items.append({
                'price_data': {
                    'currency': 'pln',  # would have had the user save a currency on the product
                    'product_data': {
                        'name': product.name,
                        'images': [i for i in [product.cloudinary_thumbnail] if i],
                        # 'images': [next(cats)],
                    },
                    'unit_amount': int(product.price.amount * 100),  # Stripe requires amount in cents
                },
                'quantity': quantity,
            })

            order = transation.items.create(
                product_name=product.name,
                quantity=product_and_amount[product.product_id],
                price=product.price * product_and_amount[product.product_id],
                # date_created=timezone.now(),
                # date_updated=timezone.now()
            )
            product.orders.add(order)
        
        transation.amount_ordered = amount_ordered

        if not line_items:
            transation.delete() 
            raise ValidationError({'error': 'No products that belonged to seller where supplied'})

        try:
            # Create a Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                payment_intent_data={
                    # "transfer_data": {"destination": '{{CONNECTED_ACCOUNT_ID}}'},
                    "transfer_data":{
                        'destination': destination_account_id,
                    },
                },
              metadata={
                'transaction_id': transation.id,
              }
            )
            transation.stripe_checkout_id = session['id']
            transation.save()

            DailyTransactionStat.record(transation)
        except stripe.error.InvalidRequestError as ex:
            transation.delete()
            raise APIException({'error': f'Stripe returned with the following error: {str(ex)}'})

        # Construct the checkout page link
        checkout_link = session.url

        # Return the checkout page link to the frontend
        return checkout_link


    def do_paypal_checkout(self):
        raise ValidationError({'error': 'NotImplemented'})


    def handle_checkout_error(self):
        raise ValidationError('Checkout does not support this account type')

    def _get_product_list_by_ids(self, products):
        pass



#########################################################################################################
# Statistis

class StatisticsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint for managing user store products.
    """
    queryset = DailyTransactionStat.objects.all()
    serializers = {
        'default': DailyTransactionStatSerializer, 
        'statistics': StatRangeSerializer,
        'summary': StatRangeSerializer,
    }
    permission_classes = [IsAuthenticated, ]  # Only authenticated users can access
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return user.store_profile.daily_transaction_stats.all()

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

    @action(methods=['get'], detail=False)
    def summary(self, request):
        now = timezone.now()
        all_transactions = request.user.store_profile.user_store.transactions.filter(paid=True)
        transactions_this_month = all_transactions.filter(date_created__month=now.month, date_created__year=now.year)
        
        total_sales = all_transactions.aggregate(total_amount_ordered=Sum('amount_ordered'))['total_amount_ordered'] or 0
        sales_this_month = transactions_this_month.aggregate(total_amount_ordered=Sum('amount_ordered'))['total_amount_ordered'] or 0
        # sales_this_month = Order.objects.filter(transaction__in=transactions_this_month).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        income_this_month = transactions_this_month.aggregate(total_amount_paid=Sum('amount_paid'))['total_amount_paid'] or 0
        income_today = transactions_this_month.filter(date_created__day=now.day).aggregate(total_amount_paid=Sum('amount_paid'))['total_amount_paid'] or 0

        data = {
            "total_sold_codes": total_sales,
            "sold_codes_this_month": sales_this_month,
            "income_today": intcomma(income_today),
            "income_this_month": intcomma(income_this_month),
            "currency": "PLN",
        }

        return Response(data, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def statistics(self, request):
        """
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        daily_stats = self.get_queryset().filter(date_created__range=(start_date, end_date))

        # transactions = DailyTransactionStatSerializer(daily_stats, many=True).data


        stats_total = None
        trs =  generate_date_dict(start_date, end_date)

        for day_transaction in daily_stats:
            store_transactions = day_transaction.user_store_transactions.all().filter(paid=True)
            payments = []
            for transaction in store_transactions:
                amount = transaction.amount_paid
                payments.append(amount)

            payment_sum = sum(payments)
            p = getattr(payment_sum, 'amount', payment_sum)

            # raise Exception([type(payment_sum), payment_sum, dir(payment_sum)])

            trs[day_transaction.date_created.strftime('%Y-%m-%d')] = str(p)

            if stats_total is None:
                stats_total = payment_sum
            else:
                stats_total += payment_sum

    
        if hasattr(stats_total, 'amount'):
            s = stats_total.amount
            stats_total=format_money(stats_total, default='PLN0')
        else:
            if stats_total is None:
                s = 0
            else:
                s = float(stats_total)
            stats_total = f'PLN{s}'

        if s <= 0:
            s = 1


        translated_data = {
            "transaction_dates": trs.keys(),
            "transaction_values": trs.values(),
            "stats_total": stats_total,
            "total": s,
        }

        return Response(translated_data, status=status.HTTP_200_OK)



class CreateCustomTransactionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet): 
    queryset = Transaction.objects.all().filter(paid=True)

    serializers = {
        'default': TransactionSerializer,
        'create_transaction': CreateCustomTransactionSerializer,
    }

    permission_classes = [IsAuthenticated, ]  # Only authenticated users can access

    def get_queryset(self):
        user = self.request.user
        return user.store_profile.user_store.transactions.all()

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

   
    @action(methods=['post'], detail=False)
    def create_transaction(self, request):
        custom_transaction_serializer = CreateCustomTransactionSerializer(data=request.data)

        try:
            custom_transaction_serializer.is_valid(raise_exception=True)
        except (InvalidOperation, ValueError):
            raise ValidationError({'error': 'Check the Money field'})

        product_id = custom_transaction_serializer.validated_data['product_id']
        customer_email = custom_transaction_serializer.validated_data['customer_email']
        customer_phone_number = custom_transaction_serializer.validated_data['customer_phone_number']
        quantity = custom_transaction_serializer.validated_data['quantity']
        price_per_product = custom_transaction_serializer.validated_data['price_per_product']
        # currency = custom_transaction_serializer.validated_data['currency']
        paid = custom_transaction_serializer.validated_data['paid']

        user = request.user
        transaction = Transaction.objects.create(
            store=user.store_profile.user_store,
            amount_paid=price_per_product*quantity,
            amount_ordered=quantity,
            fufiled=False,
            paid=paid,
            payment_method=None,
            buyer_email=customer_email,
            buyer_phone=customer_phone_number,
        )

        if transaction.paid:
            DailyTransactionStat.record(transaction)

        return Response({
            'id': transaction.id,
        }, 201)



class TransactionHistory(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint for managing user store products.
    """
    queryset = Transaction.objects.all().filter(paid=True)

    serializers = {
        'default': TransactionSerializer,
    }

    permission_classes = [IsAuthenticated, ]  # Only authenticated users can access

    def get_queryset(self):
        user = self.request.user
        return user.store_profile.user_store.transactions.all()

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])


class PaymentHistoryViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Transaction.objects.all().filter(paid=True)
    permission_classes = [IsAuthenticated, ]  # Only authenticated users can access

    serializers = {
        'default': TransactionSerializer,
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

    def get_queryset(self):
        user = self.request.user
        return user.store_profile.user_store.transactions.all().filter(paid=True)


