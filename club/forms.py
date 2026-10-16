from django import forms
from .models import MonthlyFee, Payment, Player, FeePlan

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = [
            'first_name', 'last_name', 'ci', 'phone', 'parent_phone', 
            'blood_type', 'address', 'email', 'photo', 'fee_plan', 
            'custom_monthly_fee', 'registration_date', 'billing_day', 'initial_debt'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'ci': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'blood_type': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'fee_plan': forms.Select(attrs={'class': 'form-select'}),
            'custom_monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'registration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'billing_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'initial_debt': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['player', 'amount', 'payment_method', 'payer_name', 'reference_number', 'transfer_date']
        widgets = {
            'player': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'transfer_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class MonthlyFeeForm(forms.ModelForm):
    class Meta:
        model = MonthlyFee
        fields = ['player', 'year', 'month', 'amount', 'due_date']
        widgets = {
            'player': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'month': forms.NumberInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }