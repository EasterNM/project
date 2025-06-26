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


# ============================================
#  Customer Models
# ============================================

class Customer(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'ใช้งาน'
        INACTIVE = 'inactive', 'หยุดใช้งาน'
        SUSPENDED = 'suspended', 'ระงับการใช้งาน'

    class CustomerType(models.TextChoices):
        INDIVIDUAL = 'individual', 'บุคคลธรรมดา'
        COMPANY = 'company', 'นิติบุคคล'
    
    class PriceTier(models.TextChoices):
        A = 'A', 'ราคา A'
        AA = 'AA', 'ราคา AA'
        AAA = 'AAA', 'ราคา AAA'
    
    # ข้อมูลทั่วไป
    name = models.CharField(max_length=200, verbose_name="ชื่อลูกค้า/บริษัท")
    customer_code = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="รหัสลูกค้า")
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.INDIVIDUAL, verbose_name="ประเภทลูกค้า")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="สถานะ")
    
    # ข้อมูลผู้ติดต่อ
    contact_name = models.CharField(max_length=100, default="", verbose_name="ชื่อผู้ติดต่อ")
    contact_title = models.CharField(max_length=50, blank=True, null=True, verbose_name="ตำแหน่ง")
    email = models.EmailField(blank=True, null=True, verbose_name="อีเมล")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="เบอร์โทรศัพท์")
    fax_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="เบอร์แฟกซ์")
    website = models.URLField(blank=True, null=True, verbose_name="เว็บไซต์")
    
    # ข้อมูลที่อยู่
    address = models.TextField(blank=True, null=True, verbose_name="ที่อยู่")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="เมือง/อำเภอ")
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name="จังหวัด")
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="รหัสไปรษณีย์")
    country = models.CharField(max_length=100, default="ไทย", verbose_name="ประเทศ")
    
    # ข้อมูลการเงิน
    tax_id = models.CharField(max_length=13, blank=True, null=True, verbose_name="เลขประจำตัวผู้เสียภาษี")
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="ชื่อธนาคาร")
    bank_account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="เลขที่บัญชี")
    price_tier = models.CharField(max_length=3, choices=PriceTier.choices, default=PriceTier.A, verbose_name="ระดับราคา")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="วงเงินเครดิต")
    payment_terms = models.CharField(max_length=100, blank=True, null=True, verbose_name="เงื่อนไขการชำระเงิน")
    credit_term = models.IntegerField(default=0, verbose_name="เครดิตเทอม (วัน)")

    # ข้อมูลเพิ่มเติม
    notes = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")
    
    def save(self, *args, **kwargs):
        if not self.customer_code:
            # สร้างรหัสลูกค้าอัตโนมัติ
            last_customer = Customer.objects.filter(customer_code__startswith='CUST').order_by('customer_code').last()
            if last_customer and last_customer.customer_code:
                try:
                    last_number = int(last_customer.customer_code.replace('CUST', ''))
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            self.customer_code = f'CUST{new_number:04d}'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.customer_code})"
    
    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
    
    def get_total_orders(self):
        """ได้จำนวนออเดอร์ทั้งหมด"""
        try:
            from App_OrderingProductForSale.models import Order
            return Order.objects.filter(customer=self).count()
        except ImportError:
            return 0
    
    def get_total_order_amount(self):
        """ได้ยอดขายรวม"""
        try:
            from App_OrderingProductForSale.models import Order
            from django.db.models import Sum
            result = Order.objects.filter(customer=self).aggregate(
                total=Sum('total_amount')
            )
            return result['total'] or 0
        except ImportError:
            return 0
    
    class Meta:
        verbose_name = "ลูกค้า"
        verbose_name_plural = "ลูกค้า"
        ordering = ['name']


class CustomerContactHistory(TimeStampedModel):
    """ประวัติการติดต่อกับลูกค้า"""
    
    class ContactType(models.TextChoices):
        PHONE = 'phone', 'โทรศัพท์'
        EMAIL = 'email', 'อีเมล'
        MEETING = 'meeting', 'ประชุม'
        VISIT = 'visit', 'เยี่ยมชม'
        OTHER = 'other', 'อื่นๆ'
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contact_histories', verbose_name="ลูกค้า")
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, verbose_name="ประเภทการติดต่อ")
    contact_date = models.DateTimeField(verbose_name="วันที่ติดต่อ")
    subject = models.CharField(max_length=200, verbose_name="หัวข้อ")
    description = models.TextField(verbose_name="รายละเอียด")
    contacted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="ผู้ติดต่อ"
    )
    
    def __str__(self):
        return f"{self.customer.name} - {self.subject}"
    
    class Meta:
        verbose_name = "ประวัติการติดต่อลูกค้า"
        verbose_name_plural = "ประวัติการติดต่อลูกค้า"
        ordering = ['-contact_date']
