import uuid


from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from djmoney.models.fields import MoneyField
from django.db.models.signals import post_save
from django.dispatch import receiver



# from .serializers import CheckoutProductSerializer # this is causing circular imports

User = get_user_model()


class DailyTransactionStat(models.Model):
    '''This is a daily transaction object, all transaction'''
    # user_store_transactions
    # ebay_store_transactions
    date_created = models.DateTimeField(auto_now_add=True)
    store_profile = models.ForeignKey('store.StoreProfile', on_delete=models.CASCADE, related_name='daily_transaction_stats', null=True)
    # --> UserStoreTransactions
    # --> EbayStoreTransactions

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']


    @staticmethod
    def record(user_transaction):
        store_profile = user_transaction.store.storeprofile

        # get transaction stat for that day
        year, month, day = user_transaction.date_created.year, user_transaction.date_created.month, user_transaction.date_created.day
        stat = store_profile.daily_transaction_stats.filter(date_created__year=year, date_created__month=month, date_created__day=day).first()  # there should be only one
        
        if not stat: # DailyTransactionStat() object has not been created before
            stat = store_profile.daily_transaction_stats.create(
                store_profile=store_profile,    # how I identify the user
            )
        user_transaction.stat = stat
        user_transaction.save()



class Transaction(models.Model):
    # Note this only represents stripe transactions for user store only not ebay or any other store

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    amount_paid = MoneyField(max_digits=14, decimal_places=2, default_currency='PLN', editable=False, blank=True, null=True)
    amount_ordered = models.PositiveIntegerField(default=0, editable=False)
    paid=models.BooleanField(default=False, editable=False)

    fufiled = models.BooleanField(default=False, editable=False)

    payment_method = models.ForeignKey('store.PaymentAccount', on_delete=models.SET_NULL, null=True) # nullable
    store = models.ForeignKey('store.UserStore', on_delete=models.CASCADE, related_name='transactions') # not nullable because, no reference will point to this instance

    buyer_email = models.EmailField(blank=True, editable=False)
    buyer_name = models.CharField(max_length=1000, default='', blank=True, editable=False)
    buyer_phone = models.CharField(max_length=500, default='', blank=True, editable=False)

    # i feel like we should keep a reference to the stripe id
    stripe_checkout_id = models.CharField(max_length=1000, default='', blank=True, editable=False)


    stat = models.ForeignKey(DailyTransactionStat, on_delete=models.SET_NULL, related_name='user_store_transactions', null=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']

    def seller_email(self):
        storeprofile = self.store.storeprofile
        return storeprofile.general_settings.transaction_email or storeprofile.user.email 

    def get_store_name(self):
        user = self.store.storeprofile.user
        return self.store.settings.name or f'{user.get_short_name() or user.username}'


class OrderItem(models.Model):
    product = models.ForeignKey('store.UserStoreProduct', on_delete=models.SET_NULL, related_name='orders', null=True)  # The order to which this item belongs
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')  # The order to which this item belongs
    product_name = models.CharField(max_length=100, default='', editable=False)  # The name of the product
    quantity = models.PositiveIntegerField(default=0, editable=False)  # The quantity of the product in the order
    price = MoneyField(max_digits=14, decimal_places=2, default_currency='PLN', editable=False, blank=True, null=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']


class TransactionError(Exception):
    '''Error with ongoing transaction'''
