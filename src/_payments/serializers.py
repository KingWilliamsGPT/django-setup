from rest_framework import serializers
from rest_framework.serializers import Serializer, FileField
from djmoney.money import Money
from djmoney.contrib.django_rest_framework.fields import MoneyField

from src.common.decorators import add_url
from src.store.models import (
    UserStoreProduct,
)

from src.payments.models import (
    DailyTransactionStat,
    Transaction,
    OrderItem,
)

from src.store.serializers import PaymentMethodSerializer


# UserStore #######################################################################################################################


class CheckoutUserProductSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField(min_value=1, default=1)
    product_id = serializers.UUIDField(required=True)

    class Meta:
        model = UserStoreProduct
        fields = (
            'product_id',
            'amount',
        )
        extra_kwargs = {
            'product_id': {'required': True}
        }

    @add_url
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # ...additional data to the representation here
        return representation



class CheckoutProductSerializer(serializers.Serializer):
    products = CheckoutUserProductSerializer(many=True)
    payment_method_id = serializers.IntegerField(min_value=0)
    store_owner_id = serializers.UUIDField()

    # add sucess url and falure url
    success_url = serializers.CharField(max_length=1000, allow_blank=False,
                                       help_text="where to go when the payment is sucessful")
    cancel_url = serializers.CharField(max_length=1000, allow_blank=False,
                                        help_text="where to go when the payment fails")





class StripePostProcessLinksSerializer(serializers.Serializer):
    return_url = serializers.CharField(max_length=1000, allow_blank=False,
                                       help_text="The URL the user will be redirected to if the account link is expired, has been previously visited, or is otherwise invalid. The URL you specify should attempt to generate a new account link with the same parameters used to create the original account link, then redirect the user to the new account link's URL so they can continue with Connect Onboarding. If a new account link cannot be generated or the redirect fails you should display a useful error to the user.")
    refresh_url = serializers.CharField(max_length=1000, allow_blank=False,
                                        help_text="The URL that the user will be redirected to upon leaving or completing the linked flow.")


# Statistics #######################################################################################################################


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product_name',
            'quantity',
            'price',
            'product',
        )



class TransactionSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment_method = PaymentMethodSerializer()
    
    class Meta:
        model = Transaction
        fields = (
            'date_created',
            'id',
            'paid',
            'fufiled',
            'amount_ordered',
            'amount_paid',
            'buyer_email',
            'buyer_name',
            'buyer_phone',
            'payment_method',
            'items', 
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['currency'] = 'PLN'

        return representation


class CreateCustomTransactionSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(required=True)
    customer_email = serializers.EmailField(required=True)
    customer_phone_number = serializers.CharField(max_length=500, required=False, default='')
    quantity = serializers.IntegerField(min_value=0, required=True)
    price_per_product = MoneyField(max_digits=14, decimal_places=2, default_currency='PLN')
    currency = serializers.CharField(max_length=500, required=True)
    paid = serializers.BooleanField(required=True)
    

class DailyTransactionStatSerializer(serializers.ModelSerializer):
    user_store_transactions = TransactionSerializer(many=True)

    class Meta:
        model = DailyTransactionStat
        fields = (
            'date_created',
            'id',
            'user_store_transactions',
        )

    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # ...additional data to the representation here
        request=self.context.get('request')
        if request:
            pass

        return representation



class AllStatisticsSerializer(serializers.Serializer):
    transactions = DailyTransactionStat()
    # quantity sold
    total_sold_codes = serializers.IntegerField(default=0)
    sold_codes_this_month = serializers.IntegerField(default=0)
    # income made
    income_today = serializers.IntegerField(default=0)
    income_this_month = serializers.IntegerField(default=0)
    currency = serializers.CharField(max_length=5, default='PLN')



class StatRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    # def validate(self, data):
    #     """
    #     Check that the start_date is before the end_date.
    #     """
    #     if data['start_date'] > data['end_date']:
    #         raise serializers.ValidationError({"error": "Start date must be before end date."})
    #     return data
