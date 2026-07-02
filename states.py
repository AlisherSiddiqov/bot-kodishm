from aiogram.fsm.state import State, StatesGroup

class AddMovie(StatesGroup):
    code = State()
    caption = State()
    video = State()
    confirm = State()

class Premium(StatesGroup):
    choosing_tariff = State()
    sending_check = State()

class Broadcast(StatesGroup):
    waiting_content = State()
    waiting_code = State()
    confirm = State()

class SetLang(StatesGroup):
    choosing = State()
