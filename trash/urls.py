from django.urls import path
from .views import TrashListView, RestoreItemView, PermanentDeleteView, EmptyTrashView

urlpatterns = [
    path('', TrashListView.as_view(), name='trash_list'),
    path('restore/', RestoreItemView.as_view(), name='restore_item'),
    path('permanently/<int:item_id>/<str:item_type>/', PermanentDeleteView.as_view(), name='permanently_delete'),
    path('empty/', EmptyTrashView.as_view(), name='empty_trash'),
]