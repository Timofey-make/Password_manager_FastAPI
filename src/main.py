from fastapi import FastAPI, Request, Form, Response, requests
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
    Password: str = Form(...)
):
    print(Login, Password)
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?",
                       (Login,))
        if cursor.fetchone():
            print("Пользователь с таким именем уже есть")
            return RedirectResponse(url="/register", status_code=303)
        else:
            cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1")
            last_user = cursor.fetchone()

            if last_user:
                new_id = last_user[0] + 1
            else:
                new_id = 1
            cursor.execute("INSERT INTO users (id, username, password) VALUES (?,?,?)",
                           (new_id, Login, function.hash_password(Password)))
            return RedirectResponse(url="/login", status_code=303)

@app.get("/login", tags="Логин")
async def login(request: Request):
    try:
        print({"id":request.cookies.get("id"), "username":function.decrypt(request.cookies.get("username"))})
    except:
        print("Куки отчишены или вы не разу не заходили в аккаунт")
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
                       (request.cookies.get("id")))
        encrypted_notes = cursor.fetchall()

        notes = []
        for note in encrypted_notes:
            name, username, encrypted_password = note
            try:
                decrypted_password = function.decrypt(encrypted_password)
            except:
                decrypted_password = "Ошибка расшифровки"
            notes.append((name, username, decrypted_password))
    try:
        print({"id":request.cookies.get("id"), "username":function.decrypt(request.cookies.get("username"))})
    except:
        print("Вы не в сессии")
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
    return templates.TemplateResponse("add_note.html", {"request": request})

@app.post("/doadd", tags="Добавить пароль")
async def doadd(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM passwords WHERE name = ? AND username = ?",
                       (name, username))
        if cursor.fetchone():
            print("Такая запись уже есть")
            return RedirectResponse(url="/add", status_code=303)
        else:
            cursor.execute("INSERT INTO passwords (user_id, name, username, password) VALUES (?,?,?,?)",
                    (request.cookies.get("id"), name, username, function.encrypt(password)))
            return RedirectResponse(url="/", status_code=303)

@app.post("/delete", tags="Удалить пароль")
async def delete_password(
    request: Request,
    name: str = Form(...),
    username: str = Form(...)
):
    print(name, username)
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM passwords WHERE name = ? AND username = ?",
                       (name, username))
    return RedirectResponse(url="/", status_code=303)

@app.get("/change", tags="Изменть пароль")
async def change(request: Request):
    return templates.TemplateResponse("change-password.html", {"request": request})

@app.post("/dochange", tags="Измеить пароль")
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

if __name__ == "__main__":
    init.init_db()
    uvicorn.run("main:app", reload=True)