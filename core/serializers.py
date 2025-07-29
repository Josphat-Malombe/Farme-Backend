
from rest_framework import serializers
import uuid
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import(
     ChatMessage,
     ChatSession,
     User,
     Constituency,
     County,
     Ward
)


class UserSerializer(serializers.ModelSerializer):
    county        = serializers.PrimaryKeyRelatedField(queryset=County.objects.all())
    constituency  = serializers.PrimaryKeyRelatedField(queryset=Constituency.objects.all())
    ward          = serializers.PrimaryKeyRelatedField(queryset=Ward.objects.all())

    county_name = serializers.CharField(source='county.name', read_only=True)
    constituency_name = serializers.CharField(source='constituency.name', read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 
            'full_name', 
            'email', 
            'phone_number', 
            'county', 
            'constituency', 
            'ward',
            'language_preference', 
            'user_type']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone_number', 'password', 'county', 'constituency', 'ward', 'language_preference']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    


class FarmerProfileUpdateSerializer(serializers.ModelSerializer):
    county        = serializers.PrimaryKeyRelatedField(queryset=County.objects.all())
    constituency  = serializers.PrimaryKeyRelatedField(queryset=Constituency.objects.all())
    ward          = serializers.PrimaryKeyRelatedField(queryset=Ward.objects.all())

    county_name = serializers.CharField(source='county.name', read_only=True)
    constituency_name = serializers.CharField(source='constituency.name', read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)

    profile_picture_url = serializers.SerializerMethodField()
    class Meta:
        model=User
        fields = [
            'full_name', 
            'email', 
            'county', 
            'county_name',
            'constituency', 
            'constituency_name',
            'ward',
            'ward_name', 
            'language_preference', 
            'profile_picture',
            'profile_picture_url',
        ]
    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url)
        return None

       

    def update(self, instance, validated_data):
        print("Validated Data for Update:", validated_data)

        for attr, value in validated_data.items():
            setattr(instance,attr, value)

        instance.save()
        return instance
            
        

class ChatMessageSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(write_only=True)
    class Meta:
        model=ChatMessage
        fields=['id','session_id','role','content','timestamp']
        read_only_fields=['id','timestamp']

    def validate_role(self,value):
        if value not in ['user','agent']:
            raise serializers.ValidationError("Role must be either agent or user")
        return value
    
    def create(self, validated_data):
        session_id=validated_data.pop('session_id')

        try:
            session = ChatSession.objects.filter(id=session_id, farmer=self.context['request'].user).first()
            if not session:
                 raise serializers.ValidationError("Invalid session or not authorized.")

   
        except ChatSession.DoesNotExist:
            raise serializers.ValidationError("chat session with this ID does not exist")
        
        return ChatMessage.objects.create(session=session, **validated_data)


class FarmerTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = user.full_name
        return token
    

class ChatSessionSerializer(serializers.ModelSerializer):
    """
    model serializer for displaying chat sessions
    """
    class Meta:
        model = ChatSession
        fields = ['id','title','created_at']

class WardSerializer(serializers.ModelSerializer):

    class Meta:
        model=Ward
        fields=['id','name']


class ConstituencySerializer(serializers.ModelSerializer):
    wards=WardSerializer(many=True, read_only=True)

    class Meta:
        model=Constituency
        fields=['id','name','wards']
        read_only_fields=['id']

class CountySerializer(serializers.ModelSerializer):
    constituencies=ConstituencySerializer(many=True, read_only=True)

    class Meta:
        model=County
        fields=['id','name','constituencies']
        read_only_fields=['id']

