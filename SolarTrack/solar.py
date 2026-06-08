"""
SolarTrack Brasil — tudo em um único arquivo.

Dependências:
    pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] python-multipart pydantic-settings

Rodar:
    python solartrack.py
    Acesse: http://localhost:8000
    Login padrão: admin / admin123
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    APP_NAME: str = "SolarTrack Brasil"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./solartrack.db"
    SECRET_KEY: str = "solartrack-chave-secreta-troque-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    TARIFA_KWH: float = 0.75
    CO2_POR_KWH: float = 0.075

settings = Settings()

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String(20), default="usuario")
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    instalacoes = relationship("Instalacao", back_populates="usuario")

class Instalacao(Base):
    __tablename__ = "instalacoes"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nome = Column(String(100), nullable=False)
    localizacao = Column(String(200), nullable=False)
    capacidade_kwp = Column(Float, nullable=False)
    data_instalacao = Column(Date, nullable=False)
    descricao = Column(Text)
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    usuario = relationship("Usuario", back_populates="instalacoes")
    leituras = relationship("Leitura", back_populates="instalacao")

class Leitura(Base):
    __tablename__ = "leituras"
    id = Column(Integer, primary_key=True, index=True)
    instalacao_id = Column(Integer, ForeignKey("instalacoes.id"), nullable=False)
    data = Column(Date, nullable=False)
    kwh_produzido = Column(Float, nullable=False)
    economia_reais = Column(Float, nullable=False)
    co2_evitado_kg = Column(Float, nullable=False)
    observacao = Column(String(200))
    criado_em = Column(DateTime, server_default=func.now())
    instalacao = relationship("Instalacao", back_populates="leituras")

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    user = db.query(Usuario).filter(Usuario.username == username).first()
    if not user or not user.ativo:
        raise exc
    return user

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    nome: str
    username: str
    email: str
    password: str

class UsuarioOut(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    role: str
    ativo: bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str

class InstalacaoCreate(BaseModel):
    nome: str
    localizacao: str
    capacidade_kwp: float
    data_instalacao: date
    descricao: Optional[str] = None

class InstalacaoUpdate(BaseModel):
    nome: Optional[str] = None
    localizacao: Optional[str] = None
    capacidade_kwp: Optional[float] = None
    descricao: Optional[str] = None
    ativa: Optional[bool] = None

class InstalacaoOut(BaseModel):
    id: int
    usuario_id: int
    nome: str
    localizacao: str
    capacidade_kwp: float
    data_instalacao: date
    descricao: Optional[str]
    ativa: bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class LeituraCreate(BaseModel):
    data: date
    kwh_produzido: float
    observacao: Optional[str] = None

class LeituraOut(BaseModel):
    id: int
    instalacao_id: int
    data: date
    kwh_produzido: float
    economia_reais: float
    co2_evitado_kg: float
    observacao: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}

class RelatorioInstalacao(BaseModel):
    instalacao: InstalacaoOut
    total_leituras: int
    total_kwh_produzido: float
    total_economia_reais: float
    total_co2_evitado_kg: float
    media_kwh_dia: float
    arvores_equivalentes: float
    model_config = {"from_attributes": True}

# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ROTAS — AUTH
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/auth/registrar", response_model=UsuarioOut, tags=["Auth"])
def registrar(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.username == usuario.username).first():
        raise HTTPException(400, "Username já existe")
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(400, "Email já cadastrado")
    u = Usuario(
        nome=usuario.nome, username=usuario.username, email=usuario.email,
        hashed_password=get_password_hash(usuario.password),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u

@app.post("/auth/token", response_model=Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    if not user.ativo:
        raise HTTPException(400, "Usuário inativo")
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}

@app.get("/auth/me", response_model=UsuarioOut, tags=["Auth"])
def me(current_user=Depends(get_current_user)):
    return current_user

# ─────────────────────────────────────────────────────────────────────────────
# ROTAS — INSTALAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
def _get_instalacao(instalacao_id: int, user, db: Session):
    inst = db.query(Instalacao).filter(Instalacao.id == instalacao_id).first()
    if not inst:
        raise HTTPException(404, "Instalação não encontrada")
    if user.role != "admin" and inst.usuario_id != user.id:
        raise HTTPException(403, "Acesso negado")
    return inst

@app.post("/instalacoes/", response_model=InstalacaoOut, tags=["Instalações"])
def criar_instalacao(dados: InstalacaoCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inst = Instalacao(**dados.model_dump(), usuario_id=user.id)
    db.add(inst); db.commit(); db.refresh(inst)
    return inst

@app.get("/instalacoes/", response_model=List[InstalacaoOut], tags=["Instalações"])
def listar_instalacoes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(Instalacao)
    if user.role != "admin":
        q = q.filter(Instalacao.usuario_id == user.id)
    return q.filter(Instalacao.ativa == True).all()

@app.get("/instalacoes/{instalacao_id}", response_model=InstalacaoOut, tags=["Instalações"])
def buscar_instalacao(instalacao_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_instalacao(instalacao_id, user, db)

@app.put("/instalacoes/{instalacao_id}", response_model=InstalacaoOut, tags=["Instalações"])
def atualizar_instalacao(instalacao_id: int, dados: InstalacaoUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inst = _get_instalacao(instalacao_id, user, db)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(inst, campo, valor)
    db.commit(); db.refresh(inst)
    return inst

@app.delete("/instalacoes/{instalacao_id}", tags=["Instalações"])
def desativar_instalacao(instalacao_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inst = _get_instalacao(instalacao_id, user, db)
    inst.ativa = False; db.commit()
    return {"message": "Instalação desativada"}

# ─────────────────────────────────────────────────────────────────────────────
# ROTAS — LEITURAS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/instalacoes/{instalacao_id}/leituras/", response_model=LeituraOut, tags=["Leituras"])
def registrar_leitura(instalacao_id: int, dados: LeituraCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_instalacao(instalacao_id, user, db)
    if db.query(Leitura).filter(Leitura.instalacao_id == instalacao_id, Leitura.data == dados.data).first():
        raise HTTPException(400, "Já existe leitura para essa data")
    l = Leitura(
        instalacao_id=instalacao_id, data=dados.data,
        kwh_produzido=dados.kwh_produzido,
        economia_reais=round(dados.kwh_produzido * settings.TARIFA_KWH, 2),
        co2_evitado_kg=round(dados.kwh_produzido * settings.CO2_POR_KWH, 3),
        observacao=dados.observacao,
    )
    db.add(l); db.commit(); db.refresh(l)
    return l

@app.get("/instalacoes/{instalacao_id}/leituras/", response_model=List[LeituraOut], tags=["Leituras"])
def listar_leituras(
    instalacao_id: int,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _get_instalacao(instalacao_id, user, db)
    q = db.query(Leitura).filter(Leitura.instalacao_id == instalacao_id)
    if data_inicio: q = q.filter(Leitura.data >= data_inicio)
    if data_fim:    q = q.filter(Leitura.data <= data_fim)
    return q.order_by(Leitura.data.desc()).all()

@app.delete("/instalacoes/{instalacao_id}/leituras/{leitura_id}", tags=["Leituras"])
def deletar_leitura(instalacao_id: int, leitura_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_instalacao(instalacao_id, user, db)
    l = db.query(Leitura).filter(Leitura.id == leitura_id, Leitura.instalacao_id == instalacao_id).first()
    if not l: raise HTTPException(404, "Leitura não encontrada")
    db.delete(l); db.commit()
    return {"message": "Leitura removida"}

# ─────────────────────────────────────────────────────────────────────────────
# ROTAS — RELATÓRIOS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/relatorios/meu-resumo", tags=["Relatórios"])
def resumo_usuario(db: Session = Depends(get_db), user=Depends(get_current_user)):
    insts = db.query(Instalacao).filter(Instalacao.usuario_id == user.id, Instalacao.ativa == True).all()
    ids = [i.id for i in insts]
    leituras = db.query(Leitura).filter(Leitura.instalacao_id.in_(ids)).all() if ids else []
    total_kwh = sum(l.kwh_produzido for l in leituras)
    total_eco = sum(l.economia_reais for l in leituras)
    total_co2 = sum(l.co2_evitado_kg for l in leituras)
    return {
        "usuario": user.nome,
        "total_instalacoes": len(insts),
        "total_leituras": len(leituras),
        "total_kwh_produzido": round(total_kwh, 2),
        "total_economia_reais": round(total_eco, 2),
        "total_co2_evitado_kg": round(total_co2, 3),
        "arvores_equivalentes": round(total_co2 / 22, 2),
        "tarifa_usada_kwh": settings.TARIFA_KWH,
    }

@app.get("/relatorios/instalacao/{instalacao_id}", response_model=RelatorioInstalacao, tags=["Relatórios"])
def relatorio_instalacao(instalacao_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inst = db.query(Instalacao).filter(Instalacao.id == instalacao_id).first()
    if not inst: raise HTTPException(404, "Instalação não encontrada")
    if user.role != "admin" and inst.usuario_id != user.id: raise HTTPException(403, "Acesso negado")
    leituras = db.query(Leitura).filter(Leitura.instalacao_id == instalacao_id).all()
    if not leituras:
        return RelatorioInstalacao(instalacao=inst, total_leituras=0, total_kwh_produzido=0,
            total_economia_reais=0, total_co2_evitado_kg=0, media_kwh_dia=0, arvores_equivalentes=0)
    total_kwh = sum(l.kwh_produzido for l in leituras)
    total_eco = sum(l.economia_reais for l in leituras)
    total_co2 = sum(l.co2_evitado_kg for l in leituras)
    return RelatorioInstalacao(
        instalacao=inst,
        total_leituras=len(leituras),
        total_kwh_produzido=round(total_kwh, 2),
        total_economia_reais=round(total_eco, 2),
        total_co2_evitado_kg=round(total_co2, 3),
        media_kwh_dia=round(total_kwh / len(leituras), 2),
        arvores_equivalentes=round(total_co2 / 22, 2),
    )

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND EMBUTIDO
# ─────────────────────────────────────────────────────────────────────────────
FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SolarTrack Brasil</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --sun:#F59E0B;--sun-lt:#FEF3C7;--sun-dk:#92400E;
  --green:#10B981;--green-lt:#D1FAE5;--green-dk:#065F46;
  --blue:#3B82F6;--blue-lt:#DBEAFE;--blue-dk:#1E3A8A;
  --red:#EF4444;--red-lt:#FEE2E2;--red-dk:#991B1B;
  --coal:#1C1917;--surface:#F5F5F4;--card:#FFFFFF;
  --muted:#78716C;--border:rgba(0,0,0,0.09);
  --text:#1C1917;--sub:#57534E;--radius:12px;
}
body{font-family:'DM Sans',sans-serif;background:var(--surface);color:var(--text);min-height:100vh;font-size:14px}
.topbar{background:var(--coal);padding:0 1.5rem;height:52px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:17px;color:var(--sun);display:flex;align-items:center;gap:8px}
.logo-dot{width:7px;height:7px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.3)}}
.topbar-right{display:flex;align-items:center;gap:10px}
.badge-live{background:var(--green);color:#fff;font-size:10px;font-weight:600;padding:3px 8px;border-radius:20px;letter-spacing:.5px;display:flex;align-items:center;gap:4px}
.badge-live::before{content:'';width:5px;height:5px;background:#fff;border-radius:50%;animation:pulse 1.5s infinite}
.user-chip{background:rgba(255,255,255,.1);color:#fff;font-size:13px;padding:5px 12px;border-radius:20px}
.btn-logout{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.7);font-size:12px;padding:5px 10px;border-radius:8px;cursor:pointer;font-family:inherit}
.btn-logout:hover{background:rgba(255,255,255,.1)}
.auth-screen{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1c1917 0%,#292524 60%,#1c1917 100%);padding:1rem}
.auth-card{background:#fff;border-radius:20px;padding:2.5rem;width:100%;max-width:420px}
.auth-logo{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:var(--sun);display:flex;align-items:center;gap:8px;margin-bottom:.5rem}
.auth-sub{color:var(--muted);font-size:13px;margin-bottom:2rem}
.auth-tabs{display:flex;gap:4px;background:var(--surface);border-radius:10px;padding:4px;margin-bottom:1.5rem}
.auth-tab{flex:1;padding:8px;text-align:center;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;color:var(--muted);border:none;background:none;font-family:inherit}
.auth-tab.active{background:#fff;color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,.1)}
.field{margin-bottom:1rem}
.field label{display:block;font-size:12px;font-weight:600;color:var(--sub);margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
.field input{width:100%;padding:10px 12px;border:1.5px solid var(--border);border-radius:10px;font-size:14px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus{border-color:var(--sun)}
.btn-primary{width:100%;padding:12px;background:var(--coal);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;transition:opacity .15s}
.btn-primary:hover{opacity:.85}
.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.auth-error{background:var(--red-lt);color:var(--red-dk);font-size:13px;padding:10px 12px;border-radius:8px;margin-bottom:1rem;display:none}
.layout{display:grid;grid-template-columns:210px 1fr;min-height:calc(100vh - 52px)}
.sidebar{background:#fff;border-right:1px solid var(--border);padding:1.25rem 0;display:flex;flex-direction:column}
.sidebar-section{margin-bottom:1.5rem}
.sidebar-label{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;padding:0 1rem;margin-bottom:.4rem}
.nav-item{display:flex;align-items:center;gap:9px;padding:9px 1rem;font-size:13.5px;color:var(--sub);cursor:pointer;transition:all .12s;border:none;background:none;width:100%;text-align:left;font-family:inherit;border-left:3px solid transparent}
.nav-item:hover{background:var(--surface);color:var(--text)}
.nav-item.active{background:var(--sun-lt);color:var(--sun-dk);border-left-color:var(--sun);font-weight:600}
.nav-item i{font-size:17px}
.main{padding:1.75rem;overflow-y:auto}
.page-header{margin-bottom:1.75rem}
.page-title{font-family:'Syne',sans-serif;font-size:24px;font-weight:800;letter-spacing:-.5px}
.page-sub{font-size:13px;color:var(--muted);margin-top:3px}
.card{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1.25rem}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:.875rem;margin-bottom:1.25rem}
.metric{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1.1rem;position:relative;overflow:hidden}
.metric::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.metric.sun::before{background:var(--sun)}
.metric.green::before{background:var(--green)}
.metric.blue::before{background:var(--blue)}
.metric.pink::before{background:#EC4899}
.metric-icon{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:17px;margin-bottom:.65rem}
.metric.sun .metric-icon{background:var(--sun-lt);color:var(--sun-dk)}
.metric.green .metric-icon{background:var(--green-lt);color:var(--green-dk)}
.metric.blue .metric-icon{background:var(--blue-lt);color:var(--blue-dk)}
.metric.pink .metric-icon{background:#FCE7F3;color:#9D174D}
.metric-val{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;line-height:1}
.metric-label{font-size:12px;color:var(--muted);margin-top:3px}
.charts-grid{display:grid;grid-template-columns:2fr 1fr;gap:.875rem;margin-bottom:1.25rem}
.chart-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem}
.chart-title{font-weight:600;font-size:14.5px}
.chart-sub{font-size:12px;color:var(--muted);margin-top:2px}
.tab-group{display:flex;gap:3px;background:var(--surface);border-radius:8px;padding:3px}
.tab{font-size:11.5px;padding:4px 9px;border-radius:6px;cursor:pointer;color:var(--muted);font-weight:500;border:none;background:none;font-family:inherit}
.tab.active{background:#fff;color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.1)}
.table-wrap{background:#fff;border-radius:var(--radius);border:1px solid var(--border);overflow:hidden}
.table-header{padding:.9rem 1.1rem;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.table-title{font-weight:600;font-size:14.5px}
table{width:100%;border-collapse:collapse}
thead th{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;padding:9px 1.1rem;text-align:left;background:var(--surface);border-bottom:1px solid var(--border)}
tbody td{padding:11px 1.1rem;font-size:13px;border-bottom:1px solid var(--border)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:#fafafa}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px}
.badge-online{background:var(--green-lt);color:var(--green-dk)}
.badge-warning{background:var(--sun-lt);color:var(--sun-dk)}
.badge-offline{background:var(--red-lt);color:var(--red-dk)}
.bottom-grid{display:grid;grid-template-columns:1fr 1fr;gap:.875rem}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid var(--border);background:#fff;color:var(--text);font-family:inherit;transition:all .12s}
.btn:hover{background:var(--surface)}
.btn-accent{background:var(--coal);color:#fff;border-color:var(--coal)}
.btn-accent:hover{opacity:.85}
.btn-danger{background:var(--red-lt);color:var(--red-dk);border-color:transparent}
.btn-danger:hover{background:#fecaca}
.btn-success{background:var(--green-lt);color:var(--green-dk);border-color:transparent}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:200;display:none;align-items:center;justify-content:center}
.modal-backdrop.open{display:flex}
.modal{background:#fff;border-radius:16px;padding:1.75rem;width:100%;max-width:480px;max-height:90vh;overflow-y:auto}
.modal-title{font-family:'Syne',sans-serif;font-size:18px;font-weight:800;margin-bottom:1.25rem;display:flex;justify-content:space-between;align-items:center}
.modal-close{background:none;border:none;cursor:pointer;color:var(--muted);font-size:20px}
.modal-close:hover{color:var(--text)}
.inst-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}
.inst-card{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1.25rem}
.inst-card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.75rem}
.inst-name{font-weight:700;font-size:15px}
.inst-loc{font-size:12px;color:var(--muted);margin-top:2px;display:flex;align-items:center;gap:4px}
.inst-kw{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:var(--sun)}
.inst-kw-label{font-size:11px;color:var(--muted)}
.inst-actions{display:flex;gap:6px;margin-top:1rem}
.leitura-form-card{background:linear-gradient(135deg,#1c1917,#292524);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.25rem;border:1px solid rgba(245,158,11,.25)}
.leitura-form-title{color:#fff;font-weight:700;font-size:15px;margin-bottom:1rem;display:flex;align-items:center;gap:8px}
.leitura-form-grid{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:.75rem;align-items:end}
.dark-field label{color:rgba(255,255,255,.6);font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;display:block;margin-bottom:5px}
.dark-field input,.dark-field select,.dark-field textarea{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:#fff;padding:9px 12px;border-radius:8px;font-size:13px;font-family:inherit;outline:none;width:100%}
.dark-field input:focus,.dark-field select:focus{border-color:var(--sun)}
.roi-card{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1.25rem}
.roi-total{display:flex;justify-content:space-between;align-items:center;padding:1rem;background:var(--coal);border-radius:10px;margin-bottom:1rem}
.roi-total-label{color:rgba(255,255,255,.6);font-size:12px}
.roi-total-val{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:var(--sun)}
.roi-item{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)}
.roi-item:last-child{border-bottom:none}
.roi-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.roi-item-label{font-size:13px;color:var(--sub)}
.roi-item-val{font-size:14px;font-weight:600}
.inst-select-bar{background:#fff;border:1px solid var(--border);border-radius:10px;padding:.6rem 1rem;display:flex;align-items:center;gap:10px;margin-bottom:1.25rem}
.inst-select-bar select{border:none;outline:none;font-size:14px;font-family:inherit;flex:1;background:transparent;color:var(--text);cursor:pointer}
.forecast-strip{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1.1rem 1.25rem;display:flex;gap:1.25rem;align-items:center}
.forecast-days{display:flex;gap:.65rem;flex:1;overflow-x:auto}
.forecast-day{flex:1;min-width:72px;text-align:center;padding:9px 6px;border-radius:9px;border:1px solid var(--border)}
.forecast-day.best{background:var(--sun-lt);border-color:var(--sun)}
.forecast-day-name{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.forecast-day-kwh{font-family:'Syne',sans-serif;font-size:18px;font-weight:800;margin:4px 0 1px}
.forecast-day.best .forecast-day-kwh{color:var(--sun-dk)}
.forecast-day-sky{font-size:10.5px;color:var(--muted)}
.forecast-emoji{font-size:20px;margin-bottom:2px}
.toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:500;display:flex;flex-direction:column;gap:8px}
.toast{background:#fff;border-radius:10px;padding:12px 16px;border-left:4px solid var(--green);box-shadow:0 4px 20px rgba(0,0,0,.12);font-size:13px;font-weight:500;display:flex;align-items:center;gap:8px;animation:slideIn .2s ease}
.toast.error{border-left-color:var(--red)}
.toast.warn{border-left-color:var(--sun)}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:none;opacity:1}}
.empty{text-align:center;padding:3rem 1rem;color:var(--muted)}
.empty i{font-size:48px;opacity:.3;display:block;margin-bottom:1rem}
.spinner{width:28px;height:28px;border:3px solid var(--border);border-top-color:var(--sun);border-radius:50%;animation:spin .7s linear infinite;margin:2rem auto}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:700px){
  .layout{grid-template-columns:1fr}.sidebar{display:none}
  .metrics{grid-template-columns:1fr 1fr}
  .charts-grid,.bottom-grid{grid-template-columns:1fr}
  .leitura-form-grid{grid-template-columns:1fr 1fr}
  .form-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

<div id="authScreen" class="auth-screen">
  <div class="auth-card">
    <div class="auth-logo"><div class="logo-dot"></div>SolarTrack Brasil</div>
    <p class="auth-sub">Monitore sua energia solar com precisão</p>
    <div class="auth-tabs">
      <button class="auth-tab active" onclick="switchAuthTab('login',this)">Entrar</button>
      <button class="auth-tab" onclick="switchAuthTab('register',this)">Criar conta</button>
    </div>
    <div id="authError" class="auth-error"></div>
    <div id="loginForm">
      <div class="field"><label>Usuário</label><input id="loginUser" type="text" placeholder="admin" /></div>
      <div class="field"><label>Senha</label><input id="loginPass" type="password" placeholder="••••••••" /></div>
      <button class="btn-primary" id="loginBtn" onclick="doLogin()">Entrar</button>
    </div>
    <div id="registerForm" style="display:none">
      <div class="field"><label>Nome completo</label><input id="regNome" type="text" /></div>
      <div class="field"><label>Usuário</label><input id="regUser" type="text" /></div>
      <div class="field"><label>E-mail</label><input id="regEmail" type="email" /></div>
      <div class="field"><label>Senha</label><input id="regPass" type="password" /></div>
      <button class="btn-primary" id="registerBtn" onclick="doRegister()">Criar conta</button>
    </div>
  </div>
</div>

<div id="app" style="display:none">
  <div class="topbar">
    <div class="logo"><div class="logo-dot"></div>SolarTrack Brasil</div>
    <div class="topbar-right">
      <div class="badge-live">Ao vivo</div>
      <div class="user-chip" id="userChip">—</div>
      <button class="btn-logout" onclick="logout()"><i class="ti ti-logout"></i> Sair</button>
    </div>
  </div>
  <div class="layout">
    <div class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-label">Principal</div>
        <button class="nav-item active" data-page="dashboard" onclick="nav('dashboard',this)"><i class="ti ti-layout-dashboard"></i> Dashboard</button>
        <button class="nav-item" data-page="instalacoes" onclick="nav('instalacoes',this)"><i class="ti ti-solar-panel"></i> Instalações</button>
        <button class="nav-item" data-page="leituras" onclick="nav('leituras',this)"><i class="ti ti-bolt"></i> Leituras</button>
        <button class="nav-item" data-page="relatorios" onclick="nav('relatorios',this)"><i class="ti ti-chart-pie"></i> Relatórios</button>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-label">Conta</div>
        <button class="nav-item" onclick="logout()"><i class="ti ti-logout"></i> Sair</button>
      </div>
    </div>
    <div class="main" id="mainContent"><div class="spinner"></div></div>
  </div>
</div>

<!-- MODAIS -->
<div class="modal-backdrop" id="modalInstAdd">
  <div class="modal">
    <div class="modal-title">Nova instalação <button class="modal-close" onclick="closeModal('modalInstAdd')"><i class="ti ti-x"></i></button></div>
    <div class="form-grid">
      <div class="field"><label>Nome</label><input id="instNome" type="text" placeholder="Residência SP" /></div>
      <div class="field"><label>Localização</label><input id="instLoc" type="text" placeholder="São Paulo, SP" /></div>
      <div class="field"><label>Capacidade (kWp)</label><input id="instKwp" type="number" step="0.1" placeholder="5.0" /></div>
      <div class="field"><label>Data de instalação</label><input id="instData" type="date" /></div>
    </div>
    <div class="field" style="margin-top:.5rem"><label>Descrição (opcional)</label><input id="instDesc" type="text" /></div>
    <div style="display:flex;gap:8px;margin-top:1.25rem;justify-content:flex-end">
      <button class="btn" onclick="closeModal('modalInstAdd')">Cancelar</button>
      <button class="btn btn-accent" onclick="criarInstalacao()"><i class="ti ti-plus"></i> Criar</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="modalInstEdit">
  <div class="modal">
    <div class="modal-title">Editar instalação <button class="modal-close" onclick="closeModal('modalInstEdit')"><i class="ti ti-x"></i></button></div>
    <input type="hidden" id="editInstId" />
    <div class="form-grid">
      <div class="field"><label>Nome</label><input id="editInstNome" type="text" /></div>
      <div class="field"><label>Localização</label><input id="editInstLoc" type="text" /></div>
      <div class="field"><label>Capacidade (kWp)</label><input id="editInstKwp" type="number" step="0.1" /></div>
    </div>
    <div class="field" style="margin-top:.5rem"><label>Descrição</label><input id="editInstDesc" type="text" /></div>
    <div style="display:flex;gap:8px;margin-top:1.25rem;justify-content:flex-end">
      <button class="btn" onclick="closeModal('modalInstEdit')">Cancelar</button>
      <button class="btn btn-accent" onclick="salvarInstalacao()"><i class="ti ti-check"></i> Salvar</button>
    </div>
  </div>
</div>

<div class="toast-container" id="toastContainer"></div>

<script>
const API = '';
let token = localStorage.getItem('st_token') || null;
let currentUser = null;
let instalacoes = [];
let chartProd = null, chartEcon = null;
let leituraInstId = null;

async function api(path, opts={}) {
  const headers = {'Content-Type':'application/json'};
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API + path, {headers, ...opts});
  if (res.status === 204) return {};
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro na requisição');
  return data;
}

function toast(msg, type='success') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast' + (type==='error'?' error':type==='warn'?' warn':'');
  const icon = type==='error'?'ti-alert-circle':type==='warn'?'ti-alert-triangle':'ti-check';
  t.innerHTML = `<i class="ti ${icon}"></i>${msg}`;
  c.appendChild(t);
  setTimeout(()=>t.remove(), 3500);
}

function switchAuthTab(tab, btn) {
  document.querySelectorAll('.auth-tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('loginForm').style.display = tab==='login'?'':'none';
  document.getElementById('registerForm').style.display = tab==='register'?'':'none';
  document.getElementById('authError').style.display = 'none';
}

async function doLogin() {
  const btn = document.getElementById('loginBtn');
  btn.disabled = true; btn.textContent = 'Entrando...';
  const err = document.getElementById('authError');
  err.style.display = 'none';
  try {
    const fd = new FormData();
    fd.append('username', document.getElementById('loginUser').value);
    fd.append('password', document.getElementById('loginPass').value);
    const res = await fetch(API + '/auth/token', {method:'POST', body:fd});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Credenciais inválidas');
    token = data.access_token;
    localStorage.setItem('st_token', token);
    await initApp();
  } catch(e) {
    err.textContent = e.message; err.style.display = 'block';
  } finally { btn.disabled=false; btn.textContent='Entrar'; }
}

async function doRegister() {
  const btn = document.getElementById('registerBtn');
  btn.disabled=true; btn.textContent='Criando...';
  const err = document.getElementById('authError');
  err.style.display='none';
  try {
    await api('/auth/registrar', {method:'POST', body:JSON.stringify({
      nome: document.getElementById('regNome').value,
      username: document.getElementById('regUser').value,
      email: document.getElementById('regEmail').value,
      password: document.getElementById('regPass').value,
    })});
    toast('Conta criada! Faça login.');
    switchAuthTab('login', document.querySelectorAll('.auth-tab')[0]);
  } catch(e) { err.textContent=e.message; err.style.display='block'; }
  finally { btn.disabled=false; btn.textContent='Criar conta'; }
}

function logout() {
  token=null; localStorage.removeItem('st_token');
  document.getElementById('app').style.display='none';
  document.getElementById('authScreen').style.display='flex';
  currentUser=null;
}

async function initApp() {
  try {
    currentUser = await api('/auth/me');
    document.getElementById('userChip').textContent = currentUser.nome + ' · ' + currentUser.role;
    document.getElementById('authScreen').style.display='none';
    document.getElementById('app').style.display='block';
    instalacoes = await api('/instalacoes/');
    nav('dashboard', document.querySelector('[data-page="dashboard"]'));
  } catch(e) { logout(); }
}

function nav(page, btn) {
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  if (btn) btn.classList.add('active');
  if (page==='dashboard') renderDashboard();
  else if (page==='instalacoes') renderInstalacoes();
  else if (page==='leituras') renderLeituras();
  else if (page==='relatorios') renderRelatorios();
}

function openModal(id){document.getElementById(id).classList.add('open')}
function closeModal(id){document.getElementById(id).classList.remove('open')}

/* ── DASHBOARD ── */
async function renderDashboard() {
  const mc = document.getElementById('mainContent');
  mc.innerHTML = '<div class="spinner"></div>';
  try {
    const r = await api('/relatorios/meu-resumo');
    mc.innerHTML = `
    <div class="page-header">
      <div class="page-title">Dashboard</div>
      <div class="page-sub">Bem-vindo, ${r.usuario} · ${new Date().toLocaleDateString('pt-BR',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
    </div>
    <div class="metrics">
      <div class="metric sun"><div class="metric-icon"><i class="ti ti-sun"></i></div><div class="metric-val">${(r.total_kwh_produzido||0).toLocaleString('pt-BR',{maximumFractionDigits:1})}</div><div class="metric-label">kWh produzidos</div></div>
      <div class="metric green"><div class="metric-icon"><i class="ti ti-currency-dollar"></i></div><div class="metric-val">R$${(r.total_economia_reais||0).toLocaleString('pt-BR',{maximumFractionDigits:2})}</div><div class="metric-label">Economia acumulada</div></div>
      <div class="metric blue"><div class="metric-icon"><i class="ti ti-solar-panel"></i></div><div class="metric-val">${r.total_instalacoes||0}</div><div class="metric-label">Instalações ativas</div></div>
      <div class="metric pink"><div class="metric-icon"><i class="ti ti-leaf"></i></div><div class="metric-val">${(r.total_co2_evitado_kg||0).toLocaleString('pt-BR',{maximumFractionDigits:1})} kg</div><div class="metric-label">CO₂ evitado</div></div>
    </div>
    <div class="charts-grid">
      <div class="card">
        <div class="chart-header">
          <div><div class="chart-title">Produção por período</div><div class="chart-sub">kWh gerado (simulado)</div></div>
          <div class="tab-group">
            <button class="tab active" onclick="switchChart('day',this)">Dia</button>
            <button class="tab" onclick="switchChart('month',this)">Mês</button>
            <button class="tab" onclick="switchChart('year',this)">Ano</button>
          </div>
        </div>
        <div style="height:220px"><canvas id="prodChart"></canvas></div>
      </div>
      <div class="card">
        <div class="chart-header"><div><div class="chart-title">Economia mensal</div><div class="chart-sub">R$ economizados</div></div></div>
        <div style="height:220px"><canvas id="econChart"></canvas></div>
      </div>
    </div>
    <div class="bottom-grid">
      <div class="table-wrap">
        <div class="table-header"><div class="table-title">Instalações</div><button class="btn" onclick="nav('instalacoes',document.querySelector('[data-page=instalacoes]'))"><i class="ti ti-arrow-right"></i> Ver todas</button></div>
        <table><thead><tr><th>Nome</th><th>Local</th><th>kWp</th><th>Status</th></tr></thead><tbody id="dashInstTable"><tr><td colspan="4" style="text-align:center;padding:1.5rem;color:var(--muted)">Carregando...</td></tr></tbody></table>
      </div>
      <div class="roi-card">
        <div class="chart-title" style="margin-bottom:1rem">Resumo &amp; impacto</div>
        <div class="roi-total"><div class="roi-total-label">Economia total</div><div class="roi-total-val">R$${(r.total_economia_reais||0).toLocaleString('pt-BR',{minimumFractionDigits:2})}</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:#F59E0B"></div><span class="roi-item-label">Total leituras</span></div><div class="roi-item-val">${r.total_leituras||0}</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:#10B981"></div><span class="roi-item-label">Tarifa usada</span></div><div class="roi-item-val">R$${(r.tarifa_usada_kwh||0.75).toFixed(2)}/kWh</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:#8B5CF6"></div><span class="roi-item-label">CO₂ evitado</span></div><div class="roi-item-val" style="color:#6D28D9">${(r.total_co2_evitado_kg||0).toLocaleString('pt-BR',{maximumFractionDigits:1})} kg</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:#065F46"></div><span class="roi-item-label">Árvores equiv.</span></div><div class="roi-item-val">🌱 ${(r.arvores_equivalentes||0).toFixed(1)}</div></div>
      </div>
    </div>
    <div class="forecast-strip" style="margin-top:.875rem">
      <div><div class="chart-title">Previsão 7 dias</div><div class="chart-sub">Estimativa</div></div>
      <div class="forecast-days" id="forecastDays"></div>
    </div>`;
    buildCharts();
    loadDashInstTable();
    buildForecast();
  } catch(e) {
    mc.innerHTML = `<div class="empty"><i class="ti ti-alert-circle"></i><p>${e.message}</p></div>`;
  }
}

const dayData={labels:['6h','7h','8h','9h','10h','11h','12h','13h','14h','15h','16h','17h','18h'],data:[0,.2,1.1,2.8,4.2,5.1,5.6,5.3,4.8,3.6,2.1,.8,.1]};
const monthData={labels:['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],data:[580,620,710,850,920,780,810,890,960,1020,880,760]};
const yearData={labels:['2021','2022','2023','2024','2025'],data:[6200,7800,9100,10400,11200]};

function buildCharts() {
  const pc=document.getElementById('prodChart'), ec=document.getElementById('econChart');
  if(!pc||!ec) return;
  if(chartProd){chartProd.destroy();chartProd=null;}
  if(chartEcon){chartEcon.destroy();chartEcon=null;}
  chartProd = new Chart(pc,{type:'bar',data:{labels:dayData.labels,datasets:[{label:'kW gerado',data:dayData.data,backgroundColor:'rgba(245,158,11,.85)',borderRadius:5,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:11},color:'#78716C'}},y:{grid:{color:'rgba(0,0,0,.05)'},ticks:{font:{size:11},color:'#78716C'}}}}});
  chartEcon = new Chart(ec,{type:'line',data:{labels:monthData.labels,datasets:[{label:'Economia (R$)',data:[290,310,355,425,460,390,405,445,480,510,440,380],borderColor:'#10B981',backgroundColor:'rgba(16,185,129,.08)',borderWidth:2,fill:true,tension:.4,pointRadius:3,pointBackgroundColor:'#10B981'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:11},color:'#78716C'}},y:{grid:{color:'rgba(0,0,0,.05)'},ticks:{font:{size:11},color:'#78716C',callback:v=>'R$'+v}}}}});
}

function switchChart(key, btn) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  if(!chartProd) return;
  const d=key==='day'?dayData:key==='month'?monthData:yearData;
  chartProd.data.labels=d.labels; chartProd.data.datasets[0].data=d.data;
  chartProd.data.datasets[0].label=key==='day'?'kW gerado':'kWh gerado';
  chartProd.update();
}

async function loadDashInstTable() {
  const tb=document.getElementById('dashInstTable'); if(!tb) return;
  try {
    const list=await api('/instalacoes/');
    if(!list.length){tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:1.5rem">Nenhuma instalação</td></tr>';return;}
    tb.innerHTML=list.slice(0,5).map(i=>`<tr><td><strong>${i.nome}</strong></td><td style="color:var(--muted)">${i.localizacao}</td><td>${i.capacidade_kwp} kWp</td><td><span class="badge badge-online">Online</span></td></tr>`).join('');
  } catch{}
}

function buildForecast() {
  const days=document.getElementById('forecastDays'); if(!days) return;
  const fc=[{day:'Seg',e:'☀️',kwh:22.1,sky:'Sol forte',best:false},{day:'Ter',e:'🌞',kwh:24.8,sky:'Irradiância máx',best:true},{day:'Qua',e:'🌤️',kwh:18.5,sky:'Parcial nublado',best:false},{day:'Qui',e:'⛅',kwh:14.2,sky:'Muito nublado',best:false},{day:'Sex',e:'🌧️',kwh:8.1,sky:'Chuva prevista',best:false},{day:'Sáb',e:'🌤️',kwh:17.3,sky:'Parcial nublado',best:false},{day:'Dom',e:'☀️',kwh:21.0,sky:'Sol forte',best:false}];
  days.innerHTML=fc.map(f=>`<div class="forecast-day${f.best?' best':''}"><div class="forecast-emoji">${f.e}</div><div class="forecast-day-name">${f.day}</div><div class="forecast-day-kwh" style="color:${f.kwh<10?'var(--red)':f.best?'var(--sun-dk)':'var(--sub)'}">${f.kwh.toFixed(1)}</div><div class="forecast-day-sky">${f.sky}</div></div>`).join('');
}

/* ── INSTALAÇÕES ── */
async function renderInstalacoes() {
  const mc=document.getElementById('mainContent');
  mc.innerHTML='<div class="spinner"></div>';
  try {
    instalacoes=await api('/instalacoes/');
    mc.innerHTML=`
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="page-title">Instalações</div><div class="page-sub">${instalacoes.length} instalação(ões) ativa(s)</div></div>
      <button class="btn btn-accent" onclick="openModal('modalInstAdd')"><i class="ti ti-plus"></i> Nova instalação</button>
    </div>
    ${instalacoes.length?`<div class="inst-grid">${instalacoes.map(instCard).join('')}</div>`:'<div class="empty"><i class="ti ti-solar-panel"></i><p>Nenhuma instalação. Clique em "Nova instalação".</p></div>'}`;
  } catch(e){ mc.innerHTML=`<div class="empty"><i class="ti ti-alert-circle"></i><p>${e.message}</p></div>`; }
}

function instCard(i){
  return `<div class="inst-card">
    <div class="inst-card-top">
      <div><div class="inst-name">${i.nome}</div><div class="inst-loc"><i class="ti ti-map-pin"></i>${i.localizacao}</div></div>
      <div><div class="inst-kw">${i.capacidade_kwp}</div><div class="inst-kw-label">kWp</div></div>
    </div>
    ${i.descricao?`<p style="font-size:12.5px;color:var(--muted);margin-bottom:.5rem">${i.descricao}</p>`:''}
    <div style="font-size:11.5px;color:var(--muted);margin-bottom:.5rem">📅 ${new Date(i.data_instalacao+'T00:00:00').toLocaleDateString('pt-BR')}</div>
    <span class="badge badge-online">Online</span>
    <div class="inst-actions">
      <button class="btn" onclick="editInstalacao(${i.id})"><i class="ti ti-edit"></i> Editar</button>
      <button class="btn" onclick="verRelatorio(${i.id})"><i class="ti ti-chart-pie"></i> Relatório</button>
      <button class="btn btn-danger" onclick="desativarInstalacao(${i.id})"><i class="ti ti-trash"></i></button>
    </div>
  </div>`;
}

async function criarInstalacao(){
  try {
    await api('/instalacoes/',{method:'POST',body:JSON.stringify({nome:document.getElementById('instNome').value,localizacao:document.getElementById('instLoc').value,capacidade_kwp:parseFloat(document.getElementById('instKwp').value),data_instalacao:document.getElementById('instData').value,descricao:document.getElementById('instDesc').value||null})});
    closeModal('modalInstAdd'); toast('Instalação criada!'); renderInstalacoes();
  } catch(e){toast(e.message,'error');}
}

function editInstalacao(id){
  const i=instalacoes.find(x=>x.id===id); if(!i) return;
  document.getElementById('editInstId').value=id;
  document.getElementById('editInstNome').value=i.nome;
  document.getElementById('editInstLoc').value=i.localizacao;
  document.getElementById('editInstKwp').value=i.capacidade_kwp;
  document.getElementById('editInstDesc').value=i.descricao||'';
  openModal('modalInstEdit');
}

async function salvarInstalacao(){
  const id=document.getElementById('editInstId').value;
  try {
    await api(`/instalacoes/${id}`,{method:'PUT',body:JSON.stringify({nome:document.getElementById('editInstNome').value,localizacao:document.getElementById('editInstLoc').value,capacidade_kwp:parseFloat(document.getElementById('editInstKwp').value),descricao:document.getElementById('editInstDesc').value||null})});
    closeModal('modalInstEdit'); toast('Instalação atualizada!'); renderInstalacoes();
  } catch(e){toast(e.message,'error');}
}

async function desativarInstalacao(id){
  if(!confirm('Desativar esta instalação?')) return;
  try { await api(`/instalacoes/${id}`,{method:'DELETE'}); toast('Instalação desativada.','warn'); renderInstalacoes(); }
  catch(e){toast(e.message,'error');}
}

/* ── LEITURAS ── */
async function renderLeituras(){
  const mc=document.getElementById('mainContent');
  mc.innerHTML='<div class="spinner"></div>';
  try {
    instalacoes=await api('/instalacoes/');
    if(!instalacoes.length){mc.innerHTML='<div class="page-header"><div class="page-title">Leituras</div></div><div class="empty"><i class="ti ti-solar-panel"></i><p>Cadastre uma instalação primeiro.</p></div>';return;}
    leituraInstId=leituraInstId||instalacoes[0].id;
    mc.innerHTML=`
    <div class="page-header"><div class="page-title">Leituras</div><div class="page-sub">Registre a produção diária</div></div>
    <div class="leitura-form-card">
      <div class="leitura-form-title"><i class="ti ti-bolt"></i>Registrar nova leitura</div>
      <div class="leitura-form-grid">
        <div class="dark-field"><label>Instalação</label><select id="leituraInst" onchange="leituraInstId=parseInt(this.value);loadLeituras()">${instalacoes.map(i=>`<option value="${i.id}" ${i.id===leituraInstId?'selected':''}>${i.nome}</option>`).join('')}</select></div>
        <div class="dark-field"><label>Data</label><input type="date" id="leituraData" value="${new Date().toISOString().split('T')[0]}" /></div>
        <div class="dark-field"><label>kWh produzido</label><input type="number" id="leituraKwh" step="0.1" placeholder="12.5" /></div>
        <button class="btn btn-success" onclick="registrarLeitura()" style="height:38px;align-self:end"><i class="ti ti-plus"></i> Registrar</button>
      </div>
      <div class="dark-field" style="margin-top:.75rem"><label>Observação (opcional)</label><input type="text" id="leituraObs" placeholder="Ex: Dia parcialmente nublado" /></div>
    </div>
    <div class="table-wrap" id="leiturasTable"><div class="spinner"></div></div>`;
    loadLeituras();
  } catch(e){ mc.innerHTML=`<div class="empty"><i class="ti ti-alert-circle"></i><p>${e.message}</p></div>`; }
}

async function loadLeituras(){
  const tb=document.getElementById('leiturasTable'); if(!tb) return;
  tb.innerHTML='<div class="spinner"></div>';
  try {
    const list=await api(`/instalacoes/${leituraInstId}/leituras/`);
    if(!list.length){tb.innerHTML='<div class="empty"><i class="ti ti-bolt"></i><p>Nenhuma leitura registrada.</p></div>';return;}
    tb.innerHTML=`
    <div class="table-header"><div class="table-title">${list.length} leitura(s)</div></div>
    <table><thead><tr><th>Data</th><th>kWh</th><th>Economia</th><th>CO₂ evitado</th><th>Obs.</th><th></th></tr></thead>
    <tbody>${list.map(l=>`<tr><td>${new Date(l.data+'T00:00:00').toLocaleDateString('pt-BR')}</td><td><strong>${l.kwh_produzido.toLocaleString('pt-BR',{maximumFractionDigits:2})}</strong></td><td style="color:var(--green-dk)"><strong>R$${l.economia_reais.toLocaleString('pt-BR',{minimumFractionDigits:2})}</strong></td><td style="color:#6D28D9">${l.co2_evitado_kg.toFixed(3)} kg</td><td style="color:var(--muted)">${l.observacao||'—'}</td><td><button class="btn btn-danger" onclick="deletarLeitura(${l.id})" style="padding:5px 8px"><i class="ti ti-trash"></i></button></td></tr>`).join('')}</tbody></table>`;
  } catch(e){ tb.innerHTML=`<div class="empty"><p>${e.message}</p></div>`; }
}

async function registrarLeitura(){
  try {
    const instId=parseInt(document.getElementById('leituraInst').value);
    leituraInstId=instId;
    await api(`/instalacoes/${instId}/leituras/`,{method:'POST',body:JSON.stringify({data:document.getElementById('leituraData').value,kwh_produzido:parseFloat(document.getElementById('leituraKwh').value),observacao:document.getElementById('leituraObs').value||null})});
    toast('Leitura registrada!');
    document.getElementById('leituraKwh').value='';
    document.getElementById('leituraObs').value='';
    loadLeituras();
  } catch(e){toast(e.message,'error');}
}

async function deletarLeitura(leituraId){
  if(!confirm('Excluir esta leitura?')) return;
  try { await api(`/instalacoes/${leituraInstId}/leituras/${leituraId}`,{method:'DELETE'}); toast('Leitura removida.','warn'); loadLeituras(); }
  catch(e){toast(e.message,'error');}
}

/* ── RELATÓRIOS ── */
async function renderRelatorios(){
  const mc=document.getElementById('mainContent');
  mc.innerHTML='<div class="spinner"></div>';
  try {
    instalacoes=await api('/instalacoes/');
    mc.innerHTML=`
    <div class="page-header"><div class="page-title">Relatórios</div><div class="page-sub">Análise detalhada por instalação</div></div>
    <div class="inst-select-bar"><i class="ti ti-solar-panel"></i><select id="relatorioInstSelect" onchange="loadRelatorio(this.value)">${instalacoes.map(i=>`<option value="${i.id}">${i.nome} — ${i.localizacao}</option>`).join('')}</select></div>
    <div id="relatorioContent"><div class="spinner"></div></div>`;
    if(instalacoes.length) loadRelatorio(instalacoes[0].id);
  } catch(e){ mc.innerHTML=`<div class="empty"><i class="ti ti-alert-circle"></i><p>${e.message}</p></div>`; }
}

async function loadRelatorio(instId){
  const div=document.getElementById('relatorioContent'); if(!div) return;
  div.innerHTML='<div class="spinner"></div>';
  try {
    const r=await api(`/relatorios/instalacao/${instId}`);
    const i=r.instalacao;
    div.innerHTML=`
    <div class="metrics" style="margin-bottom:1.25rem">
      <div class="metric sun"><div class="metric-icon"><i class="ti ti-bolt"></i></div><div class="metric-val">${(r.total_kwh_produzido||0).toLocaleString('pt-BR',{maximumFractionDigits:1})}</div><div class="metric-label">kWh produzidos</div></div>
      <div class="metric green"><div class="metric-icon"><i class="ti ti-currency-dollar"></i></div><div class="metric-val">R$${(r.total_economia_reais||0).toLocaleString('pt-BR',{maximumFractionDigits:2})}</div><div class="metric-label">Economia total</div></div>
      <div class="metric blue"><div class="metric-icon"><i class="ti ti-calendar"></i></div><div class="metric-val">${r.total_leituras}</div><div class="metric-label">Dias registrados</div></div>
      <div class="metric pink"><div class="metric-icon"><i class="ti ti-leaf"></i></div><div class="metric-val">${(r.total_co2_evitado_kg||0).toLocaleString('pt-BR',{maximumFractionDigits:1})} kg</div><div class="metric-label">CO₂ evitado</div></div>
    </div>
    <div class="bottom-grid">
      <div class="card">
        <div class="chart-title" style="margin-bottom:1rem">Dados da instalação</div>
        <table style="width:100%"><tbody>
          <tr><td style="color:var(--muted);padding:8px 0;font-size:13px">Nome</td><td style="font-size:13px;font-weight:600;text-align:right">${i.nome}</td></tr>
          <tr><td style="color:var(--muted);padding:8px 0;font-size:13px">Localização</td><td style="font-size:13px;text-align:right">${i.localizacao}</td></tr>
          <tr><td style="color:var(--muted);padding:8px 0;font-size:13px">Capacidade</td><td style="font-size:13px;font-weight:600;text-align:right;color:var(--sun-dk)">${i.capacidade_kwp} kWp</td></tr>
          <tr><td style="color:var(--muted);padding:8px 0;font-size:13px">Instalado em</td><td style="font-size:13px;text-align:right">${new Date(i.data_instalacao+'T00:00:00').toLocaleDateString('pt-BR')}</td></tr>
          <tr><td style="color:var(--muted);padding:8px 0;font-size:13px">Média diária</td><td style="font-size:13px;font-weight:600;text-align:right">${(r.media_kwh_dia||0).toFixed(2)} kWh/dia</td></tr>
        </tbody></table>
      </div>
      <div class="roi-card">
        <div class="chart-title" style="margin-bottom:1rem">Impacto ambiental &amp; ROI</div>
        <div class="roi-total"><div class="roi-total-label">Economia total</div><div class="roi-total-val">R$${(r.total_economia_reais||0).toLocaleString('pt-BR',{minimumFractionDigits:2})}</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:#8B5CF6"></div><span class="roi-item-label">CO₂ evitado</span></div><div class="roi-item-val" style="color:#6D28D9">${(r.total_co2_evitado_kg||0).toFixed(3)} kg</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:var(--green-dk)"></div><span class="roi-item-label">Árvores equiv.</span></div><div class="roi-item-val">🌱 ${(r.arvores_equivalentes||0).toFixed(1)}</div></div>
        <div class="roi-item"><div style="display:flex;align-items:center;gap:8px"><div class="roi-dot" style="background:var(--blue)"></div><span class="roi-item-label">Média kWh/dia</span></div><div class="roi-item-val">${(r.media_kwh_dia||0).toFixed(2)}</div></div>
        <div style="margin-top:1rem"><button class="btn btn-accent" style="width:100%" onclick="nav('leituras',document.querySelector('[data-page=leituras]'));leituraInstId=${instId}"><i class="ti ti-bolt"></i> Leituras desta instalação</button></div>
      </div>
    </div>`;
  } catch(e){ div.innerHTML=`<div class="empty"><p>${e.message}</p></div>`; }
}

function verRelatorio(id){
  nav('relatorios',document.querySelector('[data-page="relatorios"]'));
  setTimeout(()=>{ const s=document.getElementById('relatorioInstSelect'); if(s){s.value=id;loadRelatorio(id);} },300);
}

/* ── INIT ── */
if(token){
  document.getElementById('authScreen').style.display='none';
  document.getElementById('app').style.display='block';
  initApp();
}

document.addEventListener('keydown',e=>{
  if(e.key==='Enter'){
    const lf=document.getElementById('loginForm');
    if(lf&&lf.style.display!=='none') doLogin();
  }
});
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def frontend():
    return HTMLResponse(content=FRONTEND_HTML)

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP — cria admin padrão
# ─────────────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def criar_admin():
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.username == "admin").first():
            db.add(Usuario(
                nome="Administrador", username="admin",
                email="admin@solartrack.com",
                hashed_password=get_password_hash("admin123"),
                role="admin",
            ))
            db.commit()
            print("✅  Admin criado: admin / admin123")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)