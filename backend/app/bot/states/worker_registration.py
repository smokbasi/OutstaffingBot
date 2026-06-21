from aiogram.fsm.state import State, StatesGroup


class WorkerRegistration(StatesGroup):
    first_name = State()
    last_name = State()
    age = State()
    gender = State()
    metro = State()
    experience_category = State()
    experience_title = State()
    experience_months = State()
    experience_more = State()
    min_rate = State()
    confirm = State()
