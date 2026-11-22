from fastapi import FastAPI


app = FastAPI(title="첫 FastAPI 서버")


@app.get("/")
async def root():
    return {"message": "FastAPI 서버가 동작합니다."}
