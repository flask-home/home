from django.shortcuts import render
from django.views.generic import View
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

class IndexView(View):
    '''首页'''
    def get(self, request):
        '''显示首页'''
        # 获取商品种类信息
        types = GoodsType.objects.all()

        # 获取首页轮播商品信息
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')

        # 获取首页促销信息
        promotion_banners = IndexPromotionBanner.objects.all()

        # 获取首页分类商品展示信息
        # type_goods_banners = IndexTypeGoodsBanner.objects.all()
        for type in types:
            # 获取type种类首页分类商品的图片展示信息
            image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
            # 获取type种类首页分类商品的文字提示信息
            title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

            type.image_banners = image_banners
            type.title_banners = title_banners

        # 获取用户购物车商品的数目
        cart_count = 0

        #组织模板上下文
        context = {
            'types': types,
            'goods_banners': goods_banners,
            'promotion_banners': promotion_banners,
            'cart_count': cart_count
        }

        return render(request, 'index.html', context)

