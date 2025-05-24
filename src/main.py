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
        cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1")
        last_user = cursor.fetchone()

        if last_user:
            new_id = last_user[0] + 1
        else:
            new_id = 1
        cursor.execute("INSERT INTO users (id, username, password) VALUES (?,?,?)", (new_id, Login, function.hash_password(Password)))
    return RedirectResponse(url="/login")

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
            return RedirectResponse(url="/login")

@app.get("/", tags="Личный кабинет")
async def main(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})
    # return {"id":request.cookies.get("id"), "username":function.decrypt(request.cookies.get("username"))}

if __name__ == "__main__":
    init.init_db()
    uvicorn.run("main:app", reload=True)