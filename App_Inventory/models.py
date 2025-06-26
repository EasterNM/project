from django.db import models
from django.conf import settings
from App_Products.models import Product
import string
from django.db import transaction
from django.db.models import F
from django.utils import timezone

# ============================================
#  Abstract Base Models (สำหรับใช้ซ้ำ)
# ============================================

class TimeStampedModel(models.Model):
    """
    Abstract model ที่เพิ่มฟิลด์ created_at และ updated_at อัตโนมัติ
    """
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name="วันที่แก้ไขล่าสุด")

    class Meta:
        abstract = True

class AuditedModel(TimeStampedModel):
    """
    Abstract model ที่เพิ่มฟิลด์ created_by และ updated_by อัตโนมัติ
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+', # ใช้ '+' เพื่อไม่ให้ Django สร้าง backward relation ที่ไม่จำเป็น
        verbose_name="สร้างโดย"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        verbose_name="แก้ไขโดย"
    )

    class Meta:
        abstract = True


# ============================================
#  Core Inventory Models
# ============================================

class Location(TimeStampedModel):
    """โมเดลสำหรับเก็บข้อมูลตำแหน่งจัดเก็บสินค้า"""
    # Django สร้าง 'id' ให้เป็น PK อัตโนมัติ
    location_code = models.CharField(max_length=50, unique=True, verbose_name="รหัสตำแหน่ง")
    location_name = models.CharField(max_length=100, verbose_name="ชื่อตำแหน่ง")
    description = models.TextField(blank=True, null=True, verbose_name="คำอธิบาย")
    is_active = models.BooleanField(default=True, verbose_name="สถานะใช้งาน")

    class Meta:
        verbose_name = "ตำแหน่งจัดเก็บ"
        verbose_name_plural = "ตำแหน่งจัดเก็บทั้งหมด"
        ordering = ['location_code']

    def __str__(self):
        return f"{self.location_code} - {self.location_name}"

def generate_base62(num):
    """Generate Base62 string from number"""
    chars = string.digits + string.ascii_letters
    base = len(chars)
    if num == 0:
        return '0'.zfill(10)
    result = ''
    while num:
        num, remainder = divmod(num, base)
        result = chars[remainder] + result
    return result.zfill(10)

class SerialCounter(models.Model):
    """Model to keep track of serial numbers for InventoryItem"""
    counter = models.BigIntegerField(default=0)
    def __str__(self):
        return f"Serial Counter: {self.counter}"


class InventoryItem(TimeStampedModel):
    """โมเดลสำหรับเก็บข้อมูลสินค้าแต่ละชิ้นในคลัง (Serialized Inventory)"""
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'พร้อมใช้งาน'
        RESERVED = 'reserved', 'จองแล้ว'
        SOLD = 'sold', 'ขายแล้ว'
        DAMAGED = 'damaged', 'เสียหาย'
        EXPIRED = 'expired', 'หมดอายุ'

    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="สินค้า")
    serial_number = models.CharField(max_length=10, unique=True, blank=True, help_text="Base62 serial number, auto-generated")
    lot_number = models.CharField(max_length=100, blank=True, verbose_name="Lot/Batch Number")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="ตำแหน่งจัดเก็บ")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, verbose_name="สถานะ")
    
    # ข้อมูลการรับเข้า
    receipt_detail = models.ForeignKey(
        'App_Purchase.GoodsReceiptDetail',
        on_delete=models.PROTECT,
        related_name='inventory_items',
        null=True,
        blank=True,
        verbose_name="รายละเอียดการรับเข้า"
    )
    received_date = models.DateTimeField(null=True, blank=True, verbose_name="วันที่รับเข้า")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="วันที่หมดอายุ")
    
    # ข้อมูลการขาย
    sales_detail = models.ForeignKey(
        'App_OrderingProductForSale.OrderDetail',
        on_delete=models.SET_NULL, # ใช้ SET_NULL เพื่อให้ลบ Order ได้โดยไม่กระทบสต็อก
        related_name='inventory_items',
        null=True,
        blank=True,
        verbose_name="รายละเอียดการขาย"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_inventory_items',
        verbose_name="สร้างโดย"
    )

    class Meta:
        verbose_name = "สินค้าในคลัง (รายชิ้น)"
        verbose_name_plural = "สินค้าในคลัง (รายชิ้น)"
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['lot_number']),
        ]

    def save(self, *args, **kwargs):
        if not self.serial_number:
            with transaction.atomic():
                counter, _ = SerialCounter.objects.select_for_update().get_or_create(id=1)
                counter.counter = F('counter') + 1
                counter.save()
                counter.refresh_from_db()
                self.serial_number = generate_base62(counter.counter)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} (S/N: {self.serial_number})"


# ============================================
#  Inventory Activity Models
# ============================================

class LocationHistory(models.Model):
    """โมเดลสำหรับเก็บประวัติการย้ายตำแหน่งสินค้า"""
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='location_history', verbose_name="สินค้า")
    from_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='from_moves', verbose_name="จากตำแหน่ง")
    to_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='to_moves', verbose_name="ไปยังตำแหน่ง")
    move_date = models.DateTimeField(verbose_name="วันที่ย้าย")
    reason = models.TextField(blank=True, verbose_name="เหตุผล")
    moved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="ย้ายโดย")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ประวัติการย้ายตำแหน่ง"
        verbose_name_plural = "ประวัติการย้ายตำแหน่ง"
        ordering = ['-move_date']

    def __str__(self):
        return f"Move {self.inventory_item.serial_number} to {self.to_location.location_code}"


class StockCount(TimeStampedModel):
    """โมเดลสำหรับเก็บข้อมูลการตรวจนับสต็อก (Header)"""
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'กำลังดำเนินการ'
        COMPLETED = 'completed', 'เสร็จสิ้น'
        CANCELLED = 'cancelled', 'ยกเลิก'

    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="ตำแหน่งที่นับ")
    count_date = models.DateTimeField(default=timezone.now, verbose_name="วันที่ตรวจนับ")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, verbose_name="สถานะ")
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="ผู้ตรวจนับ")
    note = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")

    class Meta:
        verbose_name = "การตรวจนับสต็อก"
        verbose_name_plural = "การตรวจนับสต็อก"
        ordering = ['-count_date']

class StockCountItem(models.Model):
    """โมเดลสำหรับเก็บรายละเอียดการตรวจนับแต่ละรายการ (Detail)"""
    class Status(models.TextChoices):
        FOUND = 'found', 'พบ'
        MISSING = 'missing', 'ไม่พบ'
        EXTRA = 'extra', 'เกิน'

    stock_count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name='items', verbose_name="ชุดการตรวจนับ")
    
    # สำหรับ status 'found' และ 'missing'
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, null=True, blank=True, verbose_name="สินค้าในระบบ")
    
    # สำหรับ status 'extra'
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, verbose_name="สินค้าที่พบ")
    counted_serial_number = models.CharField(max_length=100, blank=True, help_text="Serial ที่นับเจอ (กรณี 'เกิน')")
    
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name="ผลการนับ")
    note = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")

    class Meta:
        verbose_name = "รายการตรวจนับ"
        verbose_name_plural = "รายการตรวจนับ"
        unique_together = [['stock_count', 'inventory_item']] # ป้องกันการนับ item เดิมซ้ำใน sheet เดียว

class DamagedItem(TimeStampedModel):
    """โมเดลสำหรับบันทึกข้อมูลสินค้าเสียหาย"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'รอดำเนินการ'
        REPAIRED = 'repaired', 'ซ่อมแซมแล้ว'
        WRITTEN_OFF = 'written_off', 'ตัดจำหน่าย'

    # เปลี่ยนเป็น OneToOneField และใช้เป็น Primary Key
    inventory_item = models.OneToOneField(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='damage_record',
        primary_key=True,
        verbose_name="สินค้าที่เสียหาย"
    )
    damage_date = models.DateField(verbose_name='วันที่พบความเสียหาย')
    damage_description = models.TextField(verbose_name='รายละเอียดความเสียหาย')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='สถานะ')
    
    # ข้อมูลการซ่อม/ตัดจำหน่าย
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='ค่าซ่อมแซม')
    action_date = models.DateField(null=True, blank=True, verbose_name='วันที่ดำเนินการ (ซ่อม/ตัดจำหน่าย)')
    action_note = models.TextField(null=True, blank=True, verbose_name='บันทึกการดำเนินการ')
    
    # ใช้ AuditedModel ไม่ได้เพราะ item เป็น PK แต่สามารถเพิ่ม created_by ได้
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )

    class Meta:
        verbose_name = 'รายการสินค้าเสียหาย'
        verbose_name_plural = 'รายการสินค้าเสียหาย'
        ordering = ['-damage_date']

    def __str__(self):
        return f"{self.inventory_item.serial_number} - {self.get_status_display()}"