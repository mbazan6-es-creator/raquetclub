from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from .forms import MonthlyFeeForm, PlayerForm
from .models import MonthlyFee, Payment, PaymentAllocation, Player


def custom_login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'club/login.html', {'form': form})


def custom_logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    today = date.today()
    active_players_count = Player.objects.filter(is_active=True).count()
    pending_fees = MonthlyFee.objects.exclude(status='PAID')
    total_debt = sum(fee.pending_amount for fee in pending_fees) + sum(p.initial_debt for p in Player.objects.all())
    total_revenue = Payment.objects.filter(is_voided=False).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'today': today,
        'active_players_count': active_players_count,
        'total_debt': total_debt,
        'total_revenue': total_revenue,
    }
    return render(request, 'club/home.html', context)


@login_required
def player_list_view(request):
    query = request.GET.get('q', '')
    if query:
        players = Player.objects.filter(last_name__icontains=query) | Player.objects.filter(first_name__icontains=query)
    else:
        players = Player.objects.all()
    return render(request, 'club/player_list.html', {'players': players, 'query': query})


@login_required
def player_create_view(request):
    if request.method == 'POST':
        form = PlayerForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save()
            messages.success(request, f"Alumno {player.first_name} registrado con éxito.")
            return redirect('player_detail', pk=player.pk)
    else:
        form = PlayerForm()
    return render(request, 'club/player_form.html', {'form': form, 'title': 'Añadir Nuevo Alumno'})


@login_required
def player_edit_view(request, pk):
    player = get_object_or_404(Player, pk=pk)
    if request.method == 'POST':
        form = PlayerForm(request.POST, request.FILES, instance=player)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de {player.first_name} actualizados.")
            return redirect('player_detail', pk=player.pk)
    else:
        form = PlayerForm(instance=player)
    return render(request, 'club/player_form.html', {'form': form, 'title': 'Editar Alumno'})


@login_required
def player_detail_view(request, pk):
    player = get_object_or_404(Player, pk=pk)
    fees = player.fees.all()
    payments = player.payments.all()
    return render(request, 'club/player_detail.html', {'player': player, 'fees': fees, 'payments': payments})


@login_required
def pending_debts_view(request):
    players = Player.objects.all()
    players_with_debt = sorted(players, key=lambda p: p.total_pending_debt, reverse=True)
    return render(request, 'club/pending_debts.html', {'players': players_with_debt})


@login_required
@transaction.atomic
def collect_payment_view(request, pk):
    player = get_object_or_404(Player, pk=pk)
    pending_fees = player.fees.exclude(status='PAID')

    if request.method == 'POST':
        selected_fee_ids = request.POST.getlist('selected_fees')
        payment_method = request.POST.get('payment_method', 'CASH')
        payer_name = request.POST.get('payer_name', '').strip()
        reference_number = request.POST.get('reference_number', '').strip()
        transfer_date = request.POST.get('transfer_date') or None

        if not selected_fee_ids and player.initial_debt <= 0:
            messages.error(request, "Debe seleccionar al menos una deuda o mensualidad para cobrar.")
            return redirect('collect_payment', pk=player.pk)

        fees_to_pay = MonthlyFee.objects.filter(id__in=selected_fee_ids, player=player)
        total_amount = sum(fee.pending_amount for fee in fees_to_pay)

        if total_amount <= 0:
            messages.error(request, "El monto seleccionado es 0.")
            return redirect('collect_payment', pk=player.pk)

        payment = Payment.objects.create(
            player=player,
            amount=total_amount,
            payment_method=payment_method,
            payer_name=payer_name if payment_method == 'CASH' else '',
            reference_number=reference_number if payment_method == 'TRANSFER' else '',
            transfer_date=transfer_date if payment_method == 'TRANSFER' else None,
            registered_by=request.user
        )

        for fee in fees_to_pay:
            debt = fee.pending_amount
            if debt > 0:
                PaymentAllocation.objects.create(payment=payment, fee=fee, amount_applied=debt)
                fee.update_status()

        messages.success(request, f"¡Pago de {total_amount} Bs registrado con éxito! Las deudas seleccionadas han sido saldadas.")
        return redirect('pending_debts')

    return render(request, 'club/collect_payment.html', {
        'player': player,
        'pending_fees': pending_fees,
    })


@login_required
def financial_report_view(request):
    if not request.user.is_superuser and not request.user.groups.filter(name='Dueno').exists():
        messages.error(request, "No tienes permisos para ver la Rendición de Cuentas. Esta sección es exclusiva del Dueño.")
        return redirect('home')

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    payments = Payment.objects.filter(is_voided=False)
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
        
    total_filtered = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_total = payments.filter(payment_method='CASH').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    transfer_total = payments.filter(payment_method='TRANSFER').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    context = {
        'payments': payments,
        'total_filtered': total_filtered,
        'cash_total': cash_total,
        'transfer_total': transfer_total,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'club/financial_report.html', context)


@login_required
def create_fee_view(request):
    if request.method == 'POST':
        form = MonthlyFeeForm(request.POST)
        if form.is_valid():
            fee = form.save()
            messages.success(request, f"Mensualidad generada con éxito.")
            return redirect('player_detail', pk=fee.player.pk)
    else:
        form = MonthlyFeeForm()
    return render(request, 'club/fee_form.html', {'form': form})


# --- MÓDULO DE GESTIÓN DE USUARIOS (CONFIGURACIÓN / TUERCA ⚙️) ---

@login_required
def user_list_view(request):
    if not request.user.is_superuser and not request.user.groups.filter(name='Dueno').exists():
        messages.error(request, "No tienes permiso para gestionar usuarios.")
        return redirect('home')

    if request.user.is_superuser:
        users = User.objects.all().order_by('-is_superuser', 'username')
    else:
        users = User.objects.filter(groups__name='Secretaria').order_by('username')

    return render(request, 'club/user_list.html', {'users_list': users})


@login_required
def user_create_view(request):
    if not request.user.is_superuser and not request.user.groups.filter(name='Dueno').exists():
        messages.error(request, "No tienes permiso para crear usuarios.")
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        role = request.POST.get('role', 'Secretaria')

        if not request.user.is_superuser and role != 'Secretaria':
            messages.error(request, "Solo puedes crear cuentas de tipo Secretaria.")
            return redirect('user_list')

        if form.is_valid():
            new_user = form.save()
            group, _ = Group.objects.get_or_create(name=role)
            new_user.groups.add(group)
            
            if role == 'Dueno' and request.user.is_superuser:
                new_user.is_staff = True
                new_user.save()

            messages.success(request, f"Usuario '{new_user.username}' creado exitosamente con rol {role}.")
            return redirect('user_list')
    else:
        form = UserCreationForm()

    return render(request, 'club/user_form.html', {'form': form, 'title': 'Crear Nuevo Usuario'})


@login_required
def user_password_change_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "No puedes modificar la cuenta del Administrador Master.")
        return redirect('user_list')

    if not request.user.is_superuser:
        if not target_user.groups.filter(name='Secretaria').exists():
            messages.error(request, "Solo puedes cambiar contraseñas de Secretarias.")
            return redirect('user_list')

    if request.method == 'POST':
        form = SetPasswordForm(target_user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Contraseña de '{target_user.username}' actualizada con éxito.")
            return redirect('user_list')
    else:
        form = SetPasswordForm(target_user)

    return render(request, 'club/user_password.html', {'form': form, 'target_user': target_user})


@login_required
def user_delete_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    if target_user.is_superuser:
        messages.error(request, "¡Acción denegada! No se puede eliminar la cuenta Master.")
        return redirect('user_list')

    if target_user == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta en uso.")
        return redirect('user_list')

    if not request.user.is_superuser:
        if not target_user.groups.filter(name='Secretaria').exists():
            messages.error(request, "No tienes permiso para eliminar este usuario.")
            return redirect('user_list')

    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f"Usuario '{username}' eliminado correctamente.")
        return redirect('user_list')

    return render(request, 'club/user_confirm_delete.html', {'target_user': target_user})