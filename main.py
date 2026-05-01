import telebot
from docxtpl import DocxTemplate
import os
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore
import random
import string
import json

# --- 1. إعداد قاعدة بيانات Firebase من الـ Environment Variables ---
if not firebase_admin._apps:
    # التعديل الجوهري: القراءة من Variable بدل ملف
    try:
        service_account_info = json.loads(os.environ.get('PRIVATE_KEY_JSON'))
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Error loading credentials: {e}")

db = firestore.client()

# --- 2. إعداد البوت والخصوصية ---
TOKEN = "8612610272:AAEzZ50zSfwUQVnTnjIlaGDyQprWprFs81Q"
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS = [5338026910, 5774155559] 

user_data = {}

# قائمة الأسئلة
QUESTIONS = [
    {'field': 'duration_ar', 'text': '1. أدخل مدة الإجازة (بالعربي):'},
    {'field': 'duration_en', 'text': '2. أدخل مدة الإجازة (بالإنجليزي):'},
    {'field': 'admission_ar', 'text': '3. أدخل تاريخ الدخول (بالهجري):'},
    {'field': 'admission_en', 'text': '4. أدخل تاريخ الدخول (بالميلادي):'},
    {'field': 'discharge_ar', 'text': '5. أدخل تاريخ الخروج (بالهجري):'},
    {'field': 'discharge_en', 'text': '6. أدخل تاريخ الخروج (بالميلادي):'},
    {'field': 'issue_date', 'text': '7. أدخل تاريخ إصدار التقرير:'},
    {'field': 'name_ar', 'text': '8. أدخل اسم المريض (بالعربي):'},
    {'field': 'name_en', 'text': '9. أدخل اسم المريض (بالإنجليزي):'},
    {'field': 'id_number', 'text': '10. أدخل رقم الهوية / الإقامة:'},
    {'field': 'nationality_ar', 'text': '11. أدخل الجنسية (بالعربي):'},
    {'field': 'nationality_en', 'text': '12. أدخل الجنسية (بالإنجليزي):'},
    {'field': 'employer_ar', 'text': '13. أدخل جهة العمل (بالعربي):'},
    {'field': 'employer_en', 'text': '14. أدخل جهة العمل (بالإنجليزي):'},
    {'field': 'practitioner_ar', 'text': '15. أدخل اسم الطبيب المعالج (بالعربي):'},
    {'field': 'practitioner_en', 'text': '16. أدخل اسم الطبيب المعالج (بالإنجليزي):'},
    {'field': 'position_ar', 'text': '17. أدخل المسمى الوظيفي (بالعربي):'},
    {'field': 'position_en', 'text': '18. أدخل المسمى الوظيفي (بالإنجليزي):'},
    {'field': 'hospital_name', 'text': '19. أخيراً.. اذكر اسم المستشفى بالعربي:'}
]

def generate_gsl_code():
    numbers = ''.join(random.choices(string.digits, k=11))
    return f"GSL{numbers}"

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, "❌ عذراً، هذا البوت مخصص للاستخدام الخاص فقط.")
        return
    user_data[message.chat.id] = {'step': 0, 'answers': {}}
    bot.send_message(message.chat.id, "أهلاً بك يا بشمهندس! نبدأ بجمع البيانات لإصدار التقرير الطبي.. 📝")
    ask_question(message.chat.id)

def ask_question(chat_id):
    step = user_data[chat_id]['step']
    if step < len(QUESTIONS):
        bot.send_message(chat_id, QUESTIONS[step]['text'])
    else:
        create_document(chat_id)

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    chat_id = message.chat.id
    if chat_id not in user_data: return
    step = user_data[chat_id]['step']
    field_name = QUESTIONS[step]['field']
    user_data[chat_id]['answers'][field_name] = message.text
    user_data[chat_id]['step'] += 1
    ask_question(chat_id)

def create_document(chat_id):
    bot.send_message(chat_id, "جاري معالجة البيانات وحفظها في السحابة... ⏳")
    try:
        answers = user_data[chat_id]['answers']
        leave_id = generate_gsl_code()
        answers['leave_id'] = leave_id
        
        doc_name_db = f"{answers['id_number']}_{leave_id}"
        db.collection('sick_leaves').document(doc_name_db).set(answers)

        doc = DocxTemplate("template2.docx")
        doc.render(answers)
        
        docx_name = "sickLeaves.docx"
        pdf_name = "sickLeaves.pdf"
        doc.save(docx_name)
        
        # تحويل لـ PDF (LibreOffice)
        subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'pdf', 
            '--outdir', os.getcwd(), docx_name
        ], check=True)
        
        with open(pdf_name, "rb") as file:
            bot.send_document(
                chat_id, 
                file, 
                caption=f"✅ تم إصدار التقرير الطبي بنجاح!\n\n🔹 المستشفى: {answers.get('hospital_name', 'غير محدد')}\n🔹 رقم الهوية: {answers['id_number']}\n🔹 رمز الإجازة: {leave_id}"
            )
        
        if os.path.exists(docx_name): os.remove(docx_name)
        if os.path.exists(pdf_name): os.remove(pdf_name)
        del user_data[chat_id]
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء المعالجة: {e}")

print("🚀 البوت شغال الآن...")
bot.infinity_polling()
