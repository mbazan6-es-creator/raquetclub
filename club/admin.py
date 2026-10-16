from django.contrib import admin
from .models import MonthlyFee, Payment, PaymentAllocation, Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        'last_name',
        'first_name',
        'phone',
        'email',
        'registration_date',
        'is_active',
    )
    search_fields = ('first_name', 'last_name', 'phone')
    list_filter = ('is_active', 'registration_date')
    list_editable = ('is_active',)
    ordering = ('last_name', 'first_name')


@admin.register(MonthlyFee)
class MonthlyFeeAdmin(admin.ModelAdmin):
    list_display = (
        'player',
        'year',
        'month',
        'amount',
        'paid_amount',
        'pending_amount',
        'due_date',
        'status',
    )
    list_filter = ('status', 'year', 'month', 'due_date')
    search_fields = ('player__first_name', 'player__last_name', 'player__phone')
    ordering = ('-year', '-month', 'player')


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 1


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_date',
        'player',
        'amount',
        'payment_method',
        'reference_number',
        'registered_by',
        'is_voided',
    )
    list_filter = ('payment_method', 'is_voided', 'payment_date')
    search_fields = ('player__first_name', 'player__last_name', 'reference_number')
    inlines = [PaymentAllocationInline]
    ordering = ('-payment_date',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.registered_by = request.user
        super().save_model(request, obj, form, change)