from rest_framework import permissions


# If these functions return True the user owns the object passed,
# If they return False the user doesn't, if None the objects is not recogniszed
def is_user_product(product, user):
    x = 'product'
    if hasattr(product, 'store') and hasattr(product.store, 'storeprofile') and hasattr(product.store.storeprofile, 'user'):
        return product.store.storeprofile.user == user
        # print(f'user owns this {x} is {True}')

def is_user_store(store, user):
    x = 'store'
    if hasattr(store, 'storeprofile') and hasattr(store.storeprofile, 'user'):
        return store.storeprofile.user == user
        # print(f'user owns this {x} is {True}')

def is_user_store_setting(settings, user):
    x = 'settings'
    if hasattr(settings, 'store') and hasattr(settings.store, 'storeprofile') and hasattr(settings.store.storeprofile, 'user'):
        return settings.store.storeprofile.user == user
        # print(f'user owns this {x} is {True}')

def is_user_codebase(codebase, user):
    x = 'codebase'
    if hasattr(codebase, 'user'):
        return codebase.user == user    
        # print(f'user owns this {x} is {True}')

def is_user_code(code, user):
    x = 'code'
    if hasattr(code, 'codebase') and hasattr(code.codebase, 'user'):
        return code.codebase.user == user    
        # print(f'user owns this {x} is {True}')


class IsCreator(permissions.BasePermission):
    """
    Custom permission to allow access to only owners of an object (that is users that are related as the creater of the product)
    """

    def has_object_permission(self, request, view, obj):
        """
        Checks if the user requesting access is the owner of the product object.
        """

        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False

        user = request.user
        return (
            is_user_product(obj, user) or
            is_user_store(obj, user) or
            is_user_store_setting(obj, user) or
            is_user_codebase(obj, user) or
            is_user_code(obj, user)
        )


# from src.store.models import *
# from src.users.models import *
# user = User.objects.all().first()
# other = User.objects.all()[1]
# product = UserStoreProduct.objects.all()
# code = Code.objects.all().first()
# codebase = code.codebase