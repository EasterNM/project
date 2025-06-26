from django.db import models, transaction
from django.utils import timezone
from django.db.models import F
from django.core.exceptions import ValidationError
# from App_Supplier.models import Supplier # สมมติว่ามีการ import Supplier มาแล้ว

# ============================================
#  Category, Brand Models
# ============================================

class Category(models.Model):
    # ไม่ต้องประกาศ id เพราะ Django สร้างให้แล้ว
    name = models.CharField(max_length=100, verbose_name="ชื่อหมวดหมู่")
    description = models.TextField(null=True, blank=True, verbose_name="คำอธิบาย")
    category_code = models.CharField(
        max_length=3,
        unique=True,
        help_text="รหัสหมวดหมู่ 3 หลัก",
        default='000',
        verbose_name="รหัสหมวดหมู่"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "หมวดหมู่สินค้า"
        verbose_name_plural = "หมวดหมู่สินค้า"

class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name="ชื่อแบรนด์")
    description = models.TextField(null=True, blank=True, verbose_name="คำอธิบาย")
    brand_code = models.CharField(
        max_length=4,
        unique=True,
        help_text="รหัสแบรนด์ 4 หลัก",
        default='0000',
        verbose_name="รหัสแบรนด์"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "แบรนด์สินค้า"
        verbose_name_plural = "แบรนด์สินค้า"

# ============================================
#  Product Model
# ============================================

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU", blank=True,
                         help_text="รหัสสินค้าเฉพาะ จะถูกสร้างอัตโนมัติหากไม่ระบุ (รูปแบบ: หมวดหมู่-แบรนด์-ปี-ลำดับ)")
    name = models.CharField(max_length=255, verbose_name="ชื่อสินค้า")
    description = models.TextField(null=True, blank=True, verbose_name="คำอธิบาย")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="หมวดหมู่")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="แบรนด์")
    unit = models.CharField(max_length=50, verbose_name="หน่วยนับ")
    
    # --- ราคามาตรฐานของสินค้า ---
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคาทุน', default=0)
    price_a = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคาขาย A', default=0, help_text='ราคาขายสำหรับลูกค้าทั่วไป')
    price_aa = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคาขาย AA', default=0, help_text='ราคาขายสำหรับลูกค้าประจำ')
    price_aaa = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคาขาย AAA', default=0, help_text='ราคาขายสำหรับลูกค้า VIP')
    
    # --- ข้อมูลสต็อก ---
    reorder_point = models.PositiveIntegerField(verbose_name='จุดสั่งซื้อ (Reorder Point)', default=0, help_text='จำนวนสินค้าคงเหลือที่ควรทำการสั่งซื้อเพิ่ม')
    reorder_quantity = models.PositiveIntegerField(verbose_name='จำนวนสั่งซื้อที่แนะนำ', default=0, help_text='จำนวนที่ควรสั่งซื้อเมื่อถึงจุดสั่งซื้อ')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่อัปเดต")

    class Meta:
        verbose_name = "สินค้า"
        verbose_name_plural = "สินค้าทั้งหมด"
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
        ]

    def save(self, *args, **kwargs):
        # Generate SKU only if it's a new product and no SKU is provided
        if not self.pk and not self.sku:
            try:
                with transaction.atomic():
                    year = timezone.now().year
                    counter, _ = SKUCounter.objects.select_for_update().get_or_create(year=year, defaults={'counter': 0})
                    
                    # Get category and brand codes before incrementing counter to ensure consistency
                    category_code = '000'
                    if self.category_id:
                        try:
                            category = Category.objects.get(id=self.category_id)
                            category_code = category.category_code
                        except Category.DoesNotExist:
                            pass
                    
                    brand_code = '0000'
                    if self.brand_id:
                        try:
                            brand = Brand.objects.get(id=self.brand_id)
                            brand_code = brand.brand_code
                        except Brand.DoesNotExist:
                            pass
                    
                    # Try up to 3 times to generate a unique SKU
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        # Increment counter
                        counter.counter = F('counter') + 1
                        counter.save()
                        counter.refresh_from_db()
                        
                        running_number = str(counter.counter).zfill(6)
                        generated_sku = f"{category_code}-{brand_code}-{year}-{running_number}"
                        
                        # Check if this SKU already exists
                        if not Product.objects.filter(sku=generated_sku).exists():
                            self.sku = generated_sku
                            break
                    
                    # If we couldn't generate a unique SKU after max attempts, use a timestamp suffix
                    if not self.sku:
                        timestamp = int(timezone.now().timestamp())
                        self.sku = f"{category_code}-{brand_code}-{year}-{running_number}-{timestamp}"
            except Exception as e:
                # If there's any error in SKU generation, create a fallback SKU
                timestamp = int(timezone.now().timestamp())
                self.sku = f"AUTO-{timestamp}"
        
        # Call the parent save method to save the product
        super().save(*args, **kwargs)

    def clean(self):
        # ตรวจสอบว่าราคาขายต้องไม่ต่ำกว่าราคาทุน
        if self.price_a < self.cost_price:
            raise ValidationError({'price_a': 'ราคาขาย A ต้องไม่ต่ำกว่าราคาทุน'})
        if self.price_aa < self.cost_price:
            raise ValidationError({'price_aa': 'ราคาขาย AA ต้องไม่ต่ำกว่าราคาทุน'})
        if self.price_aaa < self.cost_price:
            raise ValidationError({'price_aaa': 'ราคาขาย AAA ต้องไม่ต่ำกว่าราคาทุน'})
        
        # ตรวจสอบลำดับของราคา
        if not (self.price_a >= self.price_aa >= self.price_aaa):
            raise ValidationError('ลำดับราคาไม่ถูกต้อง (ต้องเป็น A >= AA >= AAA)')

    def get_current_price(self):
        """ดึงราคาปัจจุบัน โดยตรวจสอบราคาพิเศษก่อน ถ้าไม่มีให้ใช้ราคามาตรฐาน"""
        now = timezone.now().date()
        # ค้นหาราคาพิเศษที่มีผล ณ ปัจจุบัน (related_name='prices' มาจาก ForeignKey ใน Pricing model)
        special_price = self.prices.filter(
            effective_date__lte=now,
            end_date__gte=now
        ).order_by('-effective_date').first() # เอาอันล่าสุดกรณีมีซ้อนกัน

        if special_price:
            return {
                'source': 'special',
                'A': special_price.price_a,
                'AA': special_price.price_aa,
                'AAA': special_price.price_aaa,
                'effective_date': special_price.effective_date,
                'end_date': special_price.end_date,
            }
        
        # ถ้าไม่มีราคาพิเศษ ใช้ราคาปกติจาก Product
        return {
            'source': 'standard',
            'A': self.price_a,
            'AA': self.price_aa,
            'AAA': self.price_aaa
        }
    
    @property
    def profit_margin_a(self):
        """คำนวณกำไรขั้นต้นสำหรับราคา A (%)"""
        if self.cost_price and self.price_a and self.price_a > 0:
            return ((self.price_a - self.cost_price) / self.price_a) * 100
        return 0

    # ... สามารถเพิ่ม property สำหรับ profit_margin_aa และ profit_margin_aaa ได้ในลักษณะเดียวกัน ...

    def __str__(self):
        return f"{self.name} ({self.sku})"

# ============================================
#  Pricing Model (สำหรับราคาโปรโมชั่น/ตามช่วงเวลา)
# ============================================

class Pricing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices', verbose_name="สินค้า")
    price_a = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคา A')
    price_aa = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคา AA')
    price_aaa = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคา AAA')
    effective_date = models.DateField(verbose_name='วันที่เริ่มต้น')
    end_date = models.DateField(verbose_name='วันที่สิ้นสุด')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ราคาพิเศษ'
        verbose_name_plural = 'ราคาพิเศษ'
        ordering = ['-effective_date']

    def clean(self):
        if self.end_date and self.effective_date > self.end_date:
            raise ValidationError({'end_date': 'วันที่สิ้นสุดต้องมาหลังหรือวันเดียวกับวันที่เริ่มต้น'})
        
        # ตรวจสอบว่าช่วงเวลาไม่ทับซ้อนกับราคาพิเศษอื่นของสินค้าตัวเดียวกัน
        overlapping_prices = Pricing.objects.filter(
            product=self.product,
            effective_date__lte=self.end_date,
            end_date__gte=self.effective_date
        ).exclude(pk=self.pk) # ไม่นับตัวเอง
        
        if overlapping_prices.exists():
            raise ValidationError('ช่วงเวลาของราคานี้ทับซ้อนกับราคาพิเศษที่มีอยู่แล้ว')

    def __str__(self):
        return f"ราคาพิเศษสำหรับ {self.product.name} ({self.effective_date} - {self.end_date})"

# ============================================
#  Other Supporting Models
# ============================================

class ProductSupplier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers', verbose_name="สินค้า")
    supplier = models.ForeignKey('App_Supplier.Supplier', on_delete=models.CASCADE, related_name='products', verbose_name="ซัพพลายเออร์")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='ราคาต่อหน่วยจากซัพพลายเออร์')
    minimum_order_quantity = models.PositiveIntegerField(default=1, verbose_name='จำนวนสั่งซื้อขั้นต่ำ')
    is_primary_supplier = models.BooleanField(default=False, verbose_name='ซัพพลายเออร์หลัก')

    class Meta:
        unique_together = ['product', 'supplier']
        verbose_name = 'ซัพพลายเออร์ของสินค้า'
        verbose_name_plural = 'ซัพพลายเออร์ของสินค้า'

    def save(self, *args, **kwargs):
        # ถ้าตั้งอันนี้เป็น primary ให้ยกเลิกอันอื่นของ product เดียวกัน
        if self.is_primary_supplier:
            with transaction.atomic():
                ProductSupplier.objects.filter(product=self.product, is_primary_supplier=True).exclude(pk=self.pk).update(is_primary_supplier=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.supplier.company_name}"


class SKUCounter(models.Model):
    year = models.IntegerField(unique=True)
    counter = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "ตัวนับ SKU"
        verbose_name_plural = "ตัวนับ SKU"
        
    def __str__(self):
        return f"SKU Counter {self.year}: {self.counter}"