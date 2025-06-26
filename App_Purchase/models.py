from django.db import models
from django.db.models import Sum, F
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

from App_Supplier.models import Supplier
from App_Products.models import Product

# ============================================
#  Abstract & Counter Models
# ============================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    class Meta:
        abstract = True

class POCounter(models.Model):
    counter = models.IntegerField(default=0)
    @classmethod
    def get_next_number(cls):
        with transaction.atomic():
            counter_obj = cls.objects.select_for_update().get_or_create(id=1)[0]
            counter_obj.counter = F('counter') + 1
            counter_obj.save()
            counter_obj.refresh_from_db()
            return f"PO{str(counter_obj.counter).zfill(7)}"

class PRCounter(models.Model):
    counter = models.IntegerField(default=0)
    @classmethod
    def get_next_number(cls):
        with transaction.atomic():
            counter_obj = cls.objects.select_for_update().get_or_create(id=1)[0]
            counter_obj.counter = F('counter') + 1
            counter_obj.save()
            counter_obj.refresh_from_db()
            return f"PR{str(counter_obj.counter).zfill(7)}"


# ============================================
#  Purchase Requisition (PR) Models
# ============================================

class PurchaseRequisition(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'ฉบับร่าง'
        PENDING = 'pending', 'รออนุมัติ'
        APPROVED = 'approved', 'อนุมัติแล้ว'
        REJECTED = 'rejected', 'ไม่อนุมัติ'
        CANCELLED = 'cancelled', 'ยกเลิก'
        CONVERTED = 'converted', 'แปลงเป็น PO แล้ว'

    pr_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name="เลขที่ใบขอซื้อ")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchase_requisitions', verbose_name="ผู้ขอซื้อ")
    department = models.CharField(max_length=100, verbose_name="แผนก")
    request_date = models.DateTimeField(default=timezone.now, verbose_name="วันที่ขอซื้อ")
    required_date = models.DateField(verbose_name="วันที่ต้องการใช้งาน")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="สถานะ")
    remarks = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")

    def save(self, *args, **kwargs):
        if not self.pr_number:
            self.pr_number = PRCounter.get_next_number()
        super().save(*args, **kwargs)

    @property
    def total_quantity(self):
        return self.details.aggregate(total=Sum('quantity'))['total'] or 0

    def __str__(self):
        return self.pr_number

class PurchaseRequisitionDetail(models.Model):
    purchase_requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="สินค้า")
    quantity = models.PositiveIntegerField(verbose_name="จำนวน")
    description = models.TextField(blank=True, null=True, verbose_name="รายละเอียดเพิ่มเติม")

    def __str__(self):
        return f"{self.purchase_requisition.pr_number} - {self.product.name}"


# ============================================
#  Purchase Order (PO) Models
# ============================================

class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'ร่าง'
        PENDING = 'pending_approval', 'รออนุมัติ'
        APPROVED = 'approved', 'อนุมัติแล้ว (รอรับของ)'
        PARTIALLY_RECEIVED = 'partially_received', 'รับของบางส่วนแล้ว'
        FULLY_RECEIVED = 'fully_received', 'รับของครบแล้ว'
        REJECTED = 'rejected', 'ไม่อนุมัติ'
        CANCELLED = 'cancelled', 'ยกเลิก'

    po_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="เลขที่ใบสั่งซื้อ")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders', verbose_name="ผู้ขาย")
    purchase_requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders', verbose_name="อ้างอิงใบขอซื้อ")
    order_date = models.DateTimeField(default=timezone.now, verbose_name="วันที่สั่งซื้อ")
    expected_delivery_date = models.DateField(verbose_name="วันที่คาดว่าจะได้รับ")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="สถานะ")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_purchase_orders', verbose_name="สร้างโดย")

    @property
    def total_amount(self):
        return self.details.aggregate(total=Sum('subtotal'))['total'] or 0

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = POCounter.get_next_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number

class PurchaseOrderDetail(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="สินค้า")
    quantity = models.PositiveIntegerField(verbose_name="จำนวนสั่งซื้อ")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อหน่วย")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ยอดรวม")

    def save(self, *args, **kwargs):
        try:
            self.quantity = int(self.quantity)
            self.unit_price = Decimal(str(self.unit_price))
            self.subtotal = Decimal(str(self.quantity)) * self.unit_price
        except (TypeError, ValueError, InvalidOperation) as e:
            raise ValidationError(f"ไม่สามารถคำนวณยอดรวมได้: {str(e)}")
        super().save(*args, **kwargs)
        # หมายเหตุ: การอัปเดต total_amount ของ PO ควรทำผ่าน signal หรือ property

    @property
    def received_quantity(self):
        return self.receipt_details.aggregate(total=Sum('quantity_received'))['total'] or 0

    @property
    def remaining_quantity(self):
        return self.quantity - self.received_quantity

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.name}"


# ============================================
#  Goods Receipt (GR) Models
# ============================================

class GoodsReceipt(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='goods_receipts', verbose_name="ใบสั่งซื้อ")
    receipt_date = models.DateTimeField(default=timezone.now, verbose_name="วันที่รับของ")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="ผู้รับของ")
    notes = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")

    @property
    def total_quantity_received(self):
        return self.details.aggregate(total=Sum('quantity_received'))['total'] or 0

    def __str__(self):
        return f"GR-{self.id} (PO: {self.purchase_order.po_number})"

class GoodsReceiptDetail(models.Model):
    class Condition(models.TextChoices):
        GOOD = 'good', 'สภาพดี'
        DAMAGED = 'damaged', 'เสียหาย'
        INCORRECT = 'incorrect', 'ไม่ตรงตามสั่ง'

    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='details')
    purchase_order_detail = models.ForeignKey(PurchaseOrderDetail, on_delete=models.PROTECT, related_name='receipt_details')
    quantity_received = models.PositiveIntegerField(verbose_name="จำนวนที่รับ")
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD, verbose_name="สภาพสินค้า")
    notes = models.TextField(blank=True, null=True)

    @property
    def product(self):
        return self.purchase_order_detail.product

    def clean(self):
        super().clean()
        # ตรวจสอบว่ารับของเกินจำนวนที่ยังค้างรับหรือไม่
        po_detail = self.purchase_order_detail
        remaining = po_detail.quantity - po_detail.received_quantity
        
        if remaining < self.quantity_received:
            raise ValidationError({
                'quantity_received': f'จำนวนที่รับ ({self.quantity_received}) เกินกว่าจำนวนที่คงเหลือ ({remaining})'
            })