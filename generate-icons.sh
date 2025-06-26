#!/bin/bash

# สร้างไอคอน PWA แบบง่ายๆ ด้วย ImageMagick (ถ้ามี)
# หรือคุณสามารถใช้เครื่องมือออนไลน์แทนได้

ICON_DIR="/home/nithiwit/Documents/project/static/images/icons"

# สร้างไอคอน SVG เป็น PNG ถ้ามี ImageMagick
if command -v convert &> /dev/null; then
    echo "สร้างไอคอน PNG จาก SVG..."
    
    # สร้างไอคอนขนาดต่างๆ
    convert -background none -size 72x72 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-72x72.png"
    convert -background none -size 96x96 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-96x96.png"
    convert -background none -size 128x128 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-128x128.png"
    convert -background none -size 144x144 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-144x144.png"
    convert -background none -size 152x152 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-152x152.png"
    convert -background none -size 192x192 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-192x192.png"
    convert -background none -size 384x384 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-384x384.png"
    convert -background none -size 512x512 "${ICON_DIR}/icon-512x512.svg" "${ICON_DIR}/icon-512x512.png"
    
    echo "สร้างไอคอนสำเร็จ!"
else
    echo "ไม่พบ ImageMagick กรุณาติดตั้งหรือสร้างไอคอนด้วยวิธีอื่น"
    echo "สามารถใช้เครื่องมือออนไลน์เช่น:"
    echo "- https://www.pwabuilder.com/"
    echo "- https://realfavicongenerator.net/"
fi
