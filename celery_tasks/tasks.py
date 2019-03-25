#使用celery
import time
from celery import Celery
from django.core.mail import send_mail
from Pesticide.settings import EMAIL_FROM

# 在任务处理者一端加这几句
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Pesticide.settings")
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
django.setup()

#创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/0')

#定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '稼稼乐欢迎信息'
    message = ''
    sender = EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s,欢迎您成为稼稼乐农药网注册会员</h1>请点击下面链接激活您的账户<br><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s'%(username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)
    time.sleep(5)


def generate_static_index_html():
    '''产生首页静态页面'''