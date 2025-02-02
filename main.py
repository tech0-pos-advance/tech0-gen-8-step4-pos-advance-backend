from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from typing import Optional
from pydantic import BaseModel
from typing import List

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()  # .env をデフォルトとして読み込む
load_dotenv(dotenv_path=".env.local", override=True)  # .env.local があれば上書き

# 環境変数の読み込み
DB_HOST = os.getenv("DB_HOST") 
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL_CA = os.getenv("DB_SSL_CA")

# MySQL接続URLを構築
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?ssl_ca={DB_SSL_CA}"

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, DB_SSL_CA]):
    raise ValueError("Missing database configuration environment variables")

# SQLAlchemyの設定（データベース接続）
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # 接続前にチェックを実施
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except SQLAlchemyError as e:
    logger.error(f"Database connection error: {e}")
    raise RuntimeError(f"Database connection error: {e}")

# ORMの基盤となるクラスを作成
Base = declarative_base()

# CORSの許可設定
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_ORIGINS_LIST = ALLOWED_ORIGINS.split(",")

# FastAPIアプリの作成
app = FastAPI()

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,  # 環境変数から取得
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Company(Base):
    __tablename__ = "m_user_companies"

    company_id = Column(String(50), primary_key=True)
    company_name = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    company_token = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

# --- Pydantic スキーマ ---
class CompanySchema(BaseModel):
    company_id: str
    company_name: str
    company_token: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# データベースセッションを取得する関数
def get_db():
    """データベースセッションを取得し、処理後にクローズする"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if db:
            db.close()

# ルートエンドポイント
@app.get("/")
def read_root():
    """アプリのルートエンドポイント"""
    return {"message": "Hello, POSTアプリのAdvanceだよ!"}

# --- 1) すべての企業情報を取得 ---
@app.get("/companies", response_model=List[CompanySchema])
def read_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    return companies

# --- 2) 特定の企業情報を取得 ---
@app.get("/companies/{company_id}", response_model=CompanySchema)
def read_company(company_id: str, db: Session = Depends(get_db)):
    """指定されたユーザーIDの情報を取得"""
    company: Optional[Company] = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="User not found")
    return company  # Pydanticが自動的にJSONへ変換

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))