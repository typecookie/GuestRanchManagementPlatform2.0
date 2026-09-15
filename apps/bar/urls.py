from django.urls import path
from . import views

app_name = 'bar'

urlpatterns = [
    # Inventory items CRUD
    path('', views.inventory_list, name='inventory_list'),
    path('new/', views.item_create, name='item_create'),
    path('tags/quick-add/', views.quick_add_tag, name='quick_add_tag'),
    path('tags/', views.tag_list, name='tag_list'),
    path('<int:pk>/', views.item_detail, name='item_detail'),
    path('<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('<int:pk>/delete/', views.item_delete, name='item_delete'),

    # Bar reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/valuation/', views.report_valuation, name='report_valuation'),
    path('reports/low-stock/', views.report_low_stock, name='report_low_stock'),
    path('reports/distributors/', views.report_distributors, name='report_distributors'),
    path('reports/count-sheet/', views.report_count_sheet, name='report_count_sheet'),
]
