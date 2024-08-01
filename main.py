import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models.gigachat import GigaChat
import config
import strings
import sqlite3
import json


bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Инициализация GigaChat
gigachat = GigaChat(credentials=config.AUTHORIZATION_DATA, verify_ssl_certs=False)


conn = sqlite3.connect('db.db')

c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS user_chats (user_id INTEGER PRIMARY KEY, chat_history TEXT)''')
conn.commit()


def messages2json(messages):
    res = []
    for message in messages:
        if isinstance(message, SystemMessage):
            res.append({"role": "system", "content": message.content})
        elif isinstance(message, HumanMessage):
            res.append({"role": "user", "content": message.content})
        elif isinstance(message, AIMessage):
            res.append({"role": "ai", "content": message.content})
        
    return json.dumps(res)

def json2messages(json_data):
    json_data = json.loads(json_data)
    res = []
    for message in json_data:
        if message["role"] == "system":
            res.append(SystemMessage(content=message["content"]))
        elif message["role"] == "user":
            res.append(HumanMessage(content=message["content"]))
        elif message["role"] == "ai":
            res.append(AIMessage(content=message["content"]))

    return res


def get_chat_history(user_id):
    c.execute("SELECT chat_history FROM user_chats WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        return json2messages(result[0])
    else:
        return [SystemMessage(content=strings.START_SYSTEM_PROMPT)]


def update_chat_history(user_id, chat_history):
    c.execute("INSERT OR REPLACE INTO user_chats (user_id, chat_history) VALUES (?, ?)", (user_id, messages2json(chat_history)))
    conn.commit()


def clear_chat_history(user_id):
    c.execute("DELETE FROM user_chats WHERE user_id = ?", (user_id, ))
    conn.commit()



@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот-ассистент. Я помогу вам на хакатоне. Задайте мне вопрос!")
    await message.answer(strings.BOT_HELP)


@dp.message(Command("clear"))
async def clear(message: types.Message):
    clear_chat_history(message.from_user.id)
    await message.answer("История чата очищена.")


@dp.message(Command("help"))
async def clear(message: types.Message):
    await message.answer(strings.BOT_HELP)


@dp.message()
async def command(message: types.Message):
    message_text = message.text
    user_id = message.from_user.id
    
    if message_text.startswith("/brainstorm"):
        elements = message_text.split(" ", 1)
        if len(elements) < 2: 
            return message.answer("Напишите /brainstorm *тема*")
        topic = elements[1]
        chat_history = get_chat_history(user_id)
        chat_history.append(HumanMessage(content=strings.BRAINSTORM_QUERY.format(topic)))
        await bot.send_chat_action(user_id, action="typing")
        response = gigachat(chat_history)
        chat_history.append(AIMessage(content=response.content))
        update_chat_history(user_id, chat_history)
        await message.answer(response.content, parse_mode='MARKDOWN')
    else:
        chat_history = get_chat_history(user_id)
        chat_history.append(HumanMessage(content=message_text))
        await bot.send_chat_action(user_id, action="typing")
        response = gigachat(chat_history)
        chat_history.append(AIMessage(content=response.content))
        update_chat_history(user_id, chat_history)
        await message.answer(response.content, parse_mode='MARKDOWN')
    
    # print(chat_history)
    # await message.answer(response, parse_mode='MARKDOWN')


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
