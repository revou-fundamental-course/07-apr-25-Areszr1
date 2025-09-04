from flask import Flask, request, redirect, url_for, session, render_template_string
import qrcode, io, sqlite3, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from openpyxl import Workbook
from flask import send_file

app = Flask(__name__)
app.secret_key = "absensi-qr-secret"

DB_NAME = "absensi_qr.db"

# ==== INIT DB ====
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS siswa(id INTEGER PRIMARY KEY, nama TEXT)")
        # Tambah kolom status jika belum ada
        c.execute("PRAGMA table_info(absensi)")
        columns = [col[1] for col in c.fetchall()]
        if "status" not in columns:
            try:
                c.execute("ALTER TABLE absensi ADD COLUMN status TEXT DEFAULT 'Hadir'")
            except sqlite3.OperationalError:
                pass
        c.execute("CREATE TABLE IF NOT EXISTS absensi(id INTEGER PRIMARY KEY, siswa_id INTEGER, waktu TEXT, petugas TEXT, status TEXT DEFAULT 'Hadir')")
        conn.commit()

        users = [("guru","guru123","guru"),("sekre","sekre123","sekre"),("ketua","ketua123","ketua")]
        for u,p,r in users:
            c.execute("SELECT * FROM users WHERE username=?",(u,))
            if not c.fetchone():
                c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                          (u, generate_password_hash(p), r))
        conn.commit()
init_db()

# ==== TEMPLATE BASE ====
base_html = """
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{title}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
  <style>
    .btn-animate { transition: transform 0.2s; }
    .btn-animate:active { transform: scale(0.95); }
    .fade-in { animation: fadeIn 0.7s; }
    @keyframes fadeIn { from {opacity:0;} to {opacity:1;} }
    .loading-spinner {
      display: none;
      margin: 0 auto;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #00ff88;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      animation: spin 1s linear infinite;
    }
    @keyframes spin { 100% { transform: rotate(360deg); } }
    .btn-kembali { border:2px solid #ff2d2d !important; }
  </style>
</head>
<body class="bg-light fade-in">
<nav class="navbar navbar-dark bg-dark fade-in">
  <div class="container-fluid">
    <span class="navbar-brand">📋 Absensi QR</span>
    {% if session.get('user') %}
      <span class="text-white">Hi, {{session['user']}} ({{session['role']}})</span>
      <a href="{{url_for('logout')}}" class="btn btn-sm btn-danger btn-animate ms-2">Logout</a>
    {% endif %}
  </div>
</nav>
<div class="container my-4 fade-in">
  {{content|safe}}
</div>
<script>
  document.body.classList.add('fade-in');
</script>
</body>
</html>
"""

# ==== ROUTES ====
@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    role = session["role"]
    content = """
    <div class='card p-4 shadow fade-in'>
      <h3 class='mb-3'>Menu</h3>
      <div class='d-grid gap-3'>
    """
    if role=="guru":
        content += "<a href='/tambah_siswa' class='btn btn-success btn-animate'>Tambah Siswa</a>"
        content += "<a href='/rekap' class='btn btn-primary btn-animate'>Lihat Rekap</a>"
    content += "<a href='/scan' class='btn btn-warning btn-animate'>Scan QR</a>"
    content += "<a href='/izin' class='btn btn-info btn-animate'>Input Izin/Sakit</a>"
    content += """
      </div>
    </div>
    """
    return render_template_string(base_html, title="Dashboard", content=content)

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method=="POST":
        u,p=request.form["u"],request.form["p"]
        with sqlite3.connect(DB_NAME) as conn:
            c=conn.cursor(); c.execute("SELECT * FROM users WHERE username=?",(u,))
            row=c.fetchone()
            if row and check_password_hash(row[2],p):
                session["user"]=u; session["role"]=row[3]; return redirect(url_for("index"))
        error = "❌ Login gagal!"
    content=f"""
    <div class='card p-4 shadow fade-in' style='max-width:400px;margin:auto;'>
      <h3 class='mb-3'>Login</h3>
      <form method='post' onsubmit="document.getElementById('spinner').style.display='block'">
        <div class='mb-2'><input class='form-control' name='u' placeholder='Username'></div>
        <div class='mb-2'><input class='form-control' type='password' name='p' placeholder='Password'></div>
        <button class='btn btn-primary btn-animate w-100'>Login</button>
        <div id='spinner' class='loading-spinner mt-3'></div>
      </form>
      <div class='text-danger mt-2'>{error}</div>
      <a href='/' class='btn btn-link mt-3 btn-animate'>Kembali</a>
    </div>
    """
    return render_template_string(base_html,title="Login",content=content)

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

# ==== GURU ====
@app.route("/tambah_siswa", methods=["GET","POST"])
def tambah_siswa():
    if session.get("role")!="guru": return "Akses ditolak!"
    if request.method=="POST":
        nama=request.form["nama"]
        with sqlite3.connect(DB_NAME) as conn:
            c=conn.cursor(); c.execute("INSERT INTO siswa(nama) VALUES(?)",(nama,)); conn.commit()
        return redirect(url_for("tambah_siswa"))
    with sqlite3.connect(DB_NAME) as conn:
        c=conn.cursor(); c.execute("SELECT * FROM siswa"); siswa=c.fetchall()
    rows="".join([f"<tr><td>{s[0]}</td><td>{s[1]}</td><td><a href='/qr/{s[0]}' class='btn btn-sm btn-outline-success btn-animate'>Download QR</a></td></tr>" for s in siswa])
    content=f"""
    <div class='card p-4 shadow fade-in'>
      <h3>Tambah Siswa</h3>
      <form method='post' class='mb-3 d-flex gap-2'>
        <input class='form-control' name='nama' placeholder='Nama siswa'>
        <button class='btn btn-success btn-animate'>Tambah</button>
      </form>
      <table class='table table-bordered'><tr><th>ID</th><th>Nama</th><th>QR</th></tr>{rows}</table>
      <a href='/' class='btn btn-link btn-animate mt-2'>Kembali</a>
    </div>
    """
    return render_template_string(base_html,title="Tambah Siswa",content=content)

@app.route("/qr/<int:sid>")
def qr(sid):
    with sqlite3.connect(DB_NAME) as conn:
        c=conn.cursor(); c.execute("SELECT nama FROM siswa WHERE id=?",(sid,)); row=c.fetchone()
    if not row: return "Siswa tidak ada"
    img=qrcode.make(str(sid)); buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    return app.response_class(buf,mimetype="image/png")

@app.route("/rekap")
def rekap():
    if session.get("role")!="guru": return "Akses ditolak!"
    with sqlite3.connect(DB_NAME) as conn:
        c=conn.cursor()
        c.execute("""
            SELECT absensi.id, siswa.nama, absensi.waktu, absensi.petugas, absensi.status
            FROM absensi
            JOIN siswa ON absensi.siswa_id=siswa.id
            ORDER BY absensi.waktu DESC
        """)
        data=c.fetchall()
    grouped = defaultdict(list)
    for d in data:
        tanggal = d[2][:10]
        grouped[tanggal].append(d)
    tables = ""
    for tanggal, items in grouped.items():
        rows = "".join([
            f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2][11:]}</td><td>{d[3]}</td><td>{d[4]}</td>"
            f"<td><form method='post' action='/hapus_absen/{d[0]}' style='display:inline;' onsubmit=\"return confirm('Hapus data absen?');\">"
            "<button class='btn btn-sm btn-danger btn-animate'>Hapus</button></form></td></tr>"
            for d in items
        ])
        tables += f"""
        <div class='mb-4 fade-in'>
          <div class='d-flex justify-content-between align-items-center mb-2'>
            <h5 class='mb-0'>Tanggal: {tanggal}</h5>
            <a href='/download_excel/{tanggal}' class='btn btn-sm btn-success btn-animate'>Download Excel</a>
          </div>
          <table class='table table-striped table-bordered'>
            <thead class='table-dark'><tr>
              <th>ID</th><th>Nama</th><th>Jam</th><th>Petugas</th><th>Status</th><th>Aksi</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """
    content=f"""
    <div class='card p-4 shadow fade-in'>
      <h3>Rekap Absensi</h3>
      {tables if tables else "<div class='alert alert-info'>Belum ada data absensi.</div>"}
      <a href='/' class='btn btn-link btn-animate btn-kembali mt-2'>Kembali</a>
    </div>
    """
    return render_template_string(base_html,title="Rekap",content=content)

@app.route("/download_excel/<tanggal>")
def download_excel(tanggal):
    if session.get("role")!="guru": return "Akses ditolak!"
    with sqlite3.connect(DB_NAME) as conn:
        c=conn.cursor()
        c.execute("""
            SELECT absensi.id, siswa.nama, absensi.waktu, absensi.petugas, absensi.status
            FROM absensi
            JOIN siswa ON absensi.siswa_id=siswa.id
            WHERE absensi.waktu LIKE ?
            ORDER BY absensi.waktu ASC
        """, (f"{tanggal}%",))
        data = c.fetchall()
    wb = Workbook()
    ws = wb.active
    ws.title = f"Rekap {tanggal}"
    ws.append(["ID", "Nama", "Waktu", "Petugas", "Status"])
    for row in data:
        ws.append([row[0], row[1], row[2], row[3], row[4]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"rekap_{tanggal}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/hapus_absen/<int:aid>", methods=["POST"])
def hapus_absen(aid):
    if session.get("role")!="guru": return "Akses ditolak!"
    with sqlite3.connect(DB_NAME) as conn:
        c=conn.cursor(); c.execute("DELETE FROM absensi WHERE id=?",(aid,)); conn.commit()
    return redirect(url_for("rekap"))

# ==== SCAN QR ====
@app.route("/scan", methods=["GET","POST"])
def scan():
    if session.get("role") not in ["sekre","ketua","guru"]: return "Akses ditolak!"
    msg = ""
    if request.method=="POST":
        sid=request.form["sid"]
        with sqlite3.connect(DB_NAME) as conn:
            c=conn.cursor(); c.execute("SELECT nama FROM siswa WHERE id=?",(sid,)); row=c.fetchone()
            if row:
                waktu=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Status otomatis Hadir
                c.execute("INSERT INTO absensi(siswa_id,waktu,petugas,status) VALUES(?,?,?,?)",(sid,waktu,session["user"],"Hadir")); conn.commit()
                msg = f"<div class='alert alert-success fade-in'>✅ Absen {row[0]} berhasil oleh {session['user']}!</div>"
            else:
                msg = "<div class='alert alert-danger fade-in'>❌ Siswa tidak ditemukan!</div>"
    content=f"""
    <div class='card p-4 shadow fade-in' style='max-width:400px;margin:auto;'>
      <h3>Scan QR</h3>
      {msg}
      <div id="reader" style="width:300px"></div>
      <form method='post' id='formscan'>
        <input type='hidden' name='sid' id='sid'>
      </form>
      <div id='spinner' class='loading-spinner mt-3'></div>
      <a href='/' class='btn btn-link btn-animate btn-kembali mt-3'>Kembali</a>
    </div>
    <script>
      function onScanSuccess(decodedText, decodedResult) {{
        document.getElementById('sid').value = decodedText;
        document.getElementById('spinner').style.display='block';
        setTimeout(function(){{
          document.getElementById('formscan').submit();
        }}, 600);
      }}
      var html5QrcodeScanner = new Html5QrcodeScanner("reader", {{ fps: 10, qrbox: 200 }});
      html5QrcodeScanner.render(onScanSuccess);
    </script>
    """
    return render_template_string(base_html,title="Scan",content=content)

@app.route("/izin", methods=["GET","POST"])
def izin():
    if session.get("role") not in ["guru","sekre","ketua"]: return "Akses ditolak!"
    msg = ""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id, nama FROM siswa")
        siswa = c.fetchall()
    if request.method == "POST":
        sid = request.form["sid"]
        status = request.form["status"]
        waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO absensi(siswa_id,waktu,petugas,status) VALUES(?,?,?,?)",
                      (sid, waktu, session["user"], status))
            conn.commit()
        msg = f"<div class='alert alert-success fade-in'>✅ Status {status} berhasil dicatat!</div>"
    siswa_options = "".join([f"<option value='{s[0]}'>{s[1]}</option>" for s in siswa])
    status_options = "<option value='Sakit'>Sakit</option><option value='Izin'>Izin</option>"
    content = f"""
    <div class='card p-4 shadow fade-in' style='max-width:400px;margin:auto;'>
      <h3>Input Izin/Sakit</h3>
      {msg}
      <form method='post' class='mb-3'>
        <div class='mb-2'>
          <select class='form-select' name='sid' required>
            <option value=''>Pilih Siswa</option>
            {siswa_options}
          </select>
        </div>
        <div class='mb-2'>
          <select class='form-select' name='status' required>
            <option value=''>Pilih Status</option>
            {status_options}
          </select>
        </div>
        <button class='btn btn-info btn-animate w-100'>Simpan</button>
      </form>
      <a href='/' class='btn btn-link btn-animate btn-kembali mt-3'>Kembali</a>
    </div>
    """
    return render_template_string(base_html, title="Input Izin/Sakit", content=content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
