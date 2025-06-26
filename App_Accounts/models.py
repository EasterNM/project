from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Department Model (ไม่เปลี่ยนแปลง)
class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name="ชื่อแผนก",
                            help_text="ระบุชื่อแผนกให้ชัดเจน เช่น 'ฝ่ายบุคคล', 'ฝ่ายบัญชี'")
    manager = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_department',
        verbose_name='หัวหน้าแผนก'
    )
    description = models.TextField(verbose_name="คำอธิบายแผนก",
                                   help_text="อธิบายรายละเอียดของแผนก หน้าที่ความรับผิดชอบ",
                                   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่แก้ไขล่าสุด")

    class Meta:
        verbose_name = "แผนก"
        verbose_name_plural = "แผนก"
        ordering = ['name']

    def __str__(self):
        return self.name

# Position Model (ปรับปรุง created_at)
class Position(models.Model):
    name = models.CharField(max_length=100, verbose_name="ชื่อตำแหน่ง",
                            help_text="ระบุชื่อตำแหน่งงานให้ชัดเจน เช่น 'ผู้จัดการฝ่ายบุคคล', 'พนักงานบัญชี'")
    department = models.ForeignKey(Department, on_delete=models.CASCADE,
                                   verbose_name="แผนก",
                                   help_text="เลือกแผนกที่ตำแหน่งงานนี้สังกัด")
    description = models.TextField(verbose_name="คำอธิบายตำแหน่ง",
                                   help_text="อธิบายรายละเอียดของตำแหน่งงาน หน้าที่ความรับผิดชอบ",
                                   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่แก้ไขล่าสุด")

    class Meta:
        verbose_name = "ตำแหน่ง"
        verbose_name_plural = "ตำแหน่ง"
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} ({self.department.name})"

# CustomUser Model (ปรับปรุงหลายจุด)
class CustomUser(AbstractUser):
    FULL_TIME = 'FT'
    PART_TIME = 'PT'
    CONTRACT = 'CT'
    EMPLOYMENT_TYPE_CHOICES = [
        (FULL_TIME, 'Full-time'),
        (PART_TIME, 'Part-time'),
        (CONTRACT, 'Contract'),
    ]

    # ไม่ต้องประกาศ first_name, last_name ใหม่ เพราะมีใน AbstractUser แล้ว
    # ฟิลด์จาก AbstractUser ที่ใช้ได้เลย: username, first_name, last_name, email, is_staff, is_active, date_joined

    # Personal Information
    employee_id = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="รหัสพนักงาน")
    date_of_birth = models.DateField(verbose_name='วันเดือนปีเกิด', help_text='คลิกที่ไอคอนปฏิทินเพื่อเลือกวันที่', null=True, blank=True)
    gender = models.CharField(max_length=10, verbose_name='เพศ', help_text='ระบุเพศของพนักงาน', null=True, blank=True)
    nationality = models.CharField(max_length=50, verbose_name='สัญชาติ', help_text='ระบุสัญชาติของพนักงาน', null=True, blank=True)
    phone_number = models.CharField(max_length=15, verbose_name='เบอร์โทรศัพท์', help_text='ระบุเบอร์โทรศัพท์ที่ติดต่อได้', null=True, blank=True)
    address = models.TextField(verbose_name='ที่อยู่', help_text='ระบุที่อยู่ปัจจุบันที่สามารถติดต่อได้', null=True, blank=True)
    emergency_contact = models.CharField(max_length=15, verbose_name='เบอร์ติดต่อฉุกเฉิน', help_text='ระบุเบอร์โทรศัพท์สำหรับติดต่อในกรณีฉุกเฉิน', null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True, verbose_name='รูปโปรไฟล์')
    
    # Employment Information
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ตำแหน่ง")
    # department ถูกลบออกเพื่อลดความซ้ำซ้อน
    date_of_joining = models.DateField(verbose_name='วันที่เริ่มงาน', help_text='คลิกที่ไอคอนปฏิทินเพื่อเลือกวันที่เริ่มงาน', null=True, blank=True)
    employment_type = models.CharField(max_length=2, choices=EMPLOYMENT_TYPE_CHOICES, default=FULL_TIME, verbose_name='ประเภทการจ้างงาน', help_text='เลือกประเภทการจ้างงานของพนักงาน')
    
    # แก้ไข manager_id เป็น ForeignKey
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates', verbose_name='หัวหน้างาน')
    
    # Security
    login_attempts = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'พนักงาน'
        verbose_name_plural = 'พนักงาน'

    # สร้าง property เพื่อให้เข้าถึง department ได้ง่าย
    @property
    def department(self):
        if self.position and self.position.department:
            return self.position.department
        return None

    def __str__(self):
        return self.get_full_name() or self.username