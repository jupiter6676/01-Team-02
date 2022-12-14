from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignupForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import logout as auth_logout
from .forms import CustomUserChangeForm, ProfileForm
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from products.models import Cart, Ddib
from .models import OrderItem, WatchItem, Product, User
from django.contrib import messages
from .forms import ProductBuyForm
from products.models import *
from products.forms import *
from django.http import JsonResponse
import json
from django.db.models import Q
from django.core.paginator import Paginator


# Create your views here.
def signup(request):
    if request.method == "POST":
        forms = SignupForm(request.POST, request.FILES)
        if forms.is_valid():
            user = forms.save()      
            Cart.objects.create(user=user)
            Ddib.objects.create(user=user)
            # UserDdib.objects.create(user=user)
            return redirect("articles:index")
    else:
        forms = SignupForm()
    context = {
        "forms": forms,
    }
    return render(request, "accounts/signup.html", context)

def isValidId(request):
    data = json.loads(request.body)
    username = data.get("username")
    print(data)

    if User.objects.filter(Q(username = data['username'])).exists():
        flag = 1
    else:
        flag = 0

    context = {
        "flag": flag,
        }
    return JsonResponse(context)

def index(request):
    members = get_user_model().objects.all()
    return render(request, "accounts/index.html")


def login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(request.GET.get("next") or "articles:index")
        messages.warning(request, '?????????, ??????????????? ??????????????????', extra_tags='')
    else:
        form = AuthenticationForm()
    context = {"forms": form}
    return render(request, "accounts/login.html", context)


def logout(request):
    auth_logout(request)
    return redirect("accounts:index")


@login_required
def profile_update(request):
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)
        address = request.POST.get('address')

        if form.is_valid():
            form.save()

        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)

        if address:
            user=request.user
            user.address = address
            user.save()

        return redirect("accounts:profile", request.user.pk) 

    else:
        form = CustomUserChangeForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    context = {
        "form": form,
        "password_form": password_form
    }

    return render(request, "accounts/profile_update.html", context)


@login_required
def change_password(request):
    if request.method == "POST":
        forms = PasswordChangeForm(request.user, request.POST)
        if forms.is_valid():
            forms.save()
            update_session_auth_hash(request, forms.user)  # ????????? ??????
            return redirect("accounts:profile")
    else:
        forms = PasswordChangeForm(request.user)
    context = {
        "forms": forms,
    }
    return render(request, "accounts/change_password.html", context)
    
@login_required
def profile(request, user_pk):
    products = Product.objects.order_by('-pk')
    user = get_object_or_404(get_user_model(), pk=user_pk)
    ddib = Ddib.objects.get(user=user) # ????????? ???????????? ???(??????)??? ????????????.
    ddib_items = ddib.ddibitem_set.all() # ?????? ??????(?????? ?????? ?????? ?????????)??? ????????????.
    
    # ???????????? ?????? ?????? id ?????????
    order_product_ids = OrderItem.objects.filter(user=user).values_list('product', flat=True).distinct()
    order_items = []
    for id in order_product_ids:
        order_items.append(Product.objects.get(pk=id))

    watch_items = WatchItem.objects.filter(user=user)
    inquiries = user.inquiry_set.order_by('-pk')


    product_buy_form = ProductBuyForm() 
    cart = Cart.objects.get(user=user)
    cart_items = cart.cartitem_set.all()

    # ?????? ??????????????????
    inquiry_page = request.GET.get('inquiry_page', '1')
    inquiry_paginator = Paginator(inquiries, 5)
    inquiry_page_obj = inquiry_paginator.get_page(inquiry_page)

    # ??? ?????? ??????, ????????? ??? ??????
    total_payment = sum(OrderItem.objects.filter(user=user).values_list('price', flat=True))
    total_point = total_payment // 10
    
    if total_point >= 50000:
        user.rating = 'GOLD'
        user.save()
    elif total_point >= 30000:
        user.rating = 'SILVER'
        user.save()
    
    context = {
        "person": user,
        "ddib_items": ddib_items,
        'product_buy_form': product_buy_form,
        'order_items': order_items,
        'watch_items': watch_items,
        'cart_items': cart_items,
        'inquiries': inquiry_page_obj,
        'products': products,
        'total_payment': total_payment,
        'total_point': total_point,
    }

    return render(request, "accounts/profile.html", context)

# ?????? ?????? ??????
def ddib_delete(request, product_pk):
    product = Product.objects.get(pk=product_pk)
    ddib = Ddib.objects.get(user=request.user) # user??? ddib 1:1
    ddib_items = ddib.ddibitem_set.all()

    for item in ddib_items:
        if product == item.product:
            item.delete()
            break
    return redirect('accounts:profile', request.user.pk)


@login_required
def follow(request, user_pk):
    person = get_user_model().objects.get(pk=user_pk)
    if person != request.user:
        if person.followers.filter(pk=request.user.pk).exists():
            person.followers.remove(request.user)
        else:
            person.followers.add(request.user)
        return redirect("accounts:profile", user_pk)
    else:
        return HttpResponseForbidden()


@login_required
def delete(request):
    request.user.delete()
    auth_logout(request)
    return redirect("accounts:login")


# ???????????? ????????? ???????????? ?????????
@login_required
def cart(request):
    cart = Cart.objects.get(user=request.user)

    cart_items = cart.cartitem_set.all()
    
    # ???????????? ????????? checked??? ???
    # total_price = 0
    # for item in cart_items:
    #     total_price += item.product.price * item.quantity

    context = {
        'cart_items': cart_items,
        # 'total_price': total_price,
    }

    return render(request, 'accounts/cart.html', context)


# ?????????????????? ??????
@login_required
def cart_update(request):
    cart = Cart.objects.get(user=request.user)
    selected_items = request.POST.getlist('selected_items') # ????????? ??????????????? product_pk ?????????
    
    # print(request.POST)
    deleted_item_pk_list = []

    if 'select_delete' in request.POST.get('kindOfSubmit'):
        for i in range(len(selected_items)):
            # ????????? ???????????? ???????????? pk??? ????????? ???????????? ????????? ?????????.
            cart_item = cart.cartitem_set.get(pk=selected_items[i])
            cart_item.delete()
            deleted_item_pk_list.append(selected_items[i])
    
    elif 'delete' in request.POST.get('kindOfSubmit'):
        product_pk = request.POST.get('productPk')
        cart_item = cart.cartitem_set.get(pk=product_pk)
        cart_item.delete()
        deleted_item_pk_list.append(product_pk)

    data = {
        'deletedItemList': deleted_item_pk_list,
    }

    # return redirect('accounts:cart')
    return JsonResponse(data, safe=False)

def tocart(request, product_pk):
    product = Product.objects.get(pk=product_pk)
    cart = Cart.objects.get(user=request.user)

    cart_items = cart.cartitem_set.all()

    # if request.method == 'POST':
    #     cartitem = CartItem()
    #     cartitem.quantity = request.POST['checkquantity']
       
    #     cartitem.cart = Cart.objects.get(pk=request.user.pk)
    #     cartitem.product = product
        
    #     cartitem.save()

    if request.method == 'POST':
        for item in cart_items:
            if item.product.pk == product_pk:
                item.quantity += int(request.POST['checkquantity'])
                item.save()
                break
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=int(request.POST['checkquantity']))
            
    return redirect('accounts:cart')


# ???????????? ??????
def payment(request):
    cart = Cart.objects.get(user=request.user)

    imp_uid = request.POST.get('imp_uid')
    merchant_uid = request.POST.get('merchant_uid')
    selected_items = request.POST.getlist('selected_items') # ????????? ??????????????? product_pk ?????????
    quantities = request.POST.getlist('quantities') # ????????? ??????????????? quantity ?????????
    
    for i in range(len(selected_items)):
        # 1. ????????? ???????????? ???????????? pk??? ????????? ???????????? ????????? ?????????.
        cart_item = cart.cartitem_set.get(pk=selected_items[i])
        # 2. ???????????? ??????????????? ????????? ???????????? ??????
        quantity = int(quantities[i])
        
        # ?????? ????????? ???????????? ????????? ??????
        OrderItem.objects.create(product=cart_item.product, quantity=quantity, user=request.user, imp_uid=imp_uid, merchant_uid=merchant_uid, price=cart_item.product.price * quantity)
        cart_item.product.sold_count += 1
        cart_item.product.save()
        cart_item.delete()

    return redirect('accounts:cart')
