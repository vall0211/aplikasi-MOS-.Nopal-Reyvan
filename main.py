from fileinput import filename
from flask import Flask, flash ,render_template,request,redirect,url_for,session
from flask_mysqldb import MySQL,MySQLdb
import bcrypt
from secrets import token_hex
import datetime
from werkzeug.utils import secure_filename
from uuid import uuid4
import os
from flask import request, jsonify


app = Flask(__name__)
app.secret_key = token_hex(16)
app.config['MYSQL_CURSORCLASS']='DictCursor'
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='db_memories_of_school'
app.config['UPLOAD_FOLDER']='static/uploads'


mysql=MySQL(app)

def allowed_file(filename):
    if '.' not in filename:
        return False
    eksternal_berkas = filename.split('.')[-1].lower()
    return eksternal_berkas in ['png','jpg','jpeg','gif']

now=datetime.datetime.now()

@app.route('/')
def index():
    return redirect(url_for('utama'))


@app.route('/utama')
def utama():
    return render_template('folder/folder.html')

@app.route('/foto_acak')
def foto_acak():
    tahun=request.args.get('tahun')
    return render_template('folder/foto_acak.html',tahun=tahun)
@app.route('/api/foto')
def api_foto():
    tahun = request.args.get('tahun')
    cur = mysql.connection.cursor()

    if tahun and tahun != 'None' and tahun != 'undefined':
        cur.execute("""
            SELECT id_media, foto, keterangan,
                YEAR(tanggal_diambil) AS tahun,
                tanggal_diambil, posisi_x, posisi_y 
            FROM media 
            WHERE YEAR(tanggal_diambil) = %s
            ORDER BY tanggal_diambil DESC
        """, (tahun,))
    else:
        cur.execute("""
            SELECT id_media, foto, keterangan,
                YEAR(tanggal_diambil) AS tahun,
                tanggal_diambil, posisi_x, posisi_y 
            FROM media 
            ORDER BY tanggal_diambil DESC
        """)

    fotos = cur.fetchall()
    cur.close()

    return jsonify({'success': True, 'foto': fotos})

@app.route('/image')
def image():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT *, YEAR(tanggal_diambil) AS tahun
        FROM media
        ORDER BY tanggal_diambil DESC
    """)
    media = cur.fetchall()
    grouped_media = {}
    
    for item in media:
        tahun = item['tahun']
        if tahun not in grouped_media:
            grouped_media[tahun] = []
        grouped_media[tahun].append(item)
    cur.close()

        
    return render_template('folder/image.html', grouped_media=grouped_media)

@app.route('/admin',methods=['GET','POST'])
def admin():
    if 'id_pengguna' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT *, YEAR(tanggal_diambil) AS tahun
        FROM media
        ORDER BY tanggal_diambil DESC
    """)
    media = cur.fetchall()
    grouped_media = {}
    
    for item in media:
        tahun = item['tahun']
        if tahun not in grouped_media:
            grouped_media[tahun] = []
        grouped_media[tahun].append(item)
        
    return render_template('admin/index.html', grouped_media=grouped_media)

@app.route('/hapus_foto/<int:id_media>', methods=['GET', 'POST'])
def hapus_foto(id_media):
    if 'id_pengguna' not in session:
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT foto FROM media WHERE id_media = %s", (id_media,))
        foto = cur.fetchone()
        
        if foto and foto['foto']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], foto['foto'])
            if os.path.exists(file_path):
                os.remove(file_path)  
        
        cur.execute("DELETE FROM media WHERE id_media = %s", (id_media,))
        mysql.connection.commit()
        cur.close()
        
        flash('Foto berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Gagal menghapus foto: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/upload_foto', methods=['POST'])
def upload_foto():
    if 'id_pengguna' not in session:
        return redirect(url_for('login'))
    foto = request.files.get('foto')
    keterangan = request.form.get('keterangan')
    tanggal_diambil = request.form.get('tanggal_diambil')
    dibuat=now.strftime('%Y-%m-%d %H:%M:%S')

    filename = None

    if foto and allowed_file(foto.filename):
            filename = f"{uuid4().hex}_{secure_filename(foto.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(filepath)
        
    cur=mysql.connection.cursor()
    cur.execute("INSERT INTO media (foto, keterangan, tanggal_diambil,dibuat_pada) VALUES (%s, %s, %s,%s)", (filename, keterangan, tanggal_diambil,dibuat))
    mysql.connection.commit()
    return redirect(url_for('admin'))

@app.route('/foto_acak_admin')
def foto_acak_admin():
    if 'id_pengguna' not in session:
        return redirect(url_for('login'))
    tahun=request.args.get('tahun')
    return render_template('admin/foto_acak_admin.html',tahun=tahun)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nama = request.form['username']
        email=request.form['email']
        password = request.form['password'].encode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM pengguna WHERE nama = %s AND email = %s", (nama, email))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(password, user['kata_sandi'].encode('utf-8')):
            session['id_pengguna'] = user['id_pengguna']
            session['nama'] = user['nama']
            session['email'] = user['email']
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))
@app.route('/seeder')
def seeder():
    nama = 'StarDVall'
    password = 'nauvalsukaannayamada'
    email = 'YAMADA@gmail.com'
    peran = 'admin'
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT IGNORE INTO pengguna (nama,kata_sandi,email,peran) VALUES (%s,%s,%s,%s)",
        (nama, hashed.decode('utf-8'), email, peran)
    )
    mysql.connection.commit()
    cursor.close()
    
    return "Seeder berhasil dijalankan"
    
if __name__=='__main__':
    app.run(debug=True)