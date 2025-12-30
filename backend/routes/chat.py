from flask import Blueprint, request, jsonify
import re
import json
from services.prompt_builder import PromptBuilder
from services.user_service import UserService
from services.ollama_client import OllamaClient
from services.location_service import LocationService
from services.ai import get_ollama_client
from utils.intent import detect_intent


bp = Blueprint('chat', __name__, url_prefix='/api/chat')




@bp.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id')
        location_context = data.get('location_context', {}) # Get existing context
        
        print(f"\n💬 Chat Request: '{message}'")
        
        # Initialize services
        prompt_builder = PromptBuilder()
        user_service = UserService()
        ollama_client = OllamaClient()
        location_service = LocationService()
        
        mode = data.get('mode', 'text')
        history = data.get('history', [])
        
        # 1. Infer location from current message
        inferred = location_service.infer_location(message)
        if inferred:
            # Update context if new location detected
            location_context.update(inferred)
        
        # 2. Get user context (personalization)

        user_context = None
        if user_id:
            city = location_context.get('city', 'Agra')
            user_context = user_service.get_personalized_recommendations(user_id, city)
        
        # 3. Detect intent
        intent = detect_intent(message)
        print(f"🎯 Intent: {intent}")
        
        # 4. Build prompt with location and profile context
        profile_data = data.get('profile', {})
        prompt = prompt_builder.build_prompt(message, intent, user_context, location_context, mode, history, profile_data)

        
        # 5. Generate response
        print(f"🤖 Checking AI availability...")
        client = get_ollama_client()
        
        if client:
            print(f"✅ local dev only. Calling Ollama...")
            response_text = ollama_client.generate_response(prompt)
            # Ensure the specific "Local AI response" format if strictly required, 
            # but usually, we want the actual AI response for dev.
            # Following user request literally for the fallback logic:
        else:
            print(f"🔁 Render / cloud fallback active.")
            return jsonify({
                "reply": "AI demo mode is active. Backend is running successfully.",
                "response": "AI demo mode is active. Backend is running successfully.",
                "status": "success"
            })

        print(f"✅ Received response ({len(response_text)} chars)")

        
        # Extract map data if present (Ollama sometimes adds extra whitespace or newlines)

        map_data = None
        map_match = re.search(r'\[MAP_DATA:\s*(.*?)\]', response_text, re.DOTALL)
        if map_match:
            try:
                map_json_str = map_match.group(1).strip()
                map_data = json.loads(map_json_str)
                # Remove the data block from the text response
                response_text = re.sub(r'\[MAP_DATA:\s*.*?\]', '', response_text, flags=re.DOTALL).strip()
                print("📍 Map data successfully extracted")
            except Exception as e:
                print(f"⚠️ Map data error: {e}")
                # Optional: try to clean up malformed JSON if common

        return jsonify({
            'response': response_text,
            'reply': response_text,
            'intent': intent,

            'agent_type': intent,
            'status': 'success',
            'location_context': location_context, # Return updated context to frontend
            'language': "Hinglish",
            'data_source': 'india_guide_engine',
            'map_data': map_data
        })
        
    except ConnectionError as e:
        # Ollama is not running
        print(f"❌ Ollama Connection Error: {e}")
        return jsonify({
            'error': 'Ollama is not running',
            'message': 'Ollama service nahi chal rahi hai. Please start: ollama serve',
            'details': str(e),
            'fix': 'Run "ollama serve" in a terminal and try again'
        }), 503
        
    except TimeoutError as e:
        # Ollama timeout
        print(f"⏱️ Ollama Timeout: {e}")
        return jsonify({
            'error': 'Request timeout',
            'message': 'Ollama response mein bahut time lag raha hai. Thoda wait karein.',
            'details': str(e)
        }), 504
        
    except ValueError as e:
        # Model not found or invalid response
        error_str = str(e)
        print(f"❌ Value Error: {e}")
        if 'not found' in error_str.lower():
            return jsonify({
                'error': 'Model not found',
                'message': 'llama3 model installed nahi hai.',
                'details': str(e),
                'fix': 'Run "ollama pull llama3" to install the model'
            }), 404
        else:
            return jsonify({
                'error': 'Invalid response',
                'message': 'Ollama se invalid response aaya.',
                'details': str(e)
            }), 500
            
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': 'Backend mein error aa gayi. Console check karein.',
            'details': str(e)
        }), 500

def build_database_response(message, query_type, db_service, user_context=None):
    """Build response using database information, appropriate templates, and user preferences"""
    
    city_name = "Agra"  # This should come from config
    
    try:
        if query_type == 'city_overview':
            return build_city_overview_response(db_service, city_name, user_context)
        elif query_type == 'place_history':
            return build_place_history_response(message, db_service, city_name, user_context)
        elif query_type == 'food_history':
            return build_food_history_response(message, db_service, city_name, user_context)
        elif query_type == 'restaurant_suggestions':
            return build_restaurant_suggestions_response(db_service, city_name, user_context)
        elif query_type == 'places_to_visit':
            return build_places_to_visit_response(db_service, city_name, user_context)
        elif query_type == 'traffic_transport':
            return build_traffic_transport_response(db_service, city_name, user_context)
        elif query_type == 'accommodation':
            return build_accommodation_response(db_service, city_name, user_context)
        elif query_type == 'culture_traditions':
            return build_culture_traditions_response(db_service, city_name, user_context)
        else:
            return build_restaurant_suggestions_response(db_service, city_name, user_context)
    except Exception as e:
        print(f"Database response error: {e}")
        return get_fallback_response(query_type, user_context)

def build_city_overview_response(db_service, city_name, user_context=None):
    """Build city overview response using database"""
    data = db_service.get_city_overview(city_name)
    
    if data:
        city_info = data[0]
        response = f"""Agra ke baare mein batata hun aapko!

{city_info.get('historical_background', 'Agra ek historical city hai')}

**Cultural Significance:**
{city_info.get('cultural_significance', 'Famous for Taj Mahal and Mughal culture')}

**Daily Life:**
{city_info.get('daily_life_description', 'Locals enjoy street food and evening markets')}

**What Makes It Special:**
{city_info.get('unique_features', 'Taj Mahal, petha sweets, and warm people')}

Local Tip: {city_info.get('best_time_to_visit', 'October to March best time hai visit ke liye!')}"""
        
        # Add personalized note if user is logged in
        if user_context and user_context.get('user_preferences'):
            prefs = user_context['user_preferences']
            response += f"\n\n*Personalized Note: Aapki {prefs.get('travel_style', 'solo')} travel style aur {prefs.get('budget_range', 'mid_range')} budget ke according main aage specific recommendations dunga!*"
        
        return response
    
    return get_fallback_response('city_overview', user_context)

def build_place_history_response(message, db_service, city_name, user_context=None):
    """Build place history response"""
    # Extract place name from message (simplified)
    place_keywords = {'taj mahal': 'Taj Mahal', 'agra fort': 'Agra Fort', 'fatehpur sikri': 'Fatehpur Sikri'}
    place_name = None
    
    for keyword, proper_name in place_keywords.items():
        if keyword in message.lower():
            place_name = proper_name
            break
    
    if place_name:
        data = db_service.get_place_history(place_name, city_name)
        if data:
            place_info = data[0]
            response = f"""{place_name} ki history suniye:

**Kab Bana:** {place_info.get('built_year', 'Historical period')}
**Kisne Banaya:** {place_info.get('built_by', 'Mughal rulers')}

**Kyun Famous Hai:**
{place_info.get('historical_importance', 'Historical importance')}

**Aaj Kal:**
{place_info.get('current_status', 'Well maintained monument')}

**Interesting Fact:** {place_info.get('interesting_facts', 'Many hidden stories exist!')}

Local Tip: {place_info.get('best_visit_time', 'Early morning visit karo, kam crowd hota hai!')}"""
            
            # Add personalized visiting tips
            if user_context and user_context.get('user_preferences'):
                prefs = user_context['user_preferences']
                if prefs.get('travel_style') == 'family':
                    response += "\n\n*Family Tip: Family ke saath photography ke liye best spots main alag se bata sakta hun!*"
                elif prefs.get('travel_style') == 'solo':
                    response += "\n\n*Solo Tip: Peaceful exploration ke liye early morning ya late afternoon best hai!*"
            
            return response
    
    return "Koi specific place ka naam batayiye, main uski history detail mein bataunga!"

def build_food_history_response(message, db_service, city_name, user_context=None):
    """Build food history response"""
    food_keywords = {'petha': 'Petha', 'bedai': 'Bedai', 'jalebi': 'Jalebi'}
    food_name = None
    
    for keyword, proper_name in food_keywords.items():
        if keyword in message.lower():
            food_name = proper_name
            break
    
    if food_name:
        data = db_service.get_food_info(food_name, city_name)
        if data:
            food_info = data[0]
            response = f"""{food_name} ki kahani:

**Origin:** {food_info.get('origin_story', 'Traditional Agra food')}

**Kyun Popular:** {food_info.get('popularity_reason', 'Unique taste and tradition')}

**Kaise Khate Hain:** {food_info.get('eating_style', 'Traditional way')}

**Best Time:** {food_info.get('best_time_to_eat', 'Anytime')}

**Special Feature:** {food_info.get('unique_features', 'Unique to Agra')}

Local Habit: {food_info.get('local_habits', 'Locals love it!')}"""
            
            # Add budget-specific information
            if user_context and user_context.get('user_preferences'):
                budget = user_context['user_preferences'].get('budget_range')
                if budget == 'budget':
                    response += f"\n\n*Budget Tip: {food_name} ke liye street vendors sabse affordable hain!*"
                elif budget == 'luxury':
                    response += f"\n\n*Premium Tip: High-end sweet shops mein packaged {food_name} gift quality mein milta hai!*"
            
            return response
    
    return "Koi specific food ka naam batayiye, main uski history bataunga!"

def build_restaurant_suggestions_response(db_service, city_name, user_context=None):
    """Build restaurant suggestions response with personalization"""
    data = db_service.get_restaurants_by_city(city_name)
    
    if data:
        # Filter based on user preferences if available
        filtered_data = data
        if user_context and user_context.get('user_preferences'):
            budget_pref = user_context['user_preferences'].get('budget_range')
            if budget_pref:
                filtered_data = [place for place in data if place.get('category') == budget_pref or place.get('category') == 'street_food']
        
        response = "Agra mein khane ke liye yeh places try karo:\n\n"
        
        # Group by category
        categories = {}
        for place in filtered_data:
            cat = place.get('category', 'other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(place)
        
        for category, places in categories.items():
            if category == 'street_food':
                response += "**Street Food:**\n"
            elif category == 'budget_restaurant':
                response += "**Budget Restaurants:**\n"
            else:
                response += f"**{category.title()}:**\n"
            
            for place in places[:3]:  # Limit to top 3 per category
                response += f"• {place.get('place_name')} - {place.get('famous_for')} ({place.get('area_location')})\n"
        
        # Personalized tip
        if user_context and user_context.get('user_preferences'):
            prefs = user_context['user_preferences']
            if prefs.get('travel_style') == 'family':
                response += "\n*Family Tip: Family-friendly restaurants mein comfortable seating aur variety milti hai!*"
            elif prefs.get('budget_range') == 'budget':
                response += "\n*Budget Tip: Street food morning mein fresh aur affordable hota hai!*"
        else:
            response += "\nLocal Tip: Morning mein street food try karo, evening mein restaurants better hote hain!"
        
        return response
    
    return get_fallback_response('restaurant_suggestions', user_context)

def build_places_to_visit_response(db_service, city_name, user_context=None):
    """Build places to visit response"""
    data = db_service.get_places_to_visit(city_name)
    
    if data:
        # Filter based on user travel style
        filtered_data = data
        if user_context and user_context.get('user_preferences'):
            travel_style = user_context['user_preferences'].get('travel_style')
            if travel_style == 'family':
                # Prioritize must_visit places for families
                filtered_data = [place for place in data if place.get('importance') in ['must_visit', 'recommended']]
            elif travel_style == 'solo':
                # Include hidden gems for solo travelers
                filtered_data = data  # All places including hidden gems
        
        response = "Agra mein yeh jagah zaroor dekho:\n\n"
        
        for place in filtered_data[:5]:  # Limit to top 5
            response += f"• **{place.get('place_name')}** - {place.get('why_visit')}\n"
            if place.get('best_visit_time'):
                response += f"  Best Time: {place.get('best_visit_time')}\n"
        
        # Personalized tip
        if user_context and user_context.get('user_preferences'):
            travel_style = user_context['user_preferences'].get('travel_style')
            if travel_style == 'family':
                response += "\n*Family Tip: Family ke saath comfortable timing aur photography spots plan kar lena!*"
            elif travel_style == 'solo':
                response += "\n*Solo Tip: Hidden gems explore karne ke liye local guides se baat kar sakte hain!*"
        else:
            response += "\nLocal Tip: Early morning monuments visit karo, crowds kam hote hain!"
        
        return response
    
    return get_fallback_response('places_to_visit', user_context)

def build_traffic_transport_response(db_service, city_name, user_context=None):
    """Build traffic and transport response"""
    data = db_service.get_transport_info(city_name)
    
    if data:
        transport_info = data[0]
        response = f"""Agra mein transport ki jankari:

**Peak Hours:** {transport_info.get('peak_hours', 'Morning 8-10 AM, Evening 6-8 PM')}

**Best Travel Times:** {transport_info.get('off_peak_hours', 'Early morning or afternoon')}

**Transport Options:**
{transport_info.get('local_transport_options', 'Auto rickshaw, e-rickshaw, buses available')}

**Traffic Patterns:**
{transport_info.get('traffic_patterns', 'Main roads crowded during peak hours')}

Local Tip: {transport_info.get('time_saving_tips', 'Auto rickshaw fare negotiate karna, prepaid better option!')}"""
        
        # Add budget-specific transport tips
        if user_context and user_context.get('user_preferences'):
            budget = user_context['user_preferences'].get('budget_range')
            if budget == 'budget':
                response += "\n\n*Budget Tip: Shared auto aur city buses sabse economical hain!*"
            elif budget == 'luxury':
                response += "\n\n*Comfort Tip: Pre-booked cabs ya hotel transport comfortable aur reliable hote hain!*"
        
        return response
    
    return get_fallback_response('traffic_transport', user_context)

def build_accommodation_response(db_service, city_name, user_context=None):
    """Build accommodation response"""
    data = db_service.get_accommodation_info(city_name)
    
    if data:
        # Filter based on user budget preference
        filtered_data = data
        if user_context and user_context.get('user_preferences'):
            budget_pref = user_context['user_preferences'].get('budget_range')
            if budget_pref:
                filtered_data = [area for area in data if area.get('category') == budget_pref]
        
        response = "Agra mein rukne ke liye areas:\n\n"
        
        for area in filtered_data:
            response += f"• **{area.get('area_name')}** ({area.get('category')})\n"
            response += f"  {area.get('area_description')}\n"
            if area.get('suitable_for'):
                response += f"  Good for: {area.get('suitable_for')}\n"
        
        # Personalized tip
        if user_context and user_context.get('user_preferences'):
            travel_style = user_context['user_preferences'].get('travel_style')
            if travel_style == 'family':
                response += "\n*Family Tip: Family rooms aur nearby restaurants wale areas prefer kariye!*"
            elif travel_style == 'business':
                response += "\n*Business Tip: WiFi aur meeting facilities wale hotels check kariye!*"
        else:
            response += "\nLocal Tip: Taj Ganj tourist-friendly hai, Sadar local experience ke liye better!"
        
        return response
    
    return get_fallback_response('accommodation', user_context)

def build_culture_traditions_response(db_service, city_name, user_context=None):
    """Build culture and traditions response"""
    data = db_service.get_cultural_info(city_name)
    
    if data:
        response = "Agra ki cultural traditions:\n\n"
        
        for tradition in data:
            response += f"• **{tradition.get('tradition_name')}**\n"
            response += f"  {tradition.get('historical_background')}\n"
            if tradition.get('current_practice'):
                response += f"  Aaj Kal: {tradition.get('current_practice')}\n"
        
        # Add language-specific note
        if user_context and user_context.get('user_preferences'):
            lang_pref = user_context['user_preferences'].get('language_preference')
            if lang_pref == 'hindi':
                response += "\n*Cultural Tip: Local festivals mein participate karne se authentic experience milta hai!*"
        else:
            response += "\nLocal Tip: Festivals ke time visit karo, city ka real culture dikhta hai!"
        
        return response
    
    return get_fallback_response('culture_traditions', user_context)

def get_fallback_response(query_type, user_context=None):
    """Fallback responses when database is not available"""
    fallbacks = {
        'city_overview': """Agra - Taj Mahal ka ghar!

Yeh city Mughal samay se famous hai. Taj Mahal, Agra Fort, aur Fatehpur Sikri yahan ke main attractions hain. 

Daily life mein locals morning bedai-jalebi khate hain, evening Sadar Bazaar mein shopping karte hain. Petha yahan ki famous sweet hai.

Local Tip: October to March best time hai visit ke liye!""",
        
        'restaurant_suggestions': """Agra mein food ke liye yeh places try karo:

**Street Food:**
• Deviram Sweets - Famous bedai-jalebi (morning best)
• Sadar Bazaar - Chaat aur evening snacks

**Restaurants:**
• Joney's Place - Budget North Indian (Taj Ganj)
• Pinch of Spice - Family dining

Local Tip: Morning street food culture strong hai yahan!""",
        
        'places_to_visit': """Agra mein must-visit places:

• Taj Mahal - World wonder, sunrise/sunset best
• Agra Fort - UNESCO heritage site
• Fatehpur Sikri - Day trip, 40km away
• Sadar Bazaar - Local shopping experience

Local Tip: Early morning monuments visit karo!""",
        
        'traffic_transport': """Agra transport guide:

**Peak Hours:** Morning 8-10 AM, Evening 6-8 PM
**Best Times:** Early morning ya afternoon

**Options:** Auto rickshaw (negotiate fare), e-rickshaw, city buses

Local Tip: Railway station se Taj Mahal 6km, 20-30 minutes lagta hai!""",
        
        'accommodation': """Agra stay areas:

• **Taj Ganj** - Near Taj Mahal, tourist area
• **Sadar** - Local area, market access
• **Fatehabad Road** - Mid-range hotels

Local Tip: Taj view rooms costly but sunrise experience amazing!"""
    }
    
    base_response = fallbacks.get(query_type, fallbacks['restaurant_suggestions'])
    
    # Add personalized note if user context available
    if user_context and user_context.get('user_preferences'):
        prefs = user_context['user_preferences']
        base_response += f"\n\n*Personalized Note: Aapki {prefs.get('budget_range', 'mid_range')} budget aur {prefs.get('travel_style', 'solo')} travel style ke according specific recommendations ke liye account login kariye!*"
    
    return base_response