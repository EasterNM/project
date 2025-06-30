from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect('general:dashboard')  # ถ้าผู้ใช้เข้าสู่ระบบแล้ว ให้ redirect ไปที่หน้า dashboard
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('general:dashboard')  # ล็อกอินสำเร็จ redirect ไปที่หน้า dashboard
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')
