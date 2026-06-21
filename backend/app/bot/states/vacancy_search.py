from aiogram.fsm.state import State, StatesGroup


class VacancySearch(StatesGroup):
    filters = State()
    list = State()
    detail = State()
    conflict = State()
