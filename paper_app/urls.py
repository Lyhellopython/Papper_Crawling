from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),  # 首页
    path('papers/', views.paper_list, name="paper_list"),  # 论文列表
    path('logs/', views.logs, name="logs"),  # 日志查看
    path('collect/', views.collect_paper, name='collect_paper'),  # 收藏操作
    path('my-collections/', views.my_collections, name='my_collections'),  # 我的收藏
]