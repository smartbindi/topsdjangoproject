from django.shortcuts import render,redirect
from .models import User,Product,Wishlist,Cart,Transaction
from django.conf import settings
from django.core.mail import send_mail
import random
from django.http import JsonResponse
from .paytm import generate_checksum, verify_checksum
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

def initiate_payment(request):
    
    try:
    	user=User.objects.get(email=request.session['email'])
    	amount = int(request.POST['amount'])
    except:
        return render(request, 'pay.html', context={'error': 'Wrong Accound Details or amount'})

    transaction = Transaction.objects.create(user=user,amount=amount)
    transaction.save()
    merchant_key = settings.PAYTM_SECRET_KEY

    params = (
        ('MID', settings.PAYTM_MERCHANT_ID),
        ('ORDER_ID', str(transaction.order_id)),
        ('CUST_ID', str(user.email)),
        ('TXN_AMOUNT', str(transaction.amount)),
        ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
        ('WEBSITE', settings.PAYTM_WEBSITE),
        # ('EMAIL', request.user.email),
        # ('MOBILE_N0', '9911223388'),
        ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
        ('CALLBACK_URL', 'http://localhost:8000/callback/'),
        # ('PAYMENT_MODE_ONLY', 'NO'),
    )

    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)

    transaction.checksum = checksum
    transaction.save()

    carts=Cart.objects.filter(user=user,status="pending")
    for i in carts:
    	i.status="Completed"
    	i.save()

    carts=Cart.objects.filter(user=user,status="pending")
    request.session['cart_count']=len(carts)

    paytm_params['CHECKSUMHASH'] = checksum
    print('SENT: ', checksum)
    return render(request, 'redirect.html', context=paytm_params)

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        # Verify checksum
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = "Checksum Matched"
        else:
            received_data['message'] = "Checksum Mismatched"
            return render(request, 'callback.html', context=received_data)
        return render(request, 'callback.html', context=received_data)


def validate_email_login(request):
	email=request.GET.get('email')
	data={
		'is_taken':User.objects.filter(email__iexact=email).exists()
	}
	print(data)
	return JsonResponse(data)

def validate_email_signup(request):
	email=request.GET.get('email')
	data={
		'is_taken':User.objects.filter(email__iexact=email).exists()
	}
	print(data)
	return JsonResponse(data)
def index(request):
	return render(request,'index.html')

def product_list(request):
	products=Product.objects.all()
	return render(request,'product-list.html',{'products':products})

def product_detail(request):
	return render(request,'product-detail.html')

def cart(request):
	net_price=0
	shipping_cost=0
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status="pending")
	for i in carts:
		shipping_cost=shipping_cost+50
		net_price=net_price+i.total_price

	grand_total=net_price+shipping_cost
	request.session['cart_count']=len(carts)
	return render(request,'cart.html',{'carts':carts,'net_price':net_price,'shipping_cost':shipping_cost,'grand_total':grand_total})

def checkout(request):
	return render(request,'checkout.html')

def my_account(request):
	return render(request,'my-account.html')

def wishlist(request):

	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status="pending")
	wishlists=Wishlist.objects.filter(user=user)
	for i in wishlists:
		for j in carts:
			if i.product==j.product:
				print("i.product : ",i.product)
				print("j.product : ",j.product)
				i.cart_status="Completed"
				i.save()
				
			
	request.session['wishlist_count']=len(wishlists)
	return render(request,'wishlist.html',{'wishlists':wishlists})

def logout(request):
	try:
		del request.session['email']
		del request.session['fname']
		del request.session['wishlist_count']
		del request.session['cart_count']
		return render(request,'login.html')
	except:
		return render(request,'login.html')

def login(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'],password=request.POST['password'])
			if user.usertype=="user":

				request.session['fname']=user.fname
				request.session['email']=user.email
				wishlists=Wishlist.objects.filter(user=user)
				request.session['wishlist_count']=len(wishlists)
				carts=Cart.objects.filter(user=user,status="pending")
				request.session['cart_count']=len(carts)
				return render(request,'index.html')

			elif user.usertype=="seller":

				request.session['fname']=user.fname
				request.session['email']=user.email
				return render(request,'seller_index.html')

		except:
			msg1="Email Or Password Is Incorrect"
			return render(request,'login.html',{'msg1':msg1})
	else:
		return render(request,'login.html')

def contact(request):
	return render(request,'contact.html')

def signup(request):
	if request.method=="POST":
		try:

			User.objects.get(email=request.POST['email'])
			msg="Email Already Registered"
			return render(request,'login.html',{'msg':msg})

		except:

			User.objects.create(
					fname=request.POST['fname'],
					lname=request.POST['lname'],
					email=request.POST['email'],
					mobile=request.POST['mobile'],
					password=request.POST['password'],
					cpassword=request.POST['cpassword'],
					usertype=request.POST['usertype']
				)
			msg="User Signup Successfull"
			return render(request,'login.html',{'msg':msg})
	else:
		return render(request,'login.html')

def change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		
		old_password=request.POST['old_password']
		npassword=request.POST['npassword']
		cnpassword=request.POST['cnpassword']

		if user.password==old_password:
			if npassword==cnpassword:
				user.password=npassword
				user.cpassword=npassword
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'change_password.html',{'msg':msg})
	else:
		return render(request,'change_password.html')

def seller_change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		
		old_password=request.POST['old_password']
		npassword=request.POST['npassword']
		cnpassword=request.POST['cnpassword']

		if user.password==old_password:
			if npassword==cnpassword:
				user.password=npassword
				user.cpassword=npassword
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'seller_change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'seller_change_password.html',{'msg':msg})
	else:
		return render(request,'change_password.html')

def forgot_password(request):
	if request.method=="POST":
		try:
			User.objects.get(email=request.POST['email'])
			subject = 'OTP For Forgot Password'
			otp1=random.randint(1000,9999)
			message = 'Your OTP For Forgot Password Is '+str(otp1)
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [request.POST['email'],]
			send_mail( subject, message, email_from, recipient_list )
			return render(request,'otp.html',{'otp1':otp1,'email':request.POST['email']})
		except:
			msg="Email Is Not Registered"
			return render(request,'forgot_password.html',{'msg':msg})
	else:
		return render(request,'forgot_password.html')

def verify_otp(request):
	otp1=request.POST['otp1']
	otp2=request.POST['otp2']
	email=request.POST['email']

	if otp1==otp2:
		return render(request,'new_password.html',{'email':email})
	else:
		msg="Invalid OTP"
		return render(request,'otp.html',{'otp1':otp1,'email':email,'msg':msg})

def new_password(request):
	email=request.POST['email']
	npassword=request.POST['npassword']
	cnpassword=request.POST['cnpassword']

	if npassword==cnpassword:
		user=User.objects.get(email=email)
		user.password=npassword
		user.cpassword=npassword
		user.save()
		return redirect('login')
	else:
		msg="Password & Confirm New Password Does Not Matched"
		return render(request,'new_password.html',{'email':email,'msg':msg})

def seller_index(request):
	return render(request,'seller_index.html')

def seller_add_product(request):
	if request.method=="POST":
		seller=User.objects.get(email=request.session['email'])
		Product.objects.create(
				seller=seller,
				product_category=request.POST['product_category'],
				product_name=request.POST['product_name'],
				product_price=request.POST['product_price'],
				product_desc=request.POST['product_desc'],
				product_color=request.POST['product_color'],
				product_size=request.POST['product_size'],
				product_image=request.FILES['product_image']
			)
		msg="Product Added Successfully"
		return render(request,'seller_add_product.html',{'msg':msg})

	else:
		return render(request,'seller_add_product.html')

def seller_view_product(request):

	seller=User.objects.get(email=request.session['email'])
	products=Product.objects.filter(seller=seller)
	return render(request,'seller_view_product.html',{'products':products})

def seller_product_detail(request,pk):
	product=Product.objects.get(pk=pk)
	return render(request,'seller_product_detail.html',{'product':product})

def seller_edit_product(request,pk):
	product=Product.objects.get(pk=pk)

	if request.method=="POST":
		
		product.product_category=request.POST['product_category']
		product.product_name=request.POST['product_name']
		product.product_price=request.POST['product_price']
		product.product_desc=request.POST['product_desc']
		product.product_color=request.POST['product_color']
		product.product_size=request.POST['product_size']

		try:

			product.product_image=request.FILES['product_image']

		except:

			pass
		
		product.save()
		return redirect('seller_view_product')

	else:
		return render(request,'seller_edit_product.html',{'product':product})

def seller_delete_product(request,pk):

	product=Product.objects.get(pk=pk)
	product.delete()
	return redirect('seller_view_product')

def user_product_detail(request,pk):

	flag=False
	user=User.objects.get(email=request.session['email'])
	product=Product.objects.get(pk=pk)
	try:
		wishlists=Wishlist.objects.get(user=user,product=product)
		flag=True
	except:
		pass
	return render(request,'user_product_detail.html',{'product':product,'flag':flag})

def add_to_wishlist(request,pk):

	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.create(user=user,product=product)
	return redirect('wishlist')

def remove_from_wishlist(request,pk):

	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	wishlist=Wishlist.objects.get(user=user,product=product)
	wishlist.delete()
	return redirect('wishlist')

def add_to_cart(request,pk):

	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.create(user=user,product=product,price=product.product_price,qty=1,total_price=product.product_price)
	return redirect('cart')

def remove_from_cart(request,pk):

	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	cart=Cart.objects.get(user=user,product=product)
	cart.delete()
	return redirect('cart')

def change_qty(request,pk):

	cart=Cart.objects.get(pk=pk)
	qty=int(request.POST['qty'])
	cart.qty=qty
	cart.total_price=cart.price*qty
	cart.save()
	return redirect('cart')

def myorder(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status="Completed")
	return render(request,'myorder.html',{'carts':carts})