from decimal import Decimal
from datetime import date
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction


class FeePlan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del Plan (Ej: Estándar, Becado)")
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Importe (Bs)"
    )

    class Meta:
        verbose_name = "Plan de Mensualidad"
        verbose_name_plural = "Planes de Mensualidad"

    def __str__(self):
        return f"{self.name} ({self.amount} Bs)"


class Player(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido")
    ci = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="C.I.")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono personal")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono padres/tutor")
    blood_type = models.CharField(max_length=5, blank=True, verbose_name="Tipo de sangre")
    address = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    email = models.EmailField(blank=True, verbose_name="Correo electrónico")
    
    photo = models.ImageField(upload_to='players/', blank=True, null=True, verbose_name="Fotografía")
    
    fee_plan = models.ForeignKey(
        FeePlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Plan de Mensualidad"
    )
    custom_monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('150.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="O personalizar tarifa (Bs)"
    )
    
    registration_date = models.DateField(default=date.today, verbose_name="Fecha de ingreso / Inicio de cobro")
    billing_day = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name="Día de cobro mensual (1 al 31)"
    )
    initial_debt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Deuda previa acumulada (Bs)"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    def save(self, *args, **kwargs):
        if not self.pk and self.registration_date:
            self.billing_day = self.registration_date.day
        super().save(*args, **kwargs)

    @property
    def get_monthly_amount(self):
        if self.fee_plan:
            return self.fee_plan.amount
        return self.custom_monthly_fee

    @property
    def total_pending_debt(self):
        pending_fees = sum(fee.pending_amount for fee in self.fees.exclude(status='PAID'))
        return pending_fees + self.initial_debt


class MonthlyFee(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PARTIAL', 'Parcialmente pagada'),
        ('PAID', 'Pagada'),
        ('OVERDUE', 'Vencida'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='fees', verbose_name="Alumno")
    year = models.PositiveIntegerField(verbose_name="Año")
    month = models.PositiveIntegerField(verbose_name="Mes (1-12)")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Importe (Bs)")
    due_date = models.DateField(verbose_name="Vencimiento")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensualidad"
        verbose_name_plural = "Mensualidades"
        ordering = ['year', 'month']

    @property
    def paid_amount(self):
        total = self.allocations.filter(payment__is_voided=False).aggregate(sum_amount=models.Sum('amount_applied'))['sum_amount']
        return total or Decimal('0.00')

    @property
    def pending_amount(self):
        return self.amount - self.paid_amount

    def update_status(self):
        paid = self.paid_amount
        if paid >= self.amount:
            self.status = 'PAID'
        elif paid > Decimal('0.00'):
            self.status = 'PARTIAL'
        else:
            self.status = 'PENDING'
        self.save(update_fields=['status'])


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Efectivo'),
        ('TRANSFER', 'QR / Transferencia bancaria'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='payments', verbose_name="Alumno")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='CASH')
    
    payer_name = models.CharField(max_length=150, blank=True, verbose_name="Quién entregó el dinero (Efectivo)")
    reference_number = models.CharField(max_length=100, blank=True, verbose_name="Código de Transferencia / QR")
    transfer_date = models.DateField(blank=True, null=True, verbose_name="Fecha de transferencia")
    
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    is_voided = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-payment_date']


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    fee = models.ForeignKey(MonthlyFee, on_delete=models.CASCADE, related_name='allocations')
    amount_applied = models.DecimalField(max_digits=10, decimal_places=2)