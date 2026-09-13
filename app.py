
import os, sqlite3, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template, flash, jsonify

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY", secrets.token_hex(32))
DB=os.environ.get("MONEYPLAY_DB","moneyplay.db")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
      pix_type TEXT, pix_key TEXT, coins INTEGER DEFAULT 0,
      vip TEXT DEFAULT 'FREE', vip_until TEXT, created_at TEXT NOT NULL,
      banned INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS tasks(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
      kind TEXT NOT NULL, reward INTEGER NOT NULL, vip_only INTEGER DEFAULT 0,
      link TEXT, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS submissions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id INTEGER,
      proof TEXT, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 1,
      created_at TEXT NOT NULL, reviewed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS withdrawals(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
      amount_cents INTEGER, status TEXT DEFAULT 'pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    """)
    if c.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"]==0:
        c.executemany("INSERT INTO tasks(title,kind,reward,vip_only,link) VALUES(?,?,?,?,?)",[
          ("Baixar aplicativo","baixar",500,0,"https://example.com"),
          ("Curtir vídeo","curtir",250,0,"https://example.com"),
          ("Assistir vídeo","assistir",300,0,"https://example.com"),
          ("Tarefa VIP exclusiva","especial",800,1,"https://example.com")])
    c.commit(); c.close()
init()

def user():
    if "uid" not in session: return None
    c=db(); u=c.execute("SELECT * FROM users WHERE id=?",(session["uid"],)).fetchone(); c.close()
    return u

def vip_plan(u):
    if not u: return ("FREE", 3, None)
    vip = u["vip"] or "FREE"
    until = datetime.fromisoformat(u["vip_until"]) if u["vip_until"] else None
    if vip != "FREE" and until and until <= datetime.utcnow():
        c=db(); c.execute("UPDATE users SET vip='FREE',vip_until=NULL WHERE id=?",(u["id"],)); c.commit(); c.close()
        return ("FREE", 3, None)
    if vip == "WEEKLY": return (vip, 8, until)
    if vip == "MONTHLY": return (vip, 15, until)
    return ("FREE", 3, None)

def daily_task_count(user_id):
    today=datetime.utcnow().date().isoformat()
    c=db(); row=c.execute("SELECT COUNT(DISTINCT task_id) n FROM submissions WHERE user_id=? AND substr(created_at,1,10)=?",(user_id,today)).fetchone(); c.close()
    return row["n"]

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if not user(): return redirect(url_for("login"))
        return f(*a,**k)
    return w

def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        if session.get("admin")!=True: return redirect(url_for("admin_login"))
        return f(*a,**k)
    return w

@app.context_processor
def ctx(): return {"me":user()}

@app.route("/")
def home():
    c=db(); tasks=c.execute("SELECT * FROM tasks WHERE active=1 ORDER BY id DESC").fetchall(); c.close()
    return render_template("home.html",tasks=tasks)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower(); pw=request.form["password"]
        if len(pw)<6: flash("A senha precisa ter pelo menos 6 caracteres."); return render_template("auth.html",mode="register")
        try:
            c=db(); c.execute("INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)",(name,email,pw,datetime.utcnow().isoformat())); uid=c.lastrowid; c.commit(); c.close()
            session["uid"]=uid; return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.")
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE email=? AND password=?",(request.form["email"].lower(),request.form["password"])).fetchone(); c.close()
        if not u or u["banned"]: flash("Login inválido ou conta bloqueada."); return render_template("auth.html",mode="login")
        session["uid"]=u["id"]; return redirect(url_for("dashboard"))
    return render_template("auth.html",mode="login")

@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    c=db(); tasks=c.execute("SELECT * FROM tasks WHERE active=1 ORDER BY vip_only,id DESC").fetchall()
    rank=c.execute("SELECT name,coins FROM users WHERE banned=0 ORDER BY coins DESC LIMIT 10").fetchall()
    c.close(); return render_template("dashboard.html",tasks=tasks,rank=rank)

@app.post("/task/<int:tid>/start")
@login_required
def start_task(tid):
    u=user(); c=db(); t=c.execute("SELECT * FROM tasks WHERE id=? AND active=1",(tid,)).fetchone()
    if not t: c.close(); flash("Tarefa indisponível."); return redirect(url_for("dashboard"))
    if t["vip_only"] and u["vip"]=="FREE": c.close(); flash("Esta tarefa é exclusiva para VIP."); return redirect(url_for("dashboard"))
    # A submission represents the user's proof/claim. Admin approval releases coins.
    plan, daily_limit, _ = vip_plan(u)
    used = daily_task_count(u["id"])
    already_started = c.execute("SELECT 1 FROM submissions WHERE user_id=? AND task_id=? AND substr(created_at,1,10)=? LIMIT 1",(u["id"],tid,datetime.utcnow().date().isoformat())).fetchone()
    if not already_started and used >= daily_limit:
        c.close(); flash(f"Seu limite de hoje é de {daily_limit} tarefas."); return redirect(url_for("dashboard"))
    attempts=c.execute("SELECT COUNT(*) n FROM submissions WHERE user_id=? AND task_id=?",(u["id"],tid)).fetchone()["n"]
    if attempts>=2: c.close(); flash("Limite de 2 tentativas atingido para esta tarefa."); return redirect(url_for("dashboard"))
    proof=request.form.get("proof","").strip()
    if not proof: c.close(); flash("Envie a prova/observação da tarefa."); return redirect(url_for("dashboard"))
    c.execute("INSERT INTO submissions(user_id,task_id,proof,attempts,created_at) VALUES(?,?,?,?,?)",(u["id"],tid,proof,attempts+1,datetime.utcnow().isoformat()))
    c.commit(); c.close(); flash("Estamos analisando o seu print, aguarde."); return redirect(url_for("dashboard"))

@app.get("/wallet")
@login_required
def wallet():
    u=user(); c=db(); ws=c.execute("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall(); c.close()
    return render_template("wallet.html",withdrawals=ws)

@app.post("/pix")
@login_required
def pix():
    u=user(); typ=request.form["pix_type"]; key=request.form["pix_key"].strip()
    if typ not in ("celular","email","aleatoria"): flash("Tipo de chave inválido."); return redirect(url_for("wallet"))
    if typ=="email" and ("@" not in key or "." not in key): flash("E-mail Pix inválido."); return redirect(url_for("wallet"))
    if typ=="celular" and len("".join(x for x in key if x.isdigit()))<10: flash("Celular Pix inválido."); return redirect(url_for("wallet"))
    if len(key)<8: flash("Chave Pix inválida."); return redirect(url_for("wallet"))
    c=db(); c.execute("UPDATE users SET pix_type=?,pix_key=? WHERE id=?",(typ,key,u["id"])); c.commit(); c.close()
    flash("Chave Pix cadastrada com sucesso."); return redirect(url_for("wallet"))

@app.post("/withdraw")
@login_required
def withdraw():
    u=user()
    cents=int(request.form.get("amount_cents","0"))
    if cents not in (200,500,1000,2000): flash("Valor de saque inválido."); return redirect(url_for("wallet"))
    required=cents*10 # demo rate: 1.000 coins = R$1
    if u["coins"]<required: flash("Saldo insuficiente."); return redirect(url_for("wallet"))
    if not u["pix_key"]: flash("Cadastre sua chave Pix primeiro."); return redirect(url_for("wallet"))
    c=db(); c.execute("UPDATE users SET coins=coins-? WHERE id=?",(required,u["id"]))
    c.execute("INSERT INTO withdrawals(user_id,amount_cents,created_at) VALUES(?,?,?)",(u["id"],cents,datetime.utcnow().isoformat()))
    c.commit(); c.close(); flash("Saque solicitado. O pagamento fica pendente para processamento."); return redirect(url_for("wallet"))

@app.get("/vip")
@login_required
def vip(): return render_template("vip.html")

@app.post("/vip/subscribe")
@login_required
def subscribe():
    flash("O VIP é ativado manualmente após a confirmação do Pix.")
    return redirect(url_for("vip"))

@app.post("/admin/user/<int:uid>/vip")
@admin_required
def set_vip(uid):
    plan=request.form.get("plan")
    days=7 if plan=="WEEKLY" else 30 if plan=="MONTHLY" else 0
    c=db()
    if days:
        until=(datetime.utcnow()+timedelta(days=days)).isoformat()
        c.execute("UPDATE users SET vip=?,vip_until=? WHERE id=?",(plan,until,uid))
        flash("VIP ativado com sucesso.")
    else:
        c.execute("UPDATE users SET vip='FREE',vip_until=NULL WHERE id=?",(uid,))
        flash("VIP removido.")
    c.commit(); c.close(); return redirect(url_for("admin"))

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if request.form["password"]==os.environ.get("ADMIN_PASSWORD","troque-esta-senha"):
            session["admin"]=True; return redirect(url_for("admin"))
        flash("Senha do ADM incorreta.")
    return render_template("admin_login.html")

@app.get("/admin/logout")
def admin_logout(): session.pop("admin",None); return redirect(url_for("home"))

@app.get("/admin")
@admin_required
def admin():
    c=db()
    subs=c.execute("""SELECT s.*,u.name,u.email,t.title,t.reward FROM submissions s JOIN users u ON u.id=s.user_id JOIN tasks t ON t.id=s.task_id ORDER BY s.id DESC""").fetchall()
    ws=c.execute("""SELECT w.*,u.name,u.email,u.pix_type,u.pix_key,u.vip FROM withdrawals w JOIN users u ON u.id=w.user_id ORDER BY w.id DESC""").fetchall()
    users=c.execute("SELECT id,name,email,coins,vip,banned FROM users ORDER BY id DESC").fetchall()
    tasks=c.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall(); c.close()
    return render_template("admin.html",subs=subs,ws=ws,users=users,tasks=tasks)

@app.post("/admin/submission/<int:sid>/<action>")
@admin_required
def review(sid,action):
    if action not in ("approve","reject"): return redirect(url_for("admin"))
    c=db(); s=c.execute("SELECT s.*,t.reward FROM submissions s JOIN tasks t ON t.id=s.task_id WHERE s.id=?",(sid,)).fetchone()
    if not s or s["status"]!="pending": c.close(); return redirect(url_for("admin"))
    status="approved" if action=="approve" else "rejected"
    c.execute("UPDATE submissions SET status=?,reviewed_at=? WHERE id=?",(status,datetime.utcnow().isoformat(),sid))
    if action=="approve": c.execute("UPDATE users SET coins=coins+? WHERE id=?",(s["reward"],s["user_id"]))
    c.commit(); c.close(); return redirect(url_for("admin"))

@app.post("/admin/withdrawal/<int:wid>/paid")
@admin_required
def mark_withdrawal_paid(wid):
    c=db()
    w=c.execute("SELECT * FROM withdrawals WHERE id=?",(wid,)).fetchone()
    if w and w["status"]=="pending":
        c.execute("UPDATE withdrawals SET status='paid' WHERE id=?",(wid,))
        c.commit()
    c.close()
    return redirect(url_for("admin"))

@app.post("/admin/withdrawal/<int:wid>/cancel")
@admin_required
def cancel_withdrawal(wid):
    c=db()
    w=c.execute("SELECT * FROM withdrawals WHERE id=?",(wid,)).fetchone()
    if w and w["status"]=="pending":
        c.execute("UPDATE withdrawals SET status='cancelled' WHERE id=?",(wid,))
        # Return the reserved coins when ADM cancels the request.
        c.execute("UPDATE users SET coins=coins+? WHERE id=?",(w["amount_cents"]*10,w["user_id"]))
        c.commit()
    c.close()
    return redirect(url_for("admin"))

@app.post("/admin/user/<int:uid>/<action>")
@admin_required
def ban(uid,action):
    c=db(); c.execute("UPDATE users SET banned=? WHERE id=?",(1 if action=="ban" else 0,uid)); c.commit(); c.close(); return redirect(url_for("admin"))

@app.post("/admin/task")
@admin_required
def add_task():
    c=db(); c.execute("INSERT INTO tasks(title,kind,reward,vip_only,link) VALUES(?,?,?,?,?)",(request.form["title"],request.form["kind"],int(request.form["reward"]),1 if request.form.get("vip_only") else 0,request.form.get("link",""))); c.commit(); c.close(); return redirect(url_for("admin"))

@app.post("/admin/task/<int:tid>/toggle")
@admin_required
def toggle_task(tid):
    c=db(); c.execute("UPDATE tasks SET active=1-active WHERE id=?",(tid,)); c.commit(); c.close(); return redirect(url_for("admin"))

@app.get("/health")
def health(): return jsonify(ok=True,app="Money Play")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
