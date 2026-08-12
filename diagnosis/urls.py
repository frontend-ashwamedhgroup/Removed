from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('diagnosis/new/', views.upload_diagnosis, name='upload_diagnosis'),
    path('diagnosis/<uuid:batch_id>/', views.batch_detail, name='batch_detail'),
    path('diagnosis/<uuid:batch_id>/csv/', views.download_batch_csv, name='download_batch_csv'),
    path('profile/', views.profile, name='profile'),
    path('reviews/', views.review_queue, name='review_queue'),
    path('reviews/<int:item_id>/', views.review_item, name='review_item'),
]
