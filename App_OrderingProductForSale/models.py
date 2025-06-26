from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum
from decimal import Decimal

# ============================================
#  Abstract & Counter Models
# ============================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    class Meta:
        abstract = True

class OrderCounter(models.Model):
    year = models.IntegerField(unique=True)
    counter = models.IntegerField(default=0)
    @classmethod
    def get_next_number(cls):
        year = timezone.now().year
        with transaction.atomic():
            counter_obj, _ = cls.objects.select_for_update().get_or_create(year=year, defaults={'counter': 0})
            counter_obj.counter = F('counter') + 1
            counter_obj.save()
            counter_obj.refresh_from_db()
            return f"SO{year}{str(counter_obj.counter).zfill(8)}"

class InvoiceCounter(models.Model):
    year = models.IntegerField(unique=True)
    counter = models.IntegerField(default=0)
    @classmethod
    def get_next_number(cls):
        year = timezone.now().year
        with transaction.atomic():
            counter_obj, _ = cls.objects.select_for_update().get_or_create(year=year, defaults={'counter': 0})
            counter_obj.counter = F('counter') + 1
            counter_obj.save()
            counter_obj.refresh_from_db()
            return f"INV{year}{str(counter_obj.counter).zfill(5)}"


# ============================================
#  Order & Picking Models
# ============================================

class OrderRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'รอดำเนินการ'
        PROCESSING = 'PROCESSING', 'กำลังดำเนินการ'
        COMPLETED = 'COMPLETED', 'เสร็จสิ้น'
        CANCELLED = 'CANCELLED', 'ยกเลิก'
    
    order_id = models.CharField(max_length=20, primary_key=True, editable=False)
    customer = models.ForeignKey('App_Customer.Customer', on_delete=models.PROTECT, verbose_name="ลูกค้า")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_orders', verbose_name="สร้างโดย")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="สถานะ")
    note = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = OrderCounter.get_next_number()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.order_id

class OrderDetail(models.Model):
    order = models.ForeignKey(OrderRequest, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey('App_Products.Product', on_delete=models.PROTECT, related_name='order_details')
    quantity = models.PositiveIntegerField(default=1, verbose_name="จำนวน")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, verbose_name="ราคาต่อหน่วย (ณ วันที่สั่ง)")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        if not self.pk: # ทำเฉพาะตอนสร้างใหม่
            # ดึงราคาปัจจุบันของสินค้ามาบันทึกไว้
            self.unit_price = self.product.get_current_price().get('A', 0) # สมมติว่าใช้ราคา A เป็นหลัก
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order.order_id} - {self.product.name}"

class PickingOrder(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'รอจัดสินค้า'
        PICKING = 'PICKING', 'กำลังจัดสินค้า'
        COMPLETED = 'COMPLETED', 'จัดสินค้าเสร็จสิ้น'
    
    order_request = models.OneToOneField(OrderRequest, on_delete=models.PROTECT, related_name='picking_order')
    picker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, verbose_name="ผู้จัด")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="สถานะ")

    def __str__(self):
        return f"Picking for {self.order_request.order_id}"

class PickingDetail(models.Model):
    picking_order = models.ForeignKey(PickingOrder, on_delete=models.CASCADE, related_name='details')
    order_detail = models.OneToOneField(OrderDetail, on_delete=models.PROTECT, related_name='picking_detail')
    picked_items = models.ManyToManyField('App_Inventory.InventoryItem', blank=True, help_text='Serial Number ของสินค้าที่ถูกจัด')

    @property
    def picked_quantity(self):
        return self.picked_items.count()

    @property
    def is_completed(self):
        return self.picked_quantity >= self.order_detail.quantity

    def __str__(self):
        return f"Picking for {self.order_detail}"


# ============================================
#  Invoice Model
# ============================================
class Invoice(TimeStampedModel):
    class InvoiceType(models.TextChoices):
        REGULAR = 'REGULAR', 'ใบเสร็จรับเงิน'
        TAX = 'TAX', 'ใบกำกับภาษี'
    
    order_request = models.OneToOneField(OrderRequest, on_delete=models.PROTECT, related_name='invoice')
    invoice_number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    invoice_type = models.CharField(max_length=10, choices=InvoiceType.choices, default=InvoiceType.TAX)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, verbose_name="ยอดรวมก่อนส่วนลด")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="ส่วนลด (บาท)")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, verbose_name="ยอดหลังหักส่วนลด")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=7.00, verbose_name="อัตราภาษี (%)")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, verbose_name="ภาษีมูลค่าเพิ่ม")
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, verbose_name="ยอดรวมสุทธิ")
    
    def calculate_totals(self):
        """คำนวณยอดต่างๆ จาก Order Details"""
        # 1. คำนวณยอดรวมจากทุกรายการในออเดอร์
        order_total = self.order_request.details.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        self.total_amount = order_total
        
        # 2. คำนวณยอดหลังหักส่วนลด
        self.subtotal = self.total_amount - self.discount_amount
        
        # 3. คำนวณ VAT
        self.vat_amount = self.subtotal * (self.vat_rate / Decimal('100'))
        
        # 4. คำนวณยอดรวมสุทธิ
        self.grand_total = self.subtotal + self.vat_amount

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = InvoiceCounter.get_next_number()
        # คำนวณยอดทุกครั้งที่บันทึก
        self.calculate_totals()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number