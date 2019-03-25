import re

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

from django_redis import get_redis_connection


from celery_tasks.tasks import send_register_active_email


from user.models import User, Address
from goods.models import GoodsSKU
from Pesticide.settings import SECRET_KEY
from utils.mixin import LoginRequiredMixin


class RegisterView(View):
    '''注册'''
    def get(self,request):
        '''显示注册页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''进行处理处理'''
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        print(email)
        allow = request.POST.get('allow')

        # 进行数据校验:完整性
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验两次密码
        if password != cpassword:
            return render(request, 'register.html', {'errmsg': '两次密码不一致'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱不合法'})

        # 校验是否同意用户协议User.objects.create_user(username, password, email)
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意用户协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None
        if user:
            # 用户名 已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # #进行业务处理：进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # user.email = email
        # user.save()

        # 由于User模型类继承django内置的认证方法，所以创建users直接可以用create_user()
        user = User.objects.create_user(username, email, password)  # 默认激活
        user.is_active = 0  # 刚注册完不能是激活状态
        user.save()

        # 发送激活邮件，包含激活链接
        # 激活链接中需要包含用户身份信息
        # 加密用户的身份信息，生成激活的token
        serializer = Serializer(SECRET_KEY, 360)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()

        #  发邮件
        send_register_active_email.delay(email, username, token)

        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''
    def get(self, request, token):
        '''进行用户解密'''
        serializer = Serializer(SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取激活用户的id
            user_id = info['confirm']
            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转到登录页面
            return redirect(reverse('user:login'))

        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


class LoginView(View):
    '''登录'''
    def get(self,request):
        '''显示登录页面'''
        # 判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                # 记录用户登录状态
                login(request, user)

                # 获取登录后索要跳转的地址,默认跳转到首页
                next_url = request.GET.get('next', False)
                if next_url:
                    print(next_url)
                    response = redirect(next_url)
                else:
                    response = redirect(reverse('goods:index'))
                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                #跳转到首页
                return response
            else:
                return render(request, 'login.html', {'errmsg':'账户未激活'})

        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    '''退出登录'''
    def get(self, request):
        # 清除用户的session信息
        logout(request)
        # 跳转到首页
        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        '''显示'''
        # 如果用户未登录->AnonymousUser的一个实例
        # 如果用户登录-> User类的一个实例
        # request.is_authenticated()
        # 除了我们给模板传递你的模板变量之外，django框架会把request.user也传给模板文件

        # 获取用户个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='localhost', port=6379, db=1)
        conn = get_redis_connection('default')

        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品id
        sku_ids = conn.lrange(history_key, 0, 4)

        # 从数据库中查询用户
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user', 'address': address, 'goods_li': goods_li}
        return render(request, 'user_center_info.html', context)


class UserOrderView(LoginRequiredMixin, View):

    def get(self, request):
        '''显示'''
        # page = 'user'
        # request.user
        # 如果用户未登录->AnonymousUser的一个实例
        # 如果用户登录-> User类的一个实例
        # request.is_authenticated()
        # 除了我们给模板传递你的模板变量之外，django框架会把request.user也传给模板文件
        return render(request, 'user_center_order.html', {'page': 'order'})


class AddressView(LoginRequiredMixin, View):

    def get(self, request):
        '''显示'''
        # 获取用户默认地址
        user = request.user
        # print(user)
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        #     print(address)
        # except Address.DoesNotExist:
        #     address = None
        #     print(address)
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})


    def post(self, request):
        '''地址的添加'''
        # 接收的数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        # 校验手机号
        if not re.match(r'^1[3|4|5|6|7|8|9][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式不正确'})
        # 业务处理：地址的添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则为收货地址
        # 获取登录用户对应的User对象
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        #
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               phone=phone,
                               zip_code=zip_code,
                               is_default=is_default)
        # 返回应答，刷新地址页面
        print(reverse('user:address'))
        return redirect(reverse('user:address'))
