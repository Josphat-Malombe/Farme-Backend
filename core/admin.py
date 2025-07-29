from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import UserAdmin
from .models import User, ChatSession, ChatMessage, Ward,Constituency,County

@admin.register(User)
class FarmerAdmin(UserAdmin):
    model = User
    list_display = ('full_name', 'phone_number', 'email', 'county', 'is_staff', 'is_active')
    search_fields = ('full_name', 'phone_number', 'email')
    list_filter = ('is_staff', 'is_active', 'county')

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'county', 'constituency', 'ward')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    ordering = ('phone_number',)

admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(County)
admin.site.register(Constituency)
admin.site.register(Ward)
