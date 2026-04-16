"""
Authentication Views - Login, Register, OTP verification
"""

import os
import random
import string
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests

from .utils import send_welcome_email, generate_otp, send_otp_email


# Logic removed - now using unified functions from .utils



@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """Login with email and password"""
    try:
        import json
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return JsonResponse({'success': False, 'error': 'Email and password required'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid email or password'}, status=401)
        
        if not user.check_password(password):
            return JsonResponse({'success': False, 'error': 'Invalid email or password'}, status=401)
        
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        
        return JsonResponse({'success': True, 'message': 'Login successful'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    """Register new user and send OTP"""
    try:
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not name or not email or not password:
            return JsonResponse({'success': False, 'error': 'All fields required'}, status=400)
        
        if len(password) < 6:
            return JsonResponse({'success': False, 'error': 'Password must be at least 6 characters'}, status=400)
        
        # Check if user exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if existing_user.is_active:
                return JsonResponse({'success': False, 'error': 'Email already registered and active'}, status=400)
            else:
                # Inactive user trying again? Just update their info and resend OTP
                existing_user.set_password(password)
                existing_user.first_name = name
                existing_user.save()
                user = existing_user
        else:
            # Create new inactive user
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=name,
                is_active=False
            )
        
        # Generate and store OTP
        otp = generate_otp()
        cache.set(f'otp_{email}', otp, timeout=600)  # 10 minutes
        
        print(f"\n" + "="*50)
        print(f"OTP VERIFICATION CODE FOR {email}")
        print(f"   Your OTP is: {otp}")
        print(f"   (Valid for 10 minutes)")
        print(f"="*50 + "\n")
        
        # Send OTP email
        success, msg = send_otp_email(email, otp)
        
        if not success:
            # For demo, return OTP in response if email fails
            return JsonResponse({
                'success': True, 
                'message': 'OTP sent (check server console for demo)',
                'demo_otp': otp
            })
        
        return JsonResponse({'success': True, 'message': 'OTP sent to your email'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp_view(request):
    """Verify OTP and activate user"""
    try:
        import json
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        
        if not email or not otp:
            return JsonResponse({'success': False, 'error': 'Email and OTP required'}, status=400)
        
        stored_otp = cache.get(f'otp_{email}')
        
        if not stored_otp:
            return JsonResponse({'success': False, 'error': 'OTP expired or not found'}, status=400)
        
        if stored_otp != otp:
            return JsonResponse({'success': False, 'error': 'Invalid OTP'}, status=400)
        
        # Activate user
        try:
            user = User.objects.get(email=email)
            user.is_active = True
            user.save()
            
            # Clear OTP cache
            cache.delete(f'otp_{email}')
            
            # Auto-login
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            # Send Cyberpunk Welcome Email
            send_welcome_email(user.email, user.first_name or user.username)
            
            return JsonResponse({'success': True, 'message': 'Email verified successfully'})
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=400)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resend_otp_view(request):
    """Resend OTP to user email"""
    try:
        import json
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email required'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Email not registered'}, status=400)
        
        if user.is_active:
            return JsonResponse({'success': False, 'error': 'Email already verified'}, status=400)
        
        # Generate new OTP
        otp = generate_otp()
        cache.set(f'otp_{email}', otp, timeout=600)
        
        print(f"\n" + "="*50)
        print(f"RESEND OTP FOR {email}")
        print(f"   Your OTP is: {otp}")
        print(f"   (Valid for 10 minutes)")
        print(f"="*50 + "\n")
        
        # Send OTP email
        success, msg = send_otp_email(email, otp)
        
        if not success:
            return JsonResponse({
                'success': True, 
                'message': 'OTP resent (check server console)',
                'demo_otp': otp
            })
        
        return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
