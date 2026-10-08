import sqlite3, csv, shutil
from datetime import date, datetime, timedelta
from calendar import monthrange
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB = "kisti_hisab.db"

def db():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    return con

def money(x):
    try: return f"{float(x):,.2f}"
    except: return "0.00"

def add_months(d, n):
    y = d.year + (d.month-1+n)//12
    m = (d.month-1+n)%12 + 1
    day = min(d.day, monthrange(y,m)[1])
    return date(y,m,day)

def init_db():
    con=db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
      id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT NOT NULL,
      nid TEXT, mobile TEXT, address TEXT, nominee TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS loans(
      id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, scheme TEXT,
      loan_no TEXT, principal REAL, rate REAL, service REAL, installment REAL,
      count INTEGER, frequency TEXT, start_date TEXT, created_at TEXT,
      FOREIGN KEY(customer_id) REFERENCES customers(id));
    CREATE TABLE IF NOT EXISTS loan_schedule(
      id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER, no INTEGER,
      due_date TEXT, amount REAL, paid REAL DEFAULT 0,
      FOREIGN KEY(loan_id) REFERENCES loans(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS dps(
      id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, dps_no TEXT,
      monthly REAL, term INTEGER, rate REAL, start_date TEXT, created_at TEXT,
      FOREIGN KEY(customer_id) REFERENCES customers(id));
    CREATE TABLE IF NOT EXISTS dps_schedule(
      id INTEGER PRIMARY KEY AUTOINCREMENT, dps_id INTEGER, no INTEGER,
      due_date TEXT, amount REAL, paid REAL DEFAULT 0,
      FOREIGN KEY(dps_id) REFERENCES dps(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS collections(
      id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, product_type TEXT,
      product_id INTEGER, schedule_id INTEGER, amount REAL, method TEXT,
      note TEXT, paid_at TEXT, receipt_no TEXT,
      FOREIGN KEY(customer_id) REFERENCES customers(id));
    CREATE TABLE IF NOT EXISTS settings(
      key TEXT PRIMARY KEY, value TEXT);
    """)
    for k,v in [("org_name","আমার কিস্তি হিসাব"),("org_address",""),("org_phone","")]:
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    con.commit(); con.close()

def get_setting(k):
    con=db(); r=con.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone(); con.close()
    return r[0] if r else ""

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("কিস্তি হিসাব - Advanced Desktop")
        self.geometry("1250x760")
        self.minsize(1100,650)
        self.style=ttk.Style(self)
        try: self.style.theme_use("clam")
        except: pass
        self.customer_map={}
        self.loan_map={}
        self.dps_map={}
        self.build()

    def build(self):
        top=ttk.Frame(self,padding=10); top.pack(fill="x")
        ttk.Label(top,text=get_setting("org_name"),font=("Arial",20,"bold")).pack(side="left")
        ttk.Button(top,text="Backup",command=self.backup).pack(side="right",padx=4)
        ttk.Button(top,text="Settings",command=self.settings).pack(side="right",padx=4)
        self.nb=ttk.Notebook(self); self.nb.pack(fill="both",expand=True,padx=10,pady=5)
        self.dashboard_tab(); self.customer_tab(); self.loan_tab(); self.dps_tab(); self.collection_tab(); self.report_tab()

    def dashboard_tab(self):
        f=ttk.Frame(self.nb,padding=15); self.nb.add(f,text="📊 ড্যাশবোর্ড")
        self.cards={}
        names=["গ্রাহক","ঋণ","DPS","ঋণ আদায়","ঋণ বকেয়া","DPS বকেয়া"]
        for i,n in enumerate(names):
            box=ttk.LabelFrame(f,text=n,padding=18); box.grid(row=0,column=i,padx=5,sticky="nsew")
            v=ttk.Label(box,text="0",font=("Arial",18,"bold")); v.pack(); self.cards[n]=v
            f.columnconfigure(i,weight=1)
        ttk.Label(f,text="নোট: Grameen/Bank/DPS এখানে configurable projection হিসেবে হিসাব করা হয়; নির্দিষ্ট প্রতিষ্ঠানের official formula নয়.",
                  foreground="#8a3b00").grid(row=1,column=0,columnspan=6,pady=20)
        ttk.Button(f,text="Refresh Dashboard",command=self.refresh).grid(row=2,column=0,pady=5)
        self.refresh()

    def customer_tab(self):
        f=ttk.Frame(self.nb,padding=10); self.nb.add(f,text="👤 গ্রাহক")
        form=ttk.LabelFrame(f,text="নতুন গ্রাহক",padding=10); form.pack(fill="x")
        labels=["Code","Name","NID","Mobile","Address","Nominee"]; self.cvars=[tk.StringVar() for _ in labels]
        for i,(lab,var) in enumerate(zip(labels,self.cvars)):
            ttk.Label(form,text=lab).grid(row=i//3*2,column=i%3*2,padx=5,pady=4,sticky="w")
            ttk.Entry(form,textvariable=var,width=28).grid(row=i//3*2,column=i%3*2+1,padx=5,pady=4,sticky="ew")
        ttk.Button(form,text="Save Customer",command=self.add_customer).grid(row=4,column=4,padx=5)
        self.ct=ttk.Treeview(f,columns=("id","code","name","nid","mobile","address","nominee"),show="headings")
        for c,h,w in zip(self.ct["columns"],["ID","Code","Name","NID","Mobile","Address","Nominee"],[50,100,180,130,120,260,150]):
            self.ct.heading(c,text=h); self.ct.column(c,width=w)
        self.ct.pack(fill="both",expand=True,pady=10)
        self.refresh_customers()

    def add_customer(self):
        code,name=self.cvars[0].get().strip(),self.cvars[1].get().strip()
        if not code or not name: return messagebox.showwarning("প্রয়োজন","Code ও Name দিন")
        try:
            con=db(); con.execute("INSERT INTO customers(code,name,nid,mobile,address,nominee,created_at) VALUES(?,?,?,?,?,?,?)",
                (code,name,*[v.get().strip() for v in self.cvars[2:]],datetime.now().isoformat(timespec="seconds"))); con.commit(); con.close()
            for v in self.cvars: v.set("")
            self.refresh_customers(); self.refresh()
        except sqlite3.IntegrityError: messagebox.showerror("ভুল","এই Code আগে থেকেই আছে")

    def refresh_customers(self):
        for x in self.ct.get_children(): self.ct.delete(x)
        con=db(); rows=con.execute("SELECT id,code,name,nid,mobile,address,nominee FROM customers ORDER BY id DESC").fetchall(); con.close()
        for r in rows: self.ct.insert("", "end", values=r)

    def customer_combo(self):
        con=db(); rows=con.execute("SELECT id,code,name FROM customers ORDER BY name").fetchall(); con.close()
        self.customer_map={f"{r[1]} - {r[2]}":r[0] for r in rows}; return list(self.customer_map)

    def loan_tab(self):
        f=ttk.Frame(self.nb,padding=10); self.nb.add(f,text="💳 Loan / Grameen / Bank")
        form=ttk.LabelFrame(f,text="নতুন ঋণ",padding=10); form.pack(fill="x")
        self.lc=tk.StringVar(); self.scheme=tk.StringVar(value="Grameen"); self.lno=tk.StringVar()
        self.lp=tk.StringVar(); self.lr=tk.StringVar(value="20"); self.ls=tk.StringVar(value="0"); self.li=tk.StringVar()
        self.lcount=tk.StringVar(value="10"); self.lfreq=tk.StringVar(value="সাপ্তাহিক"); self.lstart=tk.StringVar(value=date.today().isoformat())
        fields=[("Customer",self.lc),("Scheme",self.scheme),("Loan No",self.lno),("Principal",self.lp),("Rate %",self.lr),
                ("Service",self.ls),("Installment",self.li),("Count",self.lcount),("Frequency",self.lfreq),("Start YYYY-MM-DD",self.lstart)]
        for i,(lab,var) in enumerate(fields):
            ttk.Label(form,text=lab).grid(row=i//5*2,column=i%5*2,sticky="w",padx=4,pady=3)
            if lab=="Customer": w=ttk.Combobox(form,textvariable=var,values=self.customer_combo(),width=22)
            elif lab=="Scheme": w=ttk.Combobox(form,textvariable=var,values=["Grameen","Bank","Personal"],state="readonly",width=14)
            elif lab=="Frequency": w=ttk.Combobox(form,textvariable=var,values=["দৈনিক","সাপ্তাহিক","মাসিক"],state="readonly",width=12)
            else: w=ttk.Entry(form,textvariable=var,width=14)
            w.grid(row=i//5*2,column=i%5*2+1,padx=4,pady=3)
        ttk.Button(form,text="Create Loan Schedule",command=self.add_loan).grid(row=4,column=8,padx=8)
        self.lt=ttk.Treeview(f,columns=("id","customer","scheme","loan","principal","total","inst","freq","count","paid","due","start"),show="headings")
        heads=["ID","Customer","Scheme","Loan No","Principal","Total","Installment","Frequency","Count","Paid","Due","Start"]
        widths=[45,150,90,100,100,100,100,90,60,100,100,100]
        for c,h,w in zip(self.lt["columns"],heads,widths): self.lt.heading(c,text=h); self.lt.column(c,width=w)
        self.lt.pack(fill="both",expand=True,pady=10); self.refresh_loans()

    def add_loan(self):
        try:
            cid=self.customer_map[self.lc.get()]; p=float(self.lp.get()); rate=float(self.lr.get() or 0); service=float(self.ls.get() or 0); count=int(self.lcount.get())
            if count<=0: raise ValueError()
            total=p+p*rate/100+service; inst=float(self.li.get()) if self.li.get() else total/count
            start=date.fromisoformat(self.lstart.get())
            con=db(); cur=con.execute("INSERT INTO loans(customer_id,scheme,loan_no,principal,rate,service,installment,count,frequency,start_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (cid,self.scheme.get(),self.lno.get(),p,rate,service,inst,count,self.lfreq.get(),start.isoformat(),datetime.now().isoformat(timespec="seconds"))); lid=cur.lastrowid
            for n in range(1,count+1):
                if self.lfreq.get()=="দৈনিক": due=start+timedelta(days=n-1)
                elif self.lfreq.get()=="সাপ্তাহিক": due=start+timedelta(days=(n-1)*7)
                else: due=add_months(start,n-1)
                amt=inst if n<count else total-inst*(count-1)
                con.execute("INSERT INTO loan_schedule(loan_id,no,due_date,amount) VALUES(?,?,?,?)",(lid,n,due.isoformat(),amt))
            con.commit(); con.close(); self.refresh_loans(); self.refresh()
            messagebox.showinfo("সফল",f"ঋণ তৈরি হয়েছে। মোট: {money(total)}")
        except Exception as e: messagebox.showerror("ভুল",f"তথ্য যাচাই করুন।\n{e}")

    def refresh_loans(self):
        self.customer_map=dict(self.customer_map)
        for x in self.lt.get_children(): self.lt.delete(x)
        con=db()
        rows=con.execute("""SELECT l.id,c.code||' - '||c.name,l.scheme,l.loan_no,l.principal,
        (l.principal+l.principal*l.rate/100+l.service),l.installment,l.frequency,l.count,
        COALESCE((SELECT SUM(amount) FROM collections WHERE product_type='Loan' AND product_id=l.id),0),
        MAX(0,(l.principal+l.principal*l.rate/100+l.service)-COALESCE((SELECT SUM(amount) FROM collections WHERE product_type='Loan' AND product_id=l.id),0)),
        l.start_date FROM loans l JOIN customers c ON c.id=l.customer_id ORDER BY l.id DESC""").fetchall()
        con.close()
        for r in rows: self.lt.insert("", "end", values=(r[0],r[1],r[2],r[3],money(r[4]),money(r[5]),money(r[6]),r[7],r[8],money(r[9]),money(r[10]),r[11]))

    def dps_tab(self):
        f=ttk.Frame(self.nb,padding=10); self.nb.add(f,text="🏦 DPS")
        form=ttk.LabelFrame(f,text="নতুন DPS",padding=10); form.pack(fill="x")
        self.dc=tk.StringVar(); self.dno=tk.StringVar(); self.dm=tk.StringVar(); self.dt=tk.StringVar(value="12"); self.dr=tk.StringVar(value="8"); self.ds=tk.StringVar(value=date.today().isoformat())
        fields=[("Customer",self.dc),("DPS No",self.dno),("Monthly",self.dm),("Term Months",self.dt),("Rate %",self.dr),("Start YYYY-MM-DD",self.ds)]
        for i,(lab,var) in enumerate(fields):
            ttk.Label(form,text=lab).grid(row=0,column=i*2,padx=5,pady=4)
            if lab=="Customer": w=ttk.Combobox(form,textvariable=var,values=self.customer_combo(),width=20)
            else: w=ttk.Entry(form,textvariable=var,width=15)
            w.grid(row=0,column=i*2+1,padx=5,pady=4)
        ttk.Button(form,text="Create DPS Schedule",command=self.add_dps).grid(row=1,column=10,padx=5)
        self.dtview=ttk.Treeview(f,columns=("id","customer","dps","monthly","term","rate","total","paid","due","start"),show="headings")
        for c,h,w in zip(self.dtview["columns"],["ID","Customer","DPS No","Monthly","Term","Rate %","Projection","Paid","Due","Start"],[45,170,100,100,70,70,110,110,110,100]):
            self.dtview.heading(c,text=h); self.dtview.column(c,width=w)
        self.dtview.pack(fill="both",expand=True,pady=10); self.refresh_dps()

    def add_dps(self):
        try:
            cid=self.customer_map[self.dc.get()]; monthly=float(self.dm.get()); term=int(self.dt.get()); rate=float(self.dr.get() or 0); start=date.fromisoformat(self.ds.get())
            if monthly<=0 or term<=0: raise ValueError("Monthly/Term ভুল")
            con=db(); cur=con.execute("INSERT INTO dps(customer_id,dps_no,monthly,term,rate,start_date,created_at) VALUES(?,?,?,?,?,?,?)",(cid,self.dno.get(),monthly,term,rate,start.isoformat(),datetime.now().isoformat(timespec="seconds"))); did=cur.lastrowid
            for n in range(1,term+1): con.execute("INSERT INTO dps_schedule(dps_id,no,due_date,amount) VALUES(?,?,?,?)",(did,n,add_months(start,n-1).isoformat(),monthly))
            con.commit(); con.close(); self.refresh_dps(); self.refresh()
        except Exception as e: messagebox.showerror("ভুল",str(e))

    def refresh_dps(self):
        for x in self.dtview.get_children(): self.dtview.delete(x)
        con=db(); rows=con.execute("""SELECT d.id,c.code||' - '||c.name,d.dps_no,d.monthly,d.term,d.rate,
        d.monthly*d.term*(1+d.rate/100),
        COALESCE((SELECT SUM(amount) FROM collections WHERE product_type='DPS' AND product_id=d.id),0),
        MAX(0,d.monthly*d.term-COALESCE((SELECT SUM(amount) FROM collections WHERE product_type='DPS' AND product_id=d.id),0)),d.start_date
        FROM dps d JOIN customers c ON c.id=d.customer_id ORDER BY d.id DESC""").fetchall(); con.close()
        for r in rows: self.dtview.insert("", "end", values=(r[0],r[1],r[2],money(r[3]),r[4],r[5],money(r[6]),money(r[7]),money(r[8]),r[9]))

    def collection_tab(self):
        f=ttk.Frame(self.nb,padding=10); self.nb.add(f,text="💰 আদায়")
        form=ttk.LabelFrame(f,text="কিস্তি / DPS আদায়",padding=10); form.pack(fill="x")
        self.ptype=tk.StringVar(value="Loan"); self.pno=tk.StringVar(); self.pa=tk.StringVar(); self.pm=tk.StringVar(value="Cash"); self.pnote=tk.StringVar()
        for i,(lab,var) in enumerate([("Type",self.ptype),("Product ID",self.pno),("Amount",self.pa),("Method",self.pm),("Note",self.pnote)]):
            ttk.Label(form,text=lab).grid(row=0,column=i*2,padx=5,pady=5)
            if lab=="Type": w=ttk.Combobox(form,textvariable=var,values=["Loan","DPS"],state="readonly",width=10)
            elif lab=="Method": w=ttk.Combobox(form,textvariable=var,values=["Cash","Bank","bKash","Nagad","Other"],state="readonly",width=12)
            else: w=ttk.Entry(form,textvariable=var,width=20)
            w.grid(row=0,column=i*2+1,padx=5,pady=5)
        ttk.Button(form,text="Collect / Generate Receipt",command=self.collect).grid(row=1,column=8,pady=5)
        ttk.Label(form,text="Product ID = Loan/DPS তালিকার ID").grid(row=1,column=0,columnspan=5,sticky="w")
        self.pt=ttk.Treeview(f,columns=("id","date","type","product","amount","method","receipt","note"),show="headings")
        for c,h,w in zip(self.pt["columns"],["ID","Date","Type","Product ID","Amount","Method","Receipt","Note"],[50,160,80,100,110,90,120,250]):
            self.pt.heading(c,text=h); self.pt.column(c,width=w)
        self.pt.pack(fill="both",expand=True,pady=10); self.refresh_collections()

    def collect(self):
        try:
            typ=self.ptype.get(); pid=int(self.pno.get()); amt=float(self.pa.get()); method=self.pm.get()
            if amt<=0: raise ValueError("Amount ভুল")
            con=db()
            if typ=="Loan":
                row=con.execute("SELECT customer_id FROM loans WHERE id=?",(pid,)).fetchone()
                schedules=con.execute("SELECT id,amount,paid FROM loan_schedule WHERE loan_id=? AND paid<amount ORDER BY no",(pid,)).fetchall()
            else:
                row=con.execute("SELECT customer_id FROM dps WHERE id=?",(pid,)).fetchone()
                schedules=con.execute("SELECT id,amount,paid FROM dps_schedule WHERE dps_id=? AND paid<amount ORDER BY no",(pid,)).fetchall()
            if not row: raise ValueError("Product ID পাওয়া যায়নি")
            cid=row[0]; remaining=amt; receipt="R"+datetime.now().strftime("%Y%m%d%H%M%S")
            for sid,due,paid in schedules:
                take=min(remaining,due-paid)
                if take>0:
                    table="loan_schedule" if typ=="Loan" else "dps_schedule"
                    con.execute(f"UPDATE {table} SET paid=paid+? WHERE id=?",(take,sid))
                    con.execute("INSERT INTO collections(customer_id,product_type,product_id,schedule_id,amount,method,note,paid_at,receipt_no) VALUES(?,?,?,?,?,?,?,?,?)",
                        (cid,typ,pid,sid,take,method,self.pnote.get(),datetime.now().isoformat(timespec="seconds"),receipt))
                    remaining-=take
                if remaining<=0: break
            if remaining>0: raise ValueError("বকেয়ার চেয়ে বেশি amount দেওয়া হয়েছে")
            con.commit(); con.close(); self.pa.set(""); self.pnote.set(""); self.refresh_collections(); self.refresh_loans(); self.refresh_dps(); self.refresh()
            messagebox.showinfo("আদায় সফল",f"Receipt: {receipt}\nAmount: {money(amt)}")
        except Exception as e:
            try: con.close()
            except: pass
            messagebox.showerror("ভুল",str(e))

    def refresh_collections(self):
        for x in self.pt.get_children(): self.pt.delete(x)
        con=db(); rows=con.execute("SELECT id,paid_at,product_type,product_id,amount,method,receipt_no,note FROM collections ORDER BY id DESC LIMIT 300").fetchall(); con.close()
        for r in rows: self.pt.insert("", "end", values=(r[0],r[1],r[2],r[3],money(r[4]),r[5],r[6],r[7]))

    def report_tab(self):
        f=ttk.Frame(self.nb,padding=10); self.nb.add(f,text="📄 রিপোর্ট")
        ttk.Button(f,text="Export Customers CSV",command=lambda:self.export("customers")).pack(anchor="w",pady=5)
        ttk.Button(f,text="Export Loans CSV",command=lambda:self.export("loans")).pack(anchor="w",pady=5)
        ttk.Button(f,text="Export DPS CSV",command=lambda:self.export("dps")).pack(anchor="w",pady=5)
        ttk.Button(f,text="Export Collections CSV",command=lambda:self.export("collections")).pack(anchor="w",pady=5)

    def export(self, kind):
        queries={
        "customers":"SELECT id,code,name,nid,mobile,address,nominee,created_at FROM customers",
        "loans":"SELECT l.id,c.code,c.name,l.scheme,l.loan_no,l.principal,l.rate,l.service,l.installment,l.count,l.frequency,l.start_date FROM loans l JOIN customers c ON c.id=l.customer_id",
        "dps":"SELECT d.id,c.code,c.name,d.dps_no,d.monthly,d.term,d.rate,d.start_date FROM dps d JOIN customers c ON c.id=d.customer_id",
        "collections":"SELECT id,paid_at,customer_id,product_type,product_id,schedule_id,amount,method,note,receipt_no FROM collections"}
        con=db(); cur=con.execute(queries[kind]); rows=cur.fetchall(); headers=[x[0] for x in cur.description]; con.close()
        path=filedialog.asksaveasfilename(defaultextension=".csv",initialfile=kind+".csv",filetypes=[("CSV","*.csv")])
        if not path:return
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f); w.writerow(headers); w.writerows(rows)
        messagebox.showinfo("সফল","CSV export হয়েছে")

    def refresh(self):
        try:
            con=db()
            c=con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            l=con.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
            d=con.execute("SELECT COUNT(*) FROM dps").fetchone()[0]
            lp=con.execute("SELECT COALESCE(SUM(amount),0) FROM collections WHERE product_type='Loan'").fetchone()[0]
            ld=con.execute("""SELECT COALESCE(SUM(MAX(0, l.principal+l.principal*l.rate/100+l.service-
              COALESCE((SELECT SUM(amount) FROM collections z WHERE z.product_type='Loan' AND z.product_id=l.id),0))),0) FROM loans l""").fetchone()[0]
            dp=con.execute("SELECT COALESCE(SUM(amount),0) FROM collections WHERE product_type='DPS'").fetchone()[0]
            dd=con.execute("SELECT COALESCE(SUM(d.monthly*d.term),0)-COALESCE((SELECT SUM(amount) FROM collections WHERE product_type='DPS'),0) FROM dps d").fetchone()[0]
            con.close()
            for n,v in [("গ্রাহক",c),("ঋণ",l),("DPS",d),("ঋণ আদায়",money(lp)),("ঋণ বকেয়া",money(max(0,ld))),("DPS বকেয়া",money(max(0,dd)))]:
                self.cards[n].config(text=str(v))
            self.refresh_customers(); self.refresh_loans(); self.refresh_dps(); self.refresh_collections()
        except: pass

    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension=".db",initialfile="kisti_hisab_backup.db",filetypes=[("SQLite DB","*.db")])
        if path:
            shutil.copy2(DB,path); messagebox.showinfo("Backup","Backup সম্পন্ন হয়েছে")

    def settings(self):
        w=tk.Toplevel(self); w.title("Organization Settings"); w.geometry("500x250"); w.transient(self); w.grab_set()
        vars={k:tk.StringVar(value=get_setting(k)) for k in ["org_name","org_address","org_phone"]}
        for i,(k,v) in enumerate(vars.items()):
            ttk.Label(w,text=k).grid(row=i,column=0,padx=10,pady=10,sticky="w"); ttk.Entry(w,textvariable=v,width=40).grid(row=i,column=1,padx=10,pady=10)
        def save():
            con=db()
            for k,v in vars.items(): con.execute("UPDATE settings SET value=? WHERE key=?",(v.get(),k))
            con.commit(); con.close(); messagebox.showinfo("Saved","Settings saved"); w.destroy()
        ttk.Button(w,text="Save",command=save).grid(row=4,column=1)

class Login(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Kisti Hisab Login"); self.geometry("420x280"); self.resizable(False,False)
        f=ttk.Frame(self,padding=30); f.pack(fill="both",expand=True)
        ttk.Label(f,text="কিস্তি হিসাব",font=("Arial",22,"bold")).pack(pady=10)
        self.u=tk.StringVar(value="admin"); self.p=tk.StringVar()
        ttk.Label(f,text="Username").pack(anchor="w"); ttk.Entry(f,textvariable=self.u).pack(fill="x",pady=5)
        ttk.Label(f,text="Password").pack(anchor="w"); ttk.Entry(f,textvariable=self.p,show="*").pack(fill="x",pady=5)
        ttk.Button(f,text="Login",command=self.login).pack(pady=12)
        ttk.Label(f,text="Default: admin / 1234").pack()
    def login(self):
        if self.u.get()=="admin" and self.p.get()=="1234":
            self.destroy(); app=App(); app.mainloop()
        else: messagebox.showerror("Login","Username or password ভুল")

if __name__=="__main__":
    init_db()
    Login().mainloop()
