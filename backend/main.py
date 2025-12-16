from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import os
from datetime import datetime
from typing import List, Optional
import httpx
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import SessionLocal, engine, Base, get_db
from models import User, Chat, Message, Document, DocumentAccess, UserRole
from schemas import (
    UserCreate, UserLogin, UserResponse, 
    ChatCreate, ChatResponse, MessageCreate, MessageResponse,
    DocumentUploadResponse, DocumentResponse
)
from auth import create_access_token, verify_token, get_current_user
from config import settings

# Создаем таблицы
try:
    logger.info("Инициализация базы данных...")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ База данных инициализирована успешно")
    print("✓ База данных инициализирована успешно")
except Exception as e:
    logger.error(f"✗ Ошибка при создании базы данных: {e}")
    print(f"✗ Ошибка при создании базы данных: {e}")
    import traceback
    traceback.print_exc()

app = FastAPI(title="AeroDoc Assistant API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Создаем директорию для документов
os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)


@app.get("/api/health")
async def health_check():
    """Проверка состояния сервера и базы данных"""
    try:
        # Проверяем подключение к базе данных
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # Проверяем существование таблицы users
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            table_exists = result.fetchone() is not None
        return {
            "status": "ok",
            "database": "connected",
            "tables_created": table_exists
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    logger.info(f"Попытка регистрации пользователя: {user_data.email}, роль: {user_data.role}")
    
    try:
        # Проверяем, что таблицы созданы
        try:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
        except Exception as table_error:
            logger.error(f"Таблица users не существует: {table_error}")
            # Пытаемся создать таблицы
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("Таблицы созданы успешно")
            except Exception as create_error:
                logger.error(f"Ошибка при создании таблиц: {create_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"База данных не инициализирована: {str(create_error)}"
                )
        
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
        
        # Валидируем роль
        try:
            # Преобразуем строку в enum, если нужно
            if isinstance(user_data.role, str):
                role_enum = UserRole(user_data.role)
            else:
                role_enum = user_data.role
            logger.info(f"Роль валидирована: {role_enum}")
        except (ValueError, AttributeError) as e:
            logger.error(f"Ошибка валидации роли: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректная роль: {user_data.role}. Доступные роли: {[r.value for r in UserRole]}"
            )
        
        # Хешируем пароль
        try:
            hashed_password = User.hash_password(user_data.password)
            logger.info("Пароль успешно захеширован")
        except Exception as hash_error:
            logger.error(f"Ошибка при хешировании пароля: {hash_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при обработке пароля: {str(hash_error)}"
            )
        
        # Создаем нового пользователя
        try:
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                role=role_enum,
                hashed_password=hashed_password
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Пользователь успешно создан: ID={db_user.id}")
        except Exception as db_error:
            db.rollback()
            logger.error(f"Ошибка при сохранении в БД: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при сохранении пользователя: {str(db_error)}"
            )
        
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            role=db_user.role,
            created_at=db_user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при регистрации: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        # Возвращаем более детальную ошибку
        error_detail = str(e)
        if "no such table" in error_detail.lower():
            error_detail = "База данных не инициализирована. Перезапустите сервер или запустите init_db.py"
        elif "enum" in error_detail.lower() or "role" in error_detail.lower():
            error_detail = f"Некорректная роль. Доступные роли: engineer, technician, quality_control, project_manager, maintenance, admin"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при регистрации: {error_detail}"
        )


@app.post("/api/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Авторизация пользователя"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            created_at=user.created_at
        )
    }


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        created_at=current_user.created_at
    )


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Загрузка документа"""
    # Проверяем расширение файла
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.json', '.xml'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Разрешенные: {', '.join(allowed_extensions)}"
        )
    
    # Генерируем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(settings.DOCUMENTS_DIR, safe_filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Получаем абсолютный путь
    absolute_path = os.path.abspath(file_path)
    
    # Сохраняем информацию о документе в БД
    db_document = Document(
        filename=file.filename,
        file_path=absolute_path,
        file_size=len(content),
        uploaded_by=current_user.id,
        file_type=file_ext[1:]  # убираем точку
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # Создаем запись о доступе для владельца
    access = DocumentAccess(
        document_id=db_document.id,
        user_id=current_user.id,
        access_level="owner"
    )
    db.add(access)
    db.commit()
    
    return DocumentUploadResponse(
        id=db_document.id,
        filename=db_document.filename,
        file_path=absolute_path,
        file_size=db_document.file_size,
        uploaded_at=db_document.uploaded_at
    )


@app.get("/api/documents", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список доступных документов для текущего пользователя"""
    # Получаем документы, к которым у пользователя есть доступ
    accessible_docs = db.query(Document).join(DocumentAccess).filter(
        DocumentAccess.user_id == current_user.id
    ).all()
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            uploaded_at=doc.uploaded_at,
            file_type=doc.file_type
        )
        for doc in accessible_docs
    ]


@app.post("/api/chats", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новый чат"""
    db_chat = Chat(
        title=chat_data.title or "Новый чат",
        user_id=current_user.id
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    
    return ChatResponse(
        id=db_chat.id,
        title=db_chat.title,
        user_id=db_chat.user_id,
        created_at=db_chat.created_at,
        updated_at=db_chat.updated_at
    )


@app.get("/api/chats", response_model=List[ChatResponse])
async def get_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список чатов пользователя"""
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.updated_at.desc()).all()
    
    return [
        ChatResponse(
            id=chat.id,
            title=chat.title,
            user_id=chat.user_id,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )
        for chat in chats
    ]


@app.get("/api/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сообщения чата"""
    # Проверяем, что чат принадлежит пользователю
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
    
    return [
        MessageResponse(
            id=msg.id,
            chat_id=msg.chat_id,
            content=msg.content,
            role=msg.role,
            created_at=msg.created_at
        )
        for msg in messages
    ]


@app.post("/api/chats/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить сообщение в чат"""
    # Проверяем, что чат принадлежит пользователю
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Проверяем, есть ли уже сообщения в чате
    existing_messages_count = db.query(Message).filter(Message.chat_id == chat_id).count()
    
    # Сохраняем сообщение пользователя
    user_message = Message(
        chat_id=chat_id,
        content=message_data.content,
        role="user"
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Обновляем название чата, если это первое сообщение
    if chat.title == "Новый чат" and existing_messages_count == 0:
        # Берем первые 50 символов первого сообщения как название
        title = message_data.content[:50]
        if len(message_data.content) > 50:
            title += "..."
        chat.title = title
    
    # Обновляем время последнего обновления чата
    chat.updated_at = datetime.utcnow()
    db.commit()
    
    # Получаем документы, доступные пользователю
    accessible_docs = db.query(Document).join(DocumentAccess).filter(
        DocumentAccess.user_id == current_user.id
    ).all()
    
    # Формируем список путей к документам
    document_paths = [doc.file_path for doc in accessible_docs]
    
    # Отправляем запрос в ML-сервис
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            ml_response = await client.post(
                settings.ML_SERVICE_URL,
                json={
                    "question": message_data.content,
                    "document_paths": document_paths,
                    "user_role": current_user.role
                }
            )
            ml_response.raise_for_status()
            ml_data = ml_response.json()
            assistant_response_text = ml_data.get("answer", "Извините, не удалось получить ответ.")
    except httpx.TimeoutException:
        assistant_response_text = "ML-сервис не отвечает в течение установленного времени ожидания. Попробуйте позже."
    except httpx.RequestError as e:
        assistant_response_text = f"Ошибка подключения к ML-сервису: {str(e)}. Убедитесь, что ML-сервис запущен и доступен."
    except Exception as e:
        # Если ML-сервис недоступен, возвращаем заглушку
        assistant_response_text = f"ML-сервис временно недоступен. Ошибка: {str(e)}"
    
    # Сохраняем ответ ассистента
    assistant_message = Message(
        chat_id=chat_id,
        content=assistant_response_text,
        role="assistant"
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    return MessageResponse(
        id=assistant_message.id,
        chat_id=assistant_message.chat_id,
        content=assistant_message.content,
        role=assistant_message.role,
        created_at=assistant_message.created_at
    )


@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить чат"""
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Удаляем все сообщения
    db.query(Message).filter(Message.chat_id == chat_id).delete()
    # Удаляем чат
    db.delete(chat)
    db.commit()
    
    return {"message": "Чат успешно удален"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

