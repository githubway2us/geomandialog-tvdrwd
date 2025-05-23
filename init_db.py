from firebase_admin import credentials, firestore, initialize_app

# Initialize Firebase
cred = credentials.Certificate('geomandialog-tvdrwd-native-firebase-adminsdk-fbsvc-3d2d22b607.json')
initialize_app(cred)
db = firestore.client()

# ข้อมูลจังหวัด
provinces = [
    'เชียงใหม่', 'เชียงราย', 'ลำปาง', 'ลำพูน', 'แม่ฮ่องสอน', 'น่าน', 'พะเยา', 'แพร่', 'อุตรดิตถ์',
    'อำนาจเจริญ', 'บึงกาฬ', 'บุรีรัมย์', 'ชัยภูมิ', 'กาฬสินธุ์', 'ขอนแก่น', 'เลย', 'มหาสารคาม',
    'มุกดาหาร', 'นครพนม', 'นครราชสีมา', 'หนองบัวลำภู', 'หนองคาย', 'ร้อยเอ็ด', 'สกลนคร', 'ศรีสะเกษ',
    'สุรินทร์', 'อุบลราชธานี', 'อุดรธานี', 'ยโสธร', 'อ่างทอง', 'พระนครศรีอยุธยา', 'ชัยนาท',
    'กรุงเทพมหานคร', 'ลพบุรี', 'นครปฐม', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'สมุทรสาคร',
    'สมุทรสงคราม', 'สระบุรี', 'สิงห์บุรี', 'สุพรรณบุรี', 'ชลบุรี', 'จันทบุรี', 'ฉะเชิงเทรา',
    'ปราจีนบุรี', 'ระยอง', 'สระแก้ว', 'ตราด', 'กาญจนบุรี', 'เพชรบุรี', 'ประจวบคีรีขันธ์', 'ราชบุรี',
    'ตาก', 'ชุมพร', 'กระบี่', 'นครศรีธรรมราช', 'นราธิวาส', 'ปัตตานี', 'พังงา', 'พัทลุง', 'ภูเก็ต',
    'ระนอง', 'สตูล', 'สงขลา', 'สุราษฎร์ธานี', 'ตรัง', 'ยะลา'
]

# เพิ่มจังหวัดลง Firestore
for province in provinces:
    db.collection('provinces').document().set({
        'name': province,
        'created_at': firestore.SERVER_TIMESTAMP
    })

print("เพิ่มข้อมูลจังหวัดสำเร็จ!")