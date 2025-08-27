from fastapi import FastAPI, Request, Form, Response, requests
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import unquote

from requests import session
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy import update

import function
import sqlite3
import uvicorn
import init

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/register", tags="Регистрация")
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/doregister", tags="Регистрация")
async def doregister(
    request: Request,
    Login: str = Form(...),
    Password: str = Form(...),
):
    print(Login, Password)
    with Session(init.engine) as conn:
        stmt = select(init.User).where(init.User.username == Login)
        data = conn.execute(stmt).fetchall()
        if data:
            error_msg = "Пользователь с таким именем уже есть"
            return RedirectResponse(url="/register", status_code=303)
        else:
            user = init.User(
                username=Login,
                password=function.hash_password(Password)
            )
            conn.add(user)
            conn.commit()
    conn = Session(init.engine)
    stmt = select(init.User).where(init.User.username == Login)
    id = conn.execute(stmt).fetchall()[0][0].id
    conn.commit()
    conn.close()
    redirect = RedirectResponse(url="/", status_code=303)
    # Устанавливаем куки
    redirect.set_cookie(key="id", value=str(id))
    redirect.set_cookie(key="username", value=function.encrypt(Login))
    return redirect

@app.get("/login", tags="Логин")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/dologin", tags="Логин")
async def dologin(
    request: Request,
    Login: str = Form(...),
    Password: str = Form(...)
):
    with Session(init.engine) as conn:
        stmt = select(init.User).where(init.User.username == Login)
        data = conn.execute(stmt).fetchall()
        if data and data[0][0].password == function.hash_password(Password):
            # Создаем редирект-ответ
            redirect = RedirectResponse(url="/", status_code=303)
            # Устанавливаем куки
            redirect.set_cookie(key="id", value=str(data[0][0].id))
            redirect.set_cookie(key="username", value=function.encrypt(data[0][0].username))
            return redirect
        else:
            print("Неверный логин или пароль")
            return RedirectResponse(url="/login", status_code=303)

@app.get("/", tags="Личный кабинет")
async def main(request: Request):
    with Session(init.engine) as conn:
        user_id = request.cookies.get("id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)
        stmt = select(init.Password.name, init.Password.username, init.Password.password).where(
            init.Password.user_id == user_id
        )
        encrypted_notes = conn.execute(stmt).fetchall()

        notes = []
        for note in encrypted_notes:
            name, username, encrypted_password = note
            try:
                decrypted_password = function.decrypt(encrypted_password)
            except:
                decrypted_password = "Ошибка расшифровки"
            notes.append((name, username, decrypted_password))
    return templates.TemplateResponse("main.html", {"request": request, "username":function.decrypt(request.cookies.get("username")), "notes":notes})

@app.get("/logout", tags="Выход")
async def logout(request: Request):
    # Создаем редирект-ответ
    redirect = RedirectResponse(url="/login", status_code=303)
    # Устанавливаем куки
    redirect.delete_cookie(key="id")
    redirect.delete_cookie(key="username")
    return redirect

@app.get("/add", tags="Добавить пароль")
async def add(request: Request):
    if request.cookies.get("id"):
        return templates.TemplateResponse("add_note.html", {"request": request})
    else:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/doadd", tags="Добавить пароль")
async def doadd(
    request: Request,
    categories: str = Form(...),
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)):
    with Session(init.engine) as conn:
        stmt = select(init.Password).where(
            init.Password.user_id == request.cookies.get("id"), init.Password.name == name, init.Password.username == username)
        data = conn.execute(stmt).fetchall()
        if data:
            print("Такая запись уже есть")
            return RedirectResponse(url="/add", status_code=303)
        password1 = init.Password(
            categories=categories.lower(),
            user_id=request.cookies.get("id"),
            name=name,
            username=username,
            password=function.encrypt(password)
        )
        conn.add(password1)
        conn.commit()

        return RedirectResponse(url="/", status_code=303)

@app.get("/delete", tags="Удалить пароль")
async def delete_password(
    name: str,
    username: str,
    request: Request,
):
    with Session(init.engine) as conn:
        to_delete = conn.execute(
            select(init.Password).where(
                (init.Password.user_id == request.cookies.get("id")) &
                (init.Password.name == name) &
                (init.Password.username == username)
            )
        ).scalars().all()
        to_delete2 = conn.execute(
            select(init.Share).where(
                (init.Share.sendername == function.decrypt(request.cookies.get("username"))) &
                (init.Share.name == name) &
                (init.Share.username == username)
            )
        ).scalars().all()
        for item in to_delete:
            conn.delete(item)
        for item in to_delete2:
            conn.delete(item)
        conn.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete-share", tags="Удалить пароль")
async def delete_share(
    request: Request,
    sendername: str = Form(...),
    name: str = Form(...),
    username: str = Form(...)
):
    with Session(init.engine) as conn:
        to_delete = conn.execute(
            select(init.Share).where(
                (init.Share.ownername == request.cookies.get("id")) &
                (init.Share.sendername == sendername) &
                (init.Share.name == name) &
                (init.Share.username == username)
            )
        ).scalars().all()
        for item in to_delete:
            conn.delete(item)
        conn.commit()
    return RedirectResponse(url="/view", status_code=303)

@app.get("/change", tags="Изменить пароль")
async def change(request: Request):
    if request.cookies.get("id"):
        return templates.TemplateResponse("change-password.html", {"request": request})
    else:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/dochange", tags="Изменить пароль")
async def dochange(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)):
    with Session(init.engine) as conn:
        stmt = (
            update(init.Password)
            .where((init.Password.name == name) & (init.Password.username == username))
            .values(password=function.encrypt(password))
        )
        conn.execute(stmt)
        conn.commit()
    # with sqlite3.connect("users.db") as conn:
    #     cursor = conn.cursor()
    #     cursor.execute("""UPDATE passwords SET password = ?WHERE name = ? AND username = ?""",
    #                    (function.encrypt(password), name, username))
    return RedirectResponse(url="/", status_code=303)

@app.get("/share", tags=["Шэйринг паролей"])
async def share(
        name: str,
        username: str,
        request: Request
):
    """Обработчик страницы для общего доступа к паролю"""
    if not request.cookies.get("id"):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "share-password.html",
        {
            "request": request,
            "name": name,
            "username": username
        }
    )

@app.post("/doshare", tags=["Шэйринг пролей"])
async def doshare(
        request: Request,
        login: str = Form(...),
        name: str = Form(...),
        username: str = Form(...),
        password: str = Form(...)
):
    # Получаем engine из вашей конфигурации (должен быть инициализирован ранее)
    with Session(init.engine) as conn:  # init.engine - ваш движок SQLAlchemy
        user_id = request.cookies.get("id")
        login = unquote(login)
        username = unquote(username)
        name = unquote(name)
        password = unquote(password)

        print(user_id, login, name, username, password)

        # Ищем пароль в базе с использованием SQLAlchemy
        stmt = select(init.Password).where(
            init.Password.name == name,
            init.Password.username == username,
            init.Password.user_id == user_id
        )
        true_password_record = conn.execute(stmt).scalar_one_or_none()

        if true_password_record is None:
            print("Пароль не существует или вы им не владеете")
            return RedirectResponse(url="/", status_code=303)

        if true_password_record.password == function.encrypt(password):
            # Ищем получателя
            recipient_stmt = select(init.User).where(init.User.username == login)
            recipient = conn.execute(recipient_stmt).scalar_one_or_none()

            if recipient is None:
                print("Получатель не найден")
                return RedirectResponse(url="/", status_code=303)

            sender_username = function.decrypt(request.cookies.get("username"))

            # Создаем запись о шаринге
            share_record = init.Share(
                ownername=recipient.id,  # ID получателя
                sendername=sender_username,  # Имя отправителя
                name=name,  # Название сервиса
                username=username,  # Логин для сервиса
                password=function.encrypt(password)  # Шифруем пароль
            )

            conn.add(share_record)
            conn.commit()  # Сохраняем изменения

            print("Успешный шаринг")
            return RedirectResponse(url="/", status_code=303)
        else:
            print("Неверный пароль")
            return RedirectResponse(url="/", status_code=303)


from sqlalchemy import select, delete
from sqlalchemy.orm import Session


@app.get("/view", tags=["Личный кабинет"])
async def view(request: Request):
    user_id = request.cookies.get("id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    with Session(init.engine) as conn:
        # Получаем расшаренные пароли
        stmt = select(init.Share).where(init.Share.ownername == user_id)
        shared_records = conn.execute(stmt).scalars().all()

        notes = []
        for record in shared_records:
            try:
                decrypted_password = function.decrypt(record.password)
            except:
                decrypted_password = "Ошибка расшифровки"
            notes.append((
                record.sendername,
                record.name,
                record.username,
                decrypted_password
            ))

    return templates.TemplateResponse(
        "view-password.html",
        {
            "request": request,
            "username": function.decrypt(request.cookies.get("username")),
            "notes": notes
        }
    )


@app.post("/search", tags=["Поиск по тегу"])
async def search(
        request: Request,
        categories: str = Form(...)
):
    categories = categories.lower()
    if categories == "iddqd":
        return RedirectResponse(url="/screamer", status_code=303)

    user_id = request.cookies.get("id")
    with Session(init.engine) as conn:
        stmt = select(init.Password).where(
            init.Password.categories == categories,
            init.Password.user_id == user_id
        )
        password_records = conn.execute(stmt).scalars().all()

        notes = []
        for record in password_records:
            try:
                decrypted_password = function.decrypt(record.password)
            except:
                decrypted_password = "Ошибка расшифровки"
            notes.append((
                record.name,
                record.username,
                decrypted_password
            ))

    return templates.TemplateResponse(
        "view-categories.html",
        {
            "request": request,
            "categories": categories,
            "notes": notes
        }
    )


@app.get("/screamer", tags=["Скример"])
async def screamer(request: Request):
    return templates.TemplateResponse("screamer.html", {"request": request})


@app.get("/settings", tags=["Настройки"])
async def settings(request: Request):
    username = function.decrypt(request.cookies.get("username"))
    user_id = request.cookies.get("id")
    if username and user_id:
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "username": username,
                "id": user_id
            }
        )
    return RedirectResponse(url="/login", status_code=303)


@app.get("/panic_button", tags=["Удалить все пароли"])
async def panic_button(request: Request):
    return templates.TemplateResponse("panic_button.html", {"request": request})


@app.post("/dopanic", tags=["Удалить все пароли"])
async def dopanic(request: Request):
    username = function.decrypt(request.cookies.get("username"))
    user_id = request.cookies.get("id")

    with Session(init.engine) as conn:
        try:
            # Удаляем пароли пользователя
            conn.execute(
                delete(init.Password).where(init.Password.user_id == user_id)
            )
            # Удаляем расшаренные пароли
            conn.execute(
                delete(init.Share).where(init.Share.sendername == username)
            )
            conn.commit()
            return RedirectResponse(url="/", status_code=303)
        except Exception as e:
            print(f"Ошибка при удалении: {e}")
            return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    init.Base.metadata.create_all(init.engine)
    uvicorn.run("main:app", reload=True)