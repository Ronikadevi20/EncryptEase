from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    otp_code = models.CharField(max_length=6, blank=True, null=True)  # Store the OTP code directly
    otp_verified = models.BooleanField(default=False)
    decoy_password = models.CharField(max_length=128, blank=True, null=True)
    
    def __str__(self):
        
        return self.user.username
    
    def generate_otp_code(self):
        import random
        self.otp_code = str(random.randint(100000, 999999))  # Generate a 6-digit OTP code
        self.save()
        return self.otp_code
    
    def verify_otp(self, otp_code):
        return self.otp_code == otp_code  # Direct comparison of the OTP code

    def set_decoy_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.decoy_password = make_password(raw_password)
        self.save()
        
    def check_decoy_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.decoy_password)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()