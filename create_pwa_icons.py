#!/usr/bin/env python3
"""
สร้างไอคอน PNG สำหรับ PWA
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    # สร้างภาพ
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # วาดพื้นหลังแบบ gradient (สีเดียวแทน)
    gradient_color = (102, 126, 234)  # สีฟ้า indigo
    draw.ellipse([0, 0, size, size], fill=gradient_color)
    
    # วาดตัวอักษร "S"
    try:
        # ลองใช้ font ที่มีในระบบ
        font_size = int(size * 0.6)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        # ถ้าไม่มี font ใช้ default
        font = ImageFont.load_default()
    
    # คำนวณตำแหน่งตัวอักษร
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10  # เลื่อนขึ้นเล็กน้อย
    
    # วาดตัวอักษร
    draw.text((x, y), text, fill='white', font=font)
    
    # บันทึกไฟล์
    img.save(output_path, 'PNG')
    print(f"สร้างไอคอน {output_path} สำเร็จ!")

if __name__ == "__main__":
    # โฟลเดอร์ไอคอน
    icon_dir = "/home/nithiwit/Documents/project/static/images/icons"
    
    # ขนาดไอคอนที่ต้องการ
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # สร้างไอคอนทุกขนาด
    for size in sizes:
        output_path = os.path.join(icon_dir, f"icon-{size}x{size}.png")
        create_icon(size, output_path)
    
    print("สร้างไอคอน PWA ทั้งหมดเสร็จแล้ว!")
