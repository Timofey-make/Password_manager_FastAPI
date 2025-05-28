from fastapi import FastAPI, Request, Form, Response, requests
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import unquote
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
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?",
                       (Login,))
        if cursor.fetchone():
            error_msg = "Пользователь с таким именем уже есть"
            return RedirectResponse(url="/register")
        else:
            cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1")
            last_user = cursor.fetchone()

            if last_user:
                new_id = last_user[0] + 1
            else:
                new_id = 1
            cursor.execute("INSERT INTO users (id, username, password) VALUES (?,?,?)",
                           (new_id, Login, function.hash_password(Password)))
            # Создаем редирект-ответ
            redirect = RedirectResponse(url="/", status_code=303)
            # Устанавливаем куки
            redirect.set_cookie(key="id", value=str(new_id))
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
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?",
                       (Login, function.hash_password(Password)))
        user = cursor.fetchone()

        if user:
            # session['id'] = user[0]
            # session['username'] = user[1]
            # Создаем редирект-ответ
            redirect = RedirectResponse(url="/", status_code=303)
            # Устанавливаем куки
            redirect.set_cookie(key="id", value=str(user[0]))
            redirect.set_cookie(key="username", value=function.encrypt(user[1]))
            return redirect
        else:
            print("Неверный логин или пароль")
            return RedirectResponse(url="/login", status_code=303)

@app.get("/", tags="Личный кабинет")
async def main(request: Request):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, username, password FROM passwords WHERE user_id = ?",
                       (request.cookies.get("id"),))
        encrypted_notes = cursor.fetchall()

        if request.cookies.get("id"):
            notes = []
            for note in encrypted_notes:
                name, username, encrypted_password = note
                try:
                    decrypted_password = function.decrypt(encrypted_password)
                except:
                    decrypted_password = "Ошибка расшифровки"
                notes.append((name, username, decrypted_password))
        else:
            return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("main.html", {"request": request, "username":function.decrypt(request.cookies.get("username")), "notes":notes})
    # return {"id":request.cookies.get("id"), "username":function.decrypt(request.cookies.get("username"))}

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
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?",
                       (request.cookies.get("id"),))
        if cursor.fetchone():
            return templates.TemplateResponse("add_note.html", {"request": request})
        else:
            return RedirectResponse(url="/login", status_code=303)

@app.post("/doadd", tags="Добавить пароль")
async def doadd(
    request: Request,
    categories: str = Form(...),
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    print(categories)
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM passwords WHERE name = ? AND username = ?",
                       (name, username))
        if cursor.fetchone():
            print("Такая запись уже есть")
            return RedirectResponse(url="/add", status_code=303)
        else:
            cursor.execute("INSERT INTO passwords (categories, user_id, name, username, password) VALUES (?,?,?,?,?)",
                    (categories.lower(), request.cookies.get("id"), name, username, function.encrypt(password)))
            return RedirectResponse(url="/", status_code=303)

@app.get("/delete", tags="Удалить пароль")
async def delete_password(
    name: str,
    username: str,
    request: Request,
):
    print(name, username)
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM passwords WHERE name = ? AND username = ?",
                       (name, username))
        cursor.execute("DELETE FROM share WHERE sendername = ? AND name = ? AND username = ?",
                       (function.decrypt(request.cookies.get("username")), name, username))
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete-share", tags="Удалить пароль")
async def delete_share(
    request: Request,
    sendername: str = Form(...),
    name: str = Form(...),
    username: str = Form(...)
):
    print(sendername, name, username)
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM share WHERE ownername = ? AND sendername = ? AND name = ? AND username = ?",
                       (request.cookies.get("id"), sendername, name, username))
    return RedirectResponse(url="/view", status_code=303)

@app.get("/change", tags="Изменить пароль")
async def change(request: Request):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?",
                       (request.cookies.get("id"),))
        if cursor.fetchone():
            return templates.TemplateResponse("change-password.html", {"request": request})
        else:
            return RedirectResponse(url="/login", status_code=303)

@app.post("/dochange", tags="Изменить пароль")
async def dochange(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""UPDATE passwords SET password = ?WHERE name = ? AND username = ?""",
                       (function.encrypt(password), name, username))
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
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        user_id = request.cookies.get("id")
        login = unquote(login)
        username = unquote(username)
        name = unquote(name)
        password = unquote(password)
        print(user_id, login, name, username, password)

        # Ищем пароль в базе
        cursor.execute("""
            SELECT password 
            FROM passwords 
            WHERE name = ? 
                AND username = ? 
                AND user_id = ?
        """, (name, username, user_id))

        true_password = cursor.fetchone()
        print(true_password[0])

        if true_password is None:
            print("Пароль не существует или вы им не владеете")
            return RedirectResponse(url="/", status_code=303)

        if true_password[0] == function.encrypt(password):
            cursor.execute("SELECT id FROM users WHERE username = ?", (login,))
            recipient = cursor.fetchone()

            if recipient is None:
                print("Получатель не найден")
                return RedirectResponse(url="/", status_code=303)

            sender_username = function.decrypt(request.cookies.get("username"))

            cursor.execute("""
                INSERT INTO share (
                    ownername, 
                    sendername, 
                    name, 
                    username, 
                    password
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                recipient[0],  # ID получателя
                sender_username,  # Имя отправителя
                name,  # Название сервиса
                username,  # Логин для сервиса
                function.encrypt(password)  # Шифруем пароль
            ))
            conn.commit()  # Важно: сохраняем изменения в БД!

            print("Успешный шаринг")
            return RedirectResponse(url="/", status_code=303)

        else:
            print("Неверный пароль")
            return RedirectResponse(url="/", status_code=303)

@app.get("/view", tags="Личный кабинет")
async def view(request:Request):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sendername, name, username, password FROM share WHERE ownername = ?",
                       (request.cookies.get("id"),))
        encrypted_notes = cursor.fetchall()

        if request.cookies.get("id"):
            notes = []
            for note in encrypted_notes:
                sendername, name, username, encrypted_password = note
                try:
                    decrypted_password = function.decrypt(encrypted_password)
                except:
                    decrypted_password = "Ошибка расшифровки"
                notes.append((sendername, name, username, decrypted_password))
        else:
            return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("view-password.html", {"request": request, "username":function.decrypt(request.cookies.get("username")), "notes":notes})

@app.post("/search", tags="Поиск по тегу")
async def search(
    request:Request,
    categories: str = Form(...)
):
    categories = categories.lower()
    if categories == "iddqd":
        return RedirectResponse(url="/screamer", status_code=303)
    else:
        with sqlite3.connect("users.db") as conn:
         cursor = conn.cursor()
         cursor.execute("SELECT name, username, password FROM passwords WHERE categories = ? AND user_id = ?",
                        (categories, request.cookies.get("id")))
         encrypted_notes = cursor.fetchall()
         notes = []
         for note in encrypted_notes:
             name, username, encrypted_password = note
             try:
                 decrypted_password = function.decrypt(encrypted_password)
             except:
                 decrypted_password = "Ошибка расшифровки"
             notes.append((name, username, decrypted_password))
         return templates.TemplateResponse("view-categories.html", {"request": request, "categories":categories, "notes":notes})

@app.get("/screamer", tags="Скример")
async def screamer(request: Request):
    return templates.TemplateResponse("screamer.html", {"request": request})


if __name__ == "__main__":
    init.init_db()
    uvicorn.run("main:app", reload=True)