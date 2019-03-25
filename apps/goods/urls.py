from django.urls import path, include, re_path
from apps.goods.views import IndexView

app_name = 'goods'

urlpatterns = [
    re_path(r'^$', IndexView.as_view(), name='index') #首页
]
