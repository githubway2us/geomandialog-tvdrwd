import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from firebase_admin import credentials, firestore, storage, initialize_app
from datetime import datetime
import functions_framework

# Initialize Firebase
cred = credentials.ApplicationDefault()  # ใช้ ADC สำหรับ Firebase ใน Functions
initialize_app(cred, {
    'storageBucket': 'geomandialog-tvdrwd.firebasestorage.app'
})
db = firestore.client()
bucket = storage.bucket()

# สร้าง Flask app
app = Flask(__name__, template_folder="../public/templates", static_folder="../public/static")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'  # ใช้ /tmp ใน Functions
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัดขนาดไฟล์ 16MB

# ฟังก์ชันช่วยเหลือ
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_plan_by_id(plan_id):
    plan = db.collection('travel_plans').document(str(plan_id)).get()
    if not plan.exists:
        abort(404, description="ไม่พบแผนการท่องเที่ยว")
    return plan

@app.context_processor
def inject_user():
    user = None
    puk_coins = 0
    if 'user_id' in session:
        user_doc = db.collection('users').document(str(session['user_id'])).get()
        if user_doc.exists:
            user = user_doc.to_dict()
            user['id'] = user_doc.id
            puk_coins = user.get('puk_coins', 0)
        else:
            session.pop('user_id', None)
    return dict(current_user=user, puk_coins=puk_coins)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/')
def index():
    provinces = db.collection('provinces').stream()
    regions = {
        'ภาคเหนือ': ['เชียงใหม่', 'เชียงราย', 'ลำปาง', 'ลำพูน', 'แม่ฮ่องสอน', 'น่าน', 'พะเยา', 'แพร่', 'อุตรดิตถ์'],
        # ... (เพิ่มภูมิภาคอื่น ๆ ตามเดิม)
    }
    region_provinces = {region: [] for region in regions}
    for province in provinces:
        province_data = province.to_dict()
        province_data['id'] = province.id
        post_count = db.collection('travel_plans').where('province_id', '==', province.id).get()
        province_data['post_count'] = len(post_count)
        for region, province_names in regions.items():
            if province_data['name'] in province_names:
                region_provinces[region].append(province_data)
    return render_template('index.html', region_provinces=region_provinces)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        user_ref = db.collection('users').document()
        try:
            user_ref.set({
                'username': username,
                'password': hashed_password,
                'puk_coins': 100,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            flash('สมัครสมาชิกสำเร็จ! กรุณาล็อกอิน')
            return redirect(url_for('login'))
        except:
            flash('ชื่อผู้ใช้นี้มีอยู่แล้ว')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = db.collection('users').where('username', '==', username).stream()
        user = next(users, None)
        if user and check_password_hash(user.to_dict()['password'], password):
            session['user_id'] = user.id
            flash('ล็อกอินสำเร็จ!')
            return redirect(url_for('index'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('ล็อกเอาท์สำเร็จ!')
    return redirect(url_for('index'))

def save_plan(form, files, province_id, plan=None):
    province_id = form['province_id']
    name = form['name']
    location = form['location']
    start_date = form['start_date']
    end_date = form['end_date']
    plan_ref = db.collection('travel_plans').document() if not plan else db.collection('travel_plans').document(str(plan.id))
    plan_data = {
        'user_id': session['user_id'],
        'province_id': province_id,
        'name': name,
        'location': location,
        'start_date': start_date,
        'end_date': end_date,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    plan_ref.set(plan_data)
    plan_id = plan_ref.id
    db.collection('activities').where('travel_plan_id', '==', plan_id).delete()
    total_budget = 0
    saved_activities = 0
    activity_count = max([int(key.split('[')[1].split(']')[0]) for key in form if key.startswith('activities[')] + [-1]) + 1
    for index in range(activity_count):
        time = form.get(f'activities[{index}][time]', '')
        detail = form.get(f'activities[{index}][detail]', '')
        budget = form.get(f'activities[{index}][budget]', '')
        file = files.get(f'activities[{index}][image]')
        if time or detail or budget or (file and allowed_file(file.filename)):
            budget_value = float(budget) if budget else 0
            activity_ref = db.collection('activities').document()
            activity_data = {
                'travel_plan_id': plan_id,
                'time': time,
                'detail': detail,
                'budget': budget_value
            }
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = f'activities/{plan_id}/{filename}'
                blob = bucket.blob(file_path)
                blob.upload_from_file(file, content_type=file.content_type)
                blob.make_public()
                activity_data['image_path'] = blob.public_url
            activity_ref.set(activity_data)
            total_budget += budget_value
            saved_activities += 1
    if saved_activities == 0:
        plan_ref.delete()
        flash('กรุณากรอกข้อมูลอย่างน้อยหนึ่งกิจกรรม')
        return False, province_id
    plan_ref.update({'total_budget': total_budget})
    user_ref = db.collection('users').document(str(session['user_id']))
    user_ref.update({'puk_coins': firestore.Increment(2)})
    flash(f'บันทึกแผนสำเร็จ! บันทึก {saved_activities} กิจกรรม และได้รับ 2 เหรียญ PUK')
    return True, province_id

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    provinces = db.collection('provinces').stream()
    provinces = [p.to_dict() | {'id': p.id} for p in provinces]
    selected_province_id = request.args.get('province_id')
    if request.method == 'POST':
        success, province_id = save_plan(request.form, request.files, selected_province_id)
        if success:
            return redirect(url_for('province', province_id=province_id))
        return redirect(url_for('post', province_id=province_id))
    return render_template('post.html', provinces=provinces, selected_province_id=selected_province_id)

@app.route('/add_plan', methods=['GET', 'POST'])
def add_plan():
    return post()  # รวมฟังก์ชันกับ /post

@app.route('/edit_plan/<plan_id>', methods=['GET', 'POST'])
def edit_plan(plan_id):
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    plan = get_plan_by_id(plan_id)
    if plan.to_dict()['user_id'] != session['user_id']:
        flash('คุณไม่มีสิทธิ์แก้ไขแผนนี้')
        return redirect(url_for('province', province_id=plan.to_dict()['province_id']))
    provinces = db.collection('provinces').stream()
    provinces = [p.to_dict() | {'id': p.id} for p in provinces]
    if request.method == 'POST':
        success, province_id = save_plan(request.form, request.files, plan.to_dict()['province_id'], plan)
        if success:
            return redirect(url_for('province', province_id=province_id))
        return redirect(url_for('edit_plan', plan_id=plan_id))
    return render_template('edit_plan.html', plan=plan.to_dict(), provinces=provinces)

@app.route('/province/<province_id>')
def province(province_id):
    province = db.collection('provinces').document(province_id).get()
    if not province.exists:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    plans = db.collection('travel_plans').where('province_id', '==', province_id).limit(per_page).offset((page-1)*per_page).stream()
    plans_data = []
    for plan in plans:
        plan_data = plan.to_dict()
        plan_data['id'] = plan.id
        activities = db.collection('activities').where('travel_plan_id', '==', plan.id).stream()
        plan_data['activities'] = [a.to_dict() for a in activities]
        plans_data.append(plan_data)
    return render_template('province.html', province=province.to_dict(), plans=plans_data)

@app.route('/plan/<plan_id>')
def plan_detail(plan_id):
    plan = get_plan_by_id(plan_id)
    plan_data = plan.to_dict()
    plan_data['id'] = plan.id
    transactions = db.collection('puk_transactions').where('travel_plan_id', '==', plan_id).stream()
    transactions_data = [t.to_dict() for t in transactions]
    return render_template('plan_detail.html', plan=plan_data, transactions=transactions_data)

@app.route('/plan/<plan_id>/delete', methods=['POST'])
def delete_plan(plan_id):
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    user_ref = db.collection('users').document(str(session['user_id']))
    user = user_ref.get()
    if not user.exists:
        session.pop('user_id', None)
        flash('เซสชันไม่ถูกต้อง กรุณาล็อกอินใหม่')
        return redirect(url_for('login'))
    plan = get_plan_by_id(plan_id)
    if plan.to_dict()['user_id'] != session['user_id']:
        flash('คุณไม่สามารถลบโพสต์นี้ได้')
        return redirect(url_for('province', province_id=plan.to_dict()['province_id']))
    if user.to_dict()['puk_coins'] < 10:
        flash('เหรียญ PUK ไม่เพียงพอสำหรับการลบโพสต์ (ต้องใช้ 10 เหรียญ)')
        return redirect(url_for('province', province_id=plan.to_dict()['province_id']))
    user_ref.update({'puk_coins': firestore.Increment(-10)})
    db.collection('travel_plans').document(plan_id).delete()
    flash('โพสต์ถูกลบเรียบร้อย! ใช้ 10 เหรียญ PUK')
    return redirect(url_for('province', province_id=plan.to_dict()['province_id']))

@app.route('/plan/<plan_id>/comment', methods=['POST'])
def comment(plan_id):
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    user = db.collection('users').document(str(session['user_id'])).get()
    if not user.exists:
        session.pop('user_id', None)
        flash('เซสชันไม่ถูกต้อง กรุณาล็อกอินใหม่')
        return redirect(url_for('login'))
    comment_text = request.form['comment']
    if comment_text:
        db.collection('comments').document().set({
            'travel_plan_id': plan_id,
            'user_id': session['user_id'],
            'comment': comment_text,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        flash('แสดงความคิดเห็นสำเร็จ!')
    plan = get_plan_by_id(plan_id)
    return redirect(url_for('province', province_id=plan.to_dict()['province_id']))

@app.route('/plan/<plan_id>/like', methods=['POST'])
def like(plan_id):
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    user = db.collection('users').document(str(session['user_id'])).get()
    if not user.exists:
        session.pop('user_id', None)
        flash('เซสชันไม่ถูกต้อง กรุณาล็อกอินใหม่')
        return redirect(url_for('login'))
    existing_like = db.collection('likes').where('travel_plan_id', '==', plan_id).where('user_id', '==', session['user_id']).get()
    if not existing_like:
        db.collection('likes').document().set({
            'travel_plan_id': plan_id,
            'user_id': session['user_id'],
            'created_at': firestore.SERVER_TIMESTAMP
        })
        flash('กดไลก์สำเร็จ!')
    else:
        flash('คุณกดไลก์โพสต์นี้แล้ว')
    plan = get_plan_by_id(plan_id)
    return redirect(url_for('province', province_id=plan.to_dict()['province_id']))

@app.route('/plan/<plan_id>/send_puk', methods=['POST'])
def send_puk(plan_id):
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    user_ref = db.collection('users').document(str(session['user_id']))
    user = user_ref.get()
    if not user.exists:
        session.pop('user_id', None)
        flash('เซสชันไม่ถูกต้อง กรุณาล็อกอินใหม่')
        return redirect(url_for('login'))
    amount = int(request.form['amount'])
    plan = get_plan_by_id(plan_id)
    if user.to_dict()['puk_coins'] < amount:
        flash('เหรียญ PUK ไม่เพียงพอ')
        return redirect(url_for('province', province_id=plan.to_dict()['province_id']))
    receiver_ref = db.collection('users').document(str(plan.to_dict()['user_id']))
    receiver = receiver_ref.get()
    if not receiver.exists:
        flash('ไม่พบผู้รับ กรุณาลองใหม่')
        return redirect(url_for('province', province_id=plan.to_dict()['province_id']))
    user_ref.update({'puk_coins': firestore.Increment(-amount)})
    receiver_ref.update({'puk_coins': firestore.Increment(amount)})
    db.collection('puk_transactions').document().set({
        'travel_plan_id': plan_id,
        'sender_id': session['user_id'],
        'receiver_id': plan.to_dict()['user_id'],
        'amount': amount,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    flash(f'ส่ง {amount} PUK สำเร็จ!')
    return redirect(url_for('province', province_id=plan.to_dict()['province_id']))

@app.route('/leaderboard')
def leaderboard():
    top_senders = db.collection('puk_transactions').stream()
    user_totals = {}
    for t in top_senders:
        t_data = t.to_dict()
        sender_id = t_data['sender_id']
        amount = t_data['amount']
        user = db.collection('users').document(sender_id).get()
        if user.exists:
            username = user.to_dict()['username']
            user_totals[username] = user_totals.get(username, 0) + amount
    top_senders = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    return render_template('leaderboard.html', top_senders=top_senders)

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        flash('กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))
    user = db.collection('users').document(str(session['user_id'])).get()
    if not user.exists:
        session.pop('user_id', None)
        flash('เซสชันไม่ถูกต้อง กรุณาล็อกอินใหม่')
        return redirect(url_for('login'))
    transactions = db.collection('puk_transactions').where('sender_id', '==', session['user_id']).get()
    transactions += db.collection('puk_transactions').where('receiver_id', '==', session['user_id']).get()
    transactions_data = [t.to_dict() for t in transactions]
    transactions_data.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('transactions.html', transactions=transactions_data)

@app.template_filter('format_number')
def format_number(value, precision=2):
    try:
        return f"{float(value):,.{precision}f}"
    except (ValueError, TypeError):
        return value

@app.template_filter('floatformat')
def floatformat(value, precision=2):
    try:
        return f"{float(value):.{precision}f}"
    except (ValueError, TypeError):
        return value

# Firebase Functions entry point
@functions_framework.http
def flask_app(request):
    return app(request)