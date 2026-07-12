from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()


# 数据模型定义
class Note(BaseModel):
    title: str
    content: str
    tags: list[str] = []


# 内存存储
notes_db: dict[int, Note] = {}
note_id_counter = 0


# TODO: 实现创建笔记接口 POST /notes/
@app.post("/notes/")
async def create_note(note: Note):
    notes_db[note_id_counter] = note
    note_id_counter = note_id_counter + 1


# TODO: 实现获取所有笔记接口 GET /notes/
@app.get("/notes/")
async def get_notes():
    pass


# TODO: 实现获取单个笔记接口 GET /notes/{note_id}
@app.get("/notes/{note_id}")
async def get_note(note_id: int):
    pass


# TODO: 实现删除笔记接口 DELETE /notes/{note_id}
@app.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    pass


# 扩展挑战
# @app.put("/notes/{note_id}")
# async def update_note(note_id: int, note: Note):
#     pass
