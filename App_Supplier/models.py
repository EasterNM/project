from django.db import models
from django.conf import settings
from django.utils import timezone


# ============================================
#  Abstract & Counter Models
# ============================================

class TimeStampedModel(models.Model):
    """ Abstract model สำหรับเก็บวันที่สร้างและแก้ไข """
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name="วันที่แก้ไขล่าสุด")
    class Meta:
        abstract = True

# (Optional but recommended) Counter for user-friendly supplier codes
# class SupplierCounter(models.Model): ...

# ============================================
#  Supplier Models
# ============================================

class Supplier(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    class Category(models.TextChoices):
        MANUFACTURER = 'manufacturer', 'ผู้ผลิต'
        DISTRIBUTOR = 'distributor', 'ผู้จัดจำหน่าย'
        SERVICE = 'service', 'ผู้ให้บริการ'

    # ข้อมูลทั่วไป
    company_name = models.CharField(max_length=200, verbose_name="ชื่อบริษัท")
    supplier_code = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="รหัสซัพพลายเออร์")
    contact_name = models.CharField(max_length=100, default="", verbose_name="ชื่อผู้ติดต่อ")
    contact_title = models.CharField(max_length=100, blank=True, verbose_name="ตำแหน่งผู้ติดต่อ")
    email = models.EmailField(unique=True, default="example@example.com", verbose_name="อีเมล")
    phone_number = models.CharField(max_length=30, default="", verbose_name="เบอร์โทรศัพท์")
    fax_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="เบอร์แฟกซ์")
    website = models.URLField(blank=True, null=True, verbose_name="เว็บไซต์")

    # ข้อมูลที่อยู่
    address = models.TextField(default="", verbose_name="ที่อยู่")
    city = models.CharField(max_length=100, default="กรุงเทพฯ", verbose_name="เมือง/เขต")
    state = models.CharField(max_length=100, default="กรุงเทพมหานคร", verbose_name="จังหวัด")
    postal_code = models.CharField(max_length=20, default="10000", verbose_name="รหัสไปรษณีย์")
    country = models.CharField(max_length=100, default="ไทย", verbose_name="ประเทศ")

    # ข้อมูลการเงิน
    bank_account_number = models.CharField(max_length=50, blank=True, default="", verbose_name="เลขที่บัญชีธนาคาร")
    bank_name = models.CharField(max_length=100, blank=True, default="", verbose_name="ชื่อธนาคาร")
    payment_terms = models.CharField(max_length=200, blank=True, default="", verbose_name="เงื่อนไขการชำระเงิน")
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="วงเงินเครดิต")
    tax_id = models.CharField(max_length=50, blank=True, default="", verbose_name="เลขประจำตัวผู้เสียภาษี")

    # ข้อมูลเพิ่มเติม
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.DISTRIBUTOR, verbose_name="ประเภท")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name="สถานะ")
    
    # เพิ่ม history จาก django-simple-history

    class Meta:
        verbose_name = 'ซัพพลายเออร์'
        verbose_name_plural = 'ซัพพลายเออร์'
        ordering = ['company_name']

    def __str__(self):
        return self.company_name

class ContactHistory(TimeStampedModel):
    class ContactType(models.TextChoices):
        PHONE = 'phone', 'โทรศัพท์'
        EMAIL = 'email', 'อีเมล'
        MEETING = 'meeting', 'ประชุม'
        OTHER = 'other', 'อื่นๆ'

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='contact_histories', verbose_name="ซัพพลายเออร์")
    contact_date = models.DateTimeField(default=timezone.now, verbose_name="วันที่ติดต่อ")
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, verbose_name="ประเภทการติดต่อ")
    notes = models.TextField(verbose_name="บันทึก")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="บันทึกโดย"
    )


    class Meta:
        ordering = ['-contact_date']
        verbose_name = "ประวัติการติดต่อ"
        verbose_name_plural = "ประวัติการติดต่อ"

    def __str__(self):
        return f"{self.supplier.company_name} - {self.get_contact_type_display()} on {self.contact_date.strftime('%Y-%m-%d')}"

# ไม่จำเป็นต้องใช้ SupplierChangeLog และ ContactHistoryChangeLog อีกต่อไป
# สามารถลบ 2 โมเดลนี้ทิ้งได้เลย