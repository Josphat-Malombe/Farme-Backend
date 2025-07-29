from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid
from django.contrib.auth.models import BaseUserManager
from django.conf import settings




class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)
    

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(null=True, blank=True)
    county       = models.ForeignKey(
                      'core.County',
                      on_delete=models.SET_NULL,
                      null=True,
                      blank=True,
                      related_name='users')
    constituency = models.ForeignKey(
                      'core.Constituency',
                      on_delete=models.SET_NULL,
                      null=True,
                      blank=True,
                      related_name='users')
    ward         = models.ForeignKey(
                      'core.Ward',
                      on_delete=models.SET_NULL,
                      null=True,
                      blank=True,
                      related_name='users')
    language_preference = models.CharField(max_length=50, default='kamba')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def get_full_name(self):
        """Return the full name for Django admin and authentication."""
        return self.full_name
    def get_short_name(self):
        """Return a short name (first word of full_name)."""
        return self.full_name.split(' ')[0] if self.full_name else self.phone_number

    def __str__(self):
        return self.full_name




class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False)
    farmer=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='chat_session')
    title=models.CharField(max_length=255, blank=True, null=True)
    language=models.CharField(max_length=50, default='English')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f" Chat Session ({self.id}) by {self.farmer.full_name}"
    

class ChatMessage(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session=models.ForeignKey('core.ChatSession', on_delete=models.CASCADE, related_name='messages')
    ROLE_CHOICES=[
        ('user','User'),
        ('agent','Agent'),
    ]
    role=models.CharField(max_length=10, choices=ROLE_CHOICES)
    content=models.TextField()
    timestamp=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" message ({self.role}) at {self.timestamp.strftime('%Y-%m-%d, %H:%M%S')} "



class County(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4, editable=False)
    name=models.CharField(max_length=100,db_index=True,unique=True)

    class Meta:
        ordering=['name']
        verbose_name_plural="counties"

    def __str__(self):
        return self.name

class Constituency(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=150, unique=True,db_index=True)
    county=models.ForeignKey(County ,on_delete=models.CASCADE,related_name='constituencies')
    

    class Meta:
        ordering=['name']
        unique_together=('name','county')

    def __str__(self):
        return f"{self.name} ({self.county.name})"

class Ward(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=150,unique=True,db_index=True)
    constituency=models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='wards')

    class Meta:
        ordering=['name']
       # unique_together=('name','constituency')

    def __str__(self):
        return f"{self.name} ({self.constituency.name})"



