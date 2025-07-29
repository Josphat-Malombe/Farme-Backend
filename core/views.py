from django.shortcuts import render
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password

from rest_framework.views import APIView
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework import status
from rest_framework import viewsets,filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication

from openai import OpenAI
from gtts import gTTS
from langdetect import detect
from django.conf import settings

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    FarmerProfileUpdateSerializer,
        ChatMessageSerializer,
        FarmerTokenSerializer,
        ChatSessionSerializer,
        CountySerializer,
        ConstituencySerializer,
        WardSerializer
        )
from .models import ChatMessage,ChatSession,User,Constituency,County,Ward
from .utils.weather_service import get_weather,get_weather_data

import os
import uuid
import whisper
import tempfile
import requests
import google.generativeai as genai


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

#for model in genai.list_models():
   # print(model.name)





# Create your views here.

"""
class FarmerRegistrationView(APIView):

    def post(self, request):
        serializer = FarmerRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            farmer=serializer.save()
            return Response({"message":"Farmer registered successfully","id":str(farmer.id)}, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    """


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]




class FarmerLoginView(TokenObtainPairView):
    serializer_class = FarmerTokenSerializer





class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FarmerProfileUpdateSerializer(request.user, context={'request': request})

        return Response(serializer.data) 

    def patch(self,request):
        serializer=FarmerProfileUpdateSerializer(request.user,data=request.data,partial=True,context={'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#creating a chat session view


class DisplaySessionView(APIView):
    authentication_classes = [JWTAuthentication]
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        farmer = request.user
        sessions = ChatSession.objects.filter(farmer=farmer).order_by('-created_at')
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data)

class DeleteSessionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, farmer=request.user)
            session.delete()
            return Response({"message": "Session deleted successfully"}, status=204)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)


    
class CreateSessionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        farmer = request.user
        session = ChatSession.objects.create(
            farmer=request.user,
            id=uuid.uuid4(), 
        )
        return Response({
            "id": str(session.id),
            "farmer": str(farmer.id),
            "created_at": session.created_at
        })


#for saving messages to the db
class SaveChatMessageView(APIView):
    def post(self, request):
        serializer=ChatMessageSerializer(data=request.data)

        if serializer.is_valid():
            message=serializer.save()
            return Response({
                "message": "chat message saved successfully...",
                "data": ChatMessageSerializer(message).data 
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#listing messages in a session
class ChatSessionMessageView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class=ChatMessageSerializer

    def get_queryset(self):
        session_id=self.kwargs.get('session_id')
        return ChatMessage.objects.filter(session_id=session_id).order_by('timestamp')
    


#defining the agent
class ChatAgentRespondView(APIView):
    authentication_classes = [JWTAuthentication]
    #permission_classes = [IsAuthenticated]
   

    def post(self, request):
        session_id = request.data.get("session_id")
        question = request.data.get("question")

        if not question:
            return Response({"error": "Question is required!"}, status=400)

        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, farmer=request.user)
                farmer = session.farmer
            except ChatSession.DoesNotExist:
                return Response({"error": "Invalid session"}, status=400)
        else:
            session = ChatSession.objects.create(farmer=request.user)
            farmer = session.farmer

   
        ChatMessage.objects.create(
            session=session,
            role="user",
            content=question
        )

        if not session.title:
            clean_title=question.strip()[:50]
            session.title=clean_title
            session.save()

        try:
            language = detect(question)
            language_instruction = "swahili" if language == "sw" else "English"
        except:
            language_instruction = "English"

        

        # System prompt
        system_prompt = f"""
You are Quantum Ripple AI Agent, an expert agricultural advisor dedicated to helping smallholder farmers in Kenya. Your goal is to provide accurate, actionable, and hyper-localized advice.

Farmer Context:
The farmer asking the question is located in:
County: {farmer.county}
Constituency: {farmer.constituency}
Ward: {farmer.ward}

Conversation History:

Farmer's Current Query ( {language_instruction}):
{question}

Farmers full name is: {farmer.full_name} but you can just use the first name

Instructions for You (Quantum Ripple AI):
1. Analyze Context: Consider the farmer's location and question.
2. Prioritize Localization: Focus on conditions in the farmer's ward and county.
3. Actionable & Practical: Give steps the farmer can realistically follow.
4. Farmer-Friendly Language: Be clear and simple.
5. Conciseness: Give the key points first.
6. Language Match: Reply strictly in  {language_instruction}
7. Safety: Avoid unverified advice. Recommend experts if unsure.
8. Empathy: Be kind and helpful.
9. Search: You are also allowed to search in the internet if you can

Begin your response now:

"""

        
       
        chat_history = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:4]
        chat_history = reversed(chat_history)
        gemini_messages = [{"role": "user", "parts": [system_prompt]}]

        for msg in chat_history:
            role = "user" if msg.role == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg.content]})

        gemini_messages.append({"role": "user", "parts": [question]})

        try:
            api_key=settings.GEMINI_API_KEY
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(gemini_messages)
            reply = response.text

            ChatMessage.objects.create(session=session, role="agent", content=reply)

            return Response({
                "session_id": session.id,
                "question": question,
                "response": reply
            }, status=201)

        except Exception as e:
            return Response({"error": f"llm error: {str(e)}"}, status=500)


#openai ai model
"""     
        try:
            client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model = "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.6,
                max_tokens=300
            )
            #reply = response.choices[0].message.content.strip()
            # Replace the OpenAI call with dummy text temporarily:
            reply = "This is a mock AI response for development. Once quota is restored, you'll get real answers.Stay tuned!"


            agent_msg = ChatMessage.objects.create(
                session=session,
                role="agent",
                content=reply
            )

            return Response({
                "question":question,
                "response":reply
            }, status=201)
        
        except Exception as e:
            return Response({"error":f"llm error: {str(e)}"}, status=500)

            """
        

"""

class SpeechTrascriptionView(APIView):

    def post(self, request):
        session_id=request.data.get("session_id")
        audio_file = request.FILES.get("audio")

        if not audio_file or not session_id:
            return Response({"error": "session_id and audio are required!"}, status=status.HTTP_400_BAD_REQUEST)
        
        #validating session
        try:
            session=ChatSession.objects.get(id=session_id)
            farmer=session.farmer
        
        except ChatSession.DoesNotExist:
            return Response({"error":"invalid session id!!"})
        




#saving snd transcribing audio

        try:

            temp_dir = tempfile.gettempdir()
            temp_path=os.path.join(temp_dir, audio_file.name)
            
            with open(temp_path, "wb") as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)

            model = whisper.load_model("base") #small,large,medium

            result = model.transcribe(temp_path)

            transcript=result["text"].strip()

            #return Response({
              # "transcription":transcript.strip()
           # },status=status.HTTP_200_OK)
    
        except Exception as e:
            print("Transcription error: ",e)
            return Response({"error": f"Trascription failed:  {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        #saving transcript
        user_msg=ChatMessage.objects.create(
            session=session,
            role="user",
            content=transcript

        )

        #agent context

        system_prompt = 
        

        chat_history=ChatMessage.objects.filter(session=session).order_by("-timestamp")[:4]
        chat_history=reversed(chat_history)


        gemini_messages=[{"role":"user", "parts":[system_prompt]}]
        for msg in chat_history:
            role="user" if msg.role=="user" else "model"
            gemini_messages.append({"role":role, "parts":[msg.content]})

        gemini_messages.append({"role":"user", "parts": [transcript]})

        #generating output

        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

            model=genai.GenerativeModel("models/gemini-2.5-flash-preview-04-17-thinking")

            response=model.generate_content(gemini_messages)

            reply=response.text

            #saving agent response to db
            ChatMessage.objects.create(
                session=session,
                role="agent",
                content=reply
            )

            #converting resonses to audio

            media_dir=os.path.join(os.getcwd(), "media")
            os.makedirs(media_dir, exist_ok=True)
            print("transcribed text",transcript)

            print("text to convert:", reply)

            tts=gTTS(text=reply,lang="en")
            filename=f"response_{uuid.uuid4().hex}.mp3"
            filepath=os.path.join(media_dir ,filename)
            tts.save(filepath)

        except Exception as e:

            return Response({"error": f"AI Agent Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "transcription":transcript,
            "response":reply,
            "audio_url":request.build_absolute_uri(f"/media/{filename}")
        }, status=status.HTTP_201_CREATED)
        """



class VoiceChatView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        session_id = request.data.get("session_id",None)
        audio_file = request.FILES.get("audio")

        if not audio_file:
            return Response({"error": "audio is required"}, status=400)
        
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, farmer=request.user)
                farmer = session.farmer
            except ChatSession.DoesNotExist:
                return Response({"error": "Invalid session"}, status=400)
        else:
            session = ChatSession.objects.create(farmer=request.user)
            farmer = session.farmer

        

        try:
       
            farmer_audio_name = f"farmer_{uuid.uuid4().hex}.webm"
            farmer_audio_path = os.path.join(settings.MEDIA_ROOT, farmer_audio_name)
            with open(farmer_audio_path, "wb") as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)

        
            transcript = self.transcribe_audio(farmer_audio_path)

       
            ChatMessage.objects.create(session=session, role="user", content=transcript)


            ai_text = self.generate_ai_reply(farmer, transcript, session)
            ChatMessage.objects.create(session=session, role="agent", content=ai_text)

        
            ai_audio_url = self.generate_tts(ai_text)

            return Response({
                "farmer_audio": request.build_absolute_uri(f"/media/{farmer_audio_name}"),
                "transcription": transcript,
                "ai_text": ai_text,
                "ai_audio": request.build_absolute_uri(ai_audio_url)
        }, status=200)

        except Exception as e:
               import traceback
               print("ERROR:", str(e))
               traceback.print_exc()
               return Response({"error": str(e)}, status=500)



  

    def transcribe_audio(self, audio_path):
        model = whisper.load_model("small")  
        result = model.transcribe(audio_path)
        return result["text"].strip()

    def generate_ai_reply(self, farmer, transcript, session):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        system_prompt = f"""
        You are Quantum Ripple AI, an agricultural advisor.
        Farmer location: County={farmer.county}, Constituency={farmer.constituency}, Ward={farmer.ward}
        Farmer's question: {transcript}
        Respond simply, actionable, localized.
        """

       
        chat_history = ChatMessage.objects.filter(session=session).order_by("-timestamp")[:4]
        gemini_messages = [{"role": "user", "parts": [system_prompt]}]
        for msg in reversed(chat_history):
            role = "user" if msg.role == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg.content]})

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(gemini_messages)
        return response.text

    def generate_tts(self, text):
        media_dir = os.path.join(settings.BASE_DIR, "media")
        os.makedirs(media_dir, exist_ok=True)
        filename = f"response_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(media_dir, filename)

        tts = gTTS(text=text, lang="en")
        tts.save(filepath)

        return f"/media/{filename}"




"""
class WeatherView(APIView):

    def get(self,request):
        location=request.query_params.get("location", "Athi River")
        weather_data=get_weather(location)
        return Response(weather_data)
    

class WeatherApiView(APIView):
    def get(self, request):
        county = request.query_params.get('county')
        constituency = request.query_params.get('constituency')
        ward = request.query_params.get('ward')

        if not county:
            return Response({'error': 'County is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Build query for Nominatim
        location_query = f"{ward or ''}, {constituency or ''}, {county}, Kenya"
        geo_url = f"https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_query,
            'format': 'json',
            'limit': 1
        }

        geo_res = requests.get(geo_url, params=params, headers={'User-Agent': 'FarmeApp'}).json()

        if not geo_res:
            return Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)

        lat = geo_res[0]['lat']
        lon = geo_res[0]['lon']

        # Now call AgroWeather API using these coordinates
        api_key = settings.AGRO_WEATHER_API_KEY
        weather_url = f"http://api.agromonitoring.com/agro/1.0/weather?lat={lat}&lon={lon}&appid={api_key}"
        weather_res = requests.get(weather_url).json()

        temperature_kelvin = weather_res.get("main", {}).get("temp")
        temperature_celsius = round(temperature_kelvin - 273.15,2) if temperature_kelvin else None

        result = {
            "location": location_query,
            "temperature": temperature_celsius,
            "humidity": weather_res.get("main", {}).get("humidity"),
            "wind_speed": weather_res.get("wind", {}).get("speed"),
            "description": weather_res.get("weather", [{}])[0].get("description"),
            "icon": f"http://openweathermap.org/img/wn/{weather_res.get('weather', [{}])[0].get('icon')}@2x.png"
        }

        return Response(result)



"""

class WeatherApiView(APIView):
    def get(self, request):
        county = request.query_params.get('county')
        constituency = request.query_params.get('constituency')
        ward = request.query_params.get('ward')

        if not county:
            return Response({'error': 'County is required.'}, status=status.HTTP_400_BAD_REQUEST)

        
        location_query = f"{ward or ''}, {constituency or ''}, {county}, Kenya"
        geo_url = f"https://nominatim.openstreetmap.org/search"
        params = {'q': location_query, 'format': 'json', 'limit': 1}

        geo_res = requests.get(geo_url, params=params, headers={'User-Agent': 'FarmeApp'}).json()
        if not geo_res:
            return Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)

        lat = geo_res[0]['lat']
        lon = geo_res[0]['lon']

        
        agro_api_key = settings.AGRO_WEATHER_API_KEY
        agro_url = f"http://api.agromonitoring.com/agro/1.0/weather?lat={lat}&lon={lon}&appid={agro_api_key}"

        try:
            agro_res = requests.get(agro_url, timeout=5).json()
            temperature_kelvin = agro_res.get("main", {}).get("temp")
            if temperature_kelvin:
                temperature_celsius = round(temperature_kelvin - 273.15, 2)
                return Response({
                    "source": "AgroWeather",
                    "location": location_query,
                    "temperature": temperature_celsius,
                    "humidity": agro_res.get("main", {}).get("humidity"),
                    "wind_speed": agro_res.get("wind", {}).get("speed"),
                    "description": agro_res.get("weather", [{}])[0].get("description"),
                    "icon": f"http://openweathermap.org/img/wn/{agro_res.get('weather', [{}])[0].get('icon')}@2x.png"
                })
        except Exception as e:
            print("Agro API failed:", e)

      
        try:
            weather_api_key = settings.WEATHER_API_KEY
            weather_url = f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={lat},{lon}"
            weather_res = requests.get(weather_url, timeout=5).json()
            current = weather_res.get("current", {})
            if current:
                return Response({
                    "source": "WeatherAPI",
                    "location": f"{weather_res.get('location', {}).get('name')}, {county}",
                    "temperature": current.get("temp_c"),
                    "humidity": current.get("humidity"),
                    "wind_speed": current.get("wind_kph"),
                    "description": current.get("condition", {}).get("text"),
                    "icon": "http:" + current.get("condition", {}).get("icon")
                })
        except Exception as e:
            print("WeatherAPI fallback failed:", e)

        return Response({"error": "Could not retrieve weather information"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CountyViewSet(viewsets.ModelViewSet):
    queryset=County.objects.all()
    serializer_class=CountySerializer
    filter_backends=[filters.SearchFilter]
    search_fields=['name']


class ConstituencyViewSet(viewsets.ModelViewSet):
    queryset=Constituency.objects.all()
    serializer_class=ConstituencySerializer

    def get_queryset(self):
        queryset=super().get_queryset()
        county_id=self.request.query_params.get('county')

        if county_id:
            queryset=queryset.filter(county_id=county_id)

        return queryset
    

class WardViewSet(viewsets.ModelViewSet):
    queryset=Ward.objects.all()
    serializer_class=WardSerializer


    def get_queryset(self):
        queryset=super().get_queryset()
        constituency_id=self.request.query_params.get('constituency')

        if constituency_id:
            queryset=queryset.filter(constituency_id=constituency_id)

        return queryset