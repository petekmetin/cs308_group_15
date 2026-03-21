from django.urls import path
from . import views

urlpatterns = [
    # Brands
    path('brands/', views.BrandListCreateView.as_view(), name='brand-list'),
    path('brands/<int:pk>/', views.BrandDetailView.as_view(), name='brand-detail'),

    # Categories
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),

    # Sneakers
    path('sneakers/', views.SneakerListView.as_view(), name='sneaker-list'),
    path('sneakers/create/', views.SneakerCreateView.as_view(), name='sneaker-create'),
    path('sneakers/<int:pk>/', views.SneakerDetailView.as_view(), name='sneaker-detail'),
    path('sneakers/<int:pk>/set-price/', views.set_sneaker_price, name='sneaker-set-price'),

    # Reviews
    path('sneakers/<int:pk>/reviews/', views.ReviewListView.as_view(), name='review-list'),
    path('sneakers/<int:pk>/reviews/create/', views.ReviewCreateView.as_view(), name='review-create'),
    path('reviews/<int:pk>/moderate/', views.moderate_review, name='review-moderate'),

    # Wishlist
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:pk>/', views.wishlist_remove, name='wishlist-remove'),
]